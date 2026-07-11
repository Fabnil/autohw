from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from common.validation.paths import validate_absolute_existing_directory_path
from common.validation.strings import validate_non_empty_trimmed_string
from study_agent.adapters.codex_course_mutation_runner import CodexCourseMutationRunner
from study_agent.domain.course import CourseContext, CoursesCatalog
from study_agent.domain.course_root import validate_course_root_structure
from study_agent.ports.course_mutation_runner import CourseMutationRunner
from study_agent.prompts.course.create_add_course_prompt import create_add_course_prompt
from study_agent.prompts.course.create_update_course_prompt import create_update_course_prompt

CourseMutationMode = Literal["add", "update"]
_MAX_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class AddCourseCommand:
    id: str
    title: str
    description: str
    course_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", validate_non_empty_trimmed_string(self.id))
        object.__setattr__(self, "title", validate_non_empty_trimmed_string(self.title))
        object.__setattr__(
            self,
            "description",
            validate_non_empty_trimmed_string(self.description),
        )
        course_root = validate_absolute_existing_directory_path(self.course_root)
        object.__setattr__(self, "course_root", course_root.resolve())


@dataclass(frozen=True, slots=True)
class UpdateCourseCommand:
    id: str
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", validate_non_empty_trimmed_string(self.id))
        object.__setattr__(
            self,
            "description",
            validate_non_empty_trimmed_string(self.description),
        )


@dataclass(frozen=True, slots=True)
class CourseMutationPaths:
    courses_by_id_root: Path
    target_json_path: Path
    run_dir: Path


@dataclass(frozen=True, slots=True)
class CourseMutationResult:
    mode: CourseMutationMode
    course: CourseContext
    target_json_path: Path
    run_dir: Path
    attempts: int


@dataclass(frozen=True, slots=True)
class _SnapshotDiff:
    created: tuple[Path, ...]
    modified: tuple[Path, ...]
    deleted: tuple[Path, ...]


async def add_course(
    command: AddCourseCommand,
    *,
    workspace_root: Path,
    runner: CourseMutationRunner | None = None,
) -> CourseMutationResult:
    workspace_root = validate_absolute_existing_directory_path(workspace_root)
    validate_course_root_structure(command.course_root)

    paths = _build_mutation_paths(
        workspace_root=workspace_root.resolve(),
        course_id=command.id,
        mode="add",
    )
    catalog = CoursesCatalog.from_course_json_files(courses_dir=paths.courses_by_id_root)

    if any(course.id == command.id for course in catalog.courses):
        raise ValueError(f"Course with id `{command.id}` already exists")

    if paths.target_json_path.exists():
        raise ValueError(f"Target course JSON already exists: {paths.target_json_path}")

    if any(course.course_root == command.course_root for course in catalog.courses):
        raise ValueError(
            "Course with the same course_root already exists: "
            f"{command.course_root}"
        )

    base_prompt = create_add_course_prompt(
        course_id=command.id,
        title=command.title,
        description=command.description,
        course_root=command.course_root,
        target_json_path=paths.target_json_path,
        courses_by_id_root=paths.courses_by_id_root,
    )

    return await _run_course_mutation(
        mode="add",
        course_id=command.id,
        title=command.title,
        description=command.description,
        course_root=command.course_root,
        paths=paths,
        base_prompt=base_prompt,
        runner=runner or CodexCourseMutationRunner(),
    )


async def update_course(
    command: UpdateCourseCommand,
    *,
    workspace_root: Path,
    runner: CourseMutationRunner | None = None,
) -> CourseMutationResult:
    workspace_root = validate_absolute_existing_directory_path(workspace_root)
    paths = _build_mutation_paths(
        workspace_root=workspace_root.resolve(),
        course_id=command.id,
        mode="update",
    )
    catalog = CoursesCatalog.from_course_json_files(courses_dir=paths.courses_by_id_root)
    existing_course = next(
        (course for course in catalog.courses if course.id == command.id),
        None,
    )
    if existing_course is None:
        raise ValueError(f"Course with id `{command.id}` does not exist")

    validate_course_root_structure(existing_course.course_root)

    base_prompt = create_update_course_prompt(
        course_id=existing_course.id,
        title=existing_course.title,
        description=command.description,
        course_root=existing_course.course_root,
        target_json_path=paths.target_json_path,
        courses_by_id_root=paths.courses_by_id_root,
    )

    return await _run_course_mutation(
        mode="update",
        course_id=existing_course.id,
        title=existing_course.title,
        description=command.description,
        course_root=existing_course.course_root,
        paths=paths,
        base_prompt=base_prompt,
        runner=runner or CodexCourseMutationRunner(),
    )


async def _run_course_mutation(
    *,
    mode: CourseMutationMode,
    course_id: str,
    title: str,
    description: str,
    course_root: Path,
    paths: CourseMutationPaths,
    base_prompt: str,
    runner: CourseMutationRunner,
) -> CourseMutationResult:
    paths.courses_by_id_root.mkdir(parents=True, exist_ok=True)
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    baseline_snapshot = _snapshot_course_json_files(paths.courses_by_id_root)

    corrective_issues: tuple[str, ...] = ()

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        attempt_dir = paths.run_dir / f"attempt-{attempt:02d}"
        attempt_dir.mkdir(parents=True, exist_ok=True)

        prompt = _compose_prompt(
            base_prompt=base_prompt,
            corrective_issues=corrective_issues,
        )
        (attempt_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        await runner.run(
            course_root=course_root,
            prompt=prompt,
            artifact_path=attempt_dir / "last-message.txt",
            stdout_log_path=attempt_dir / "stdout.jsonl",
            stderr_log_path=attempt_dir / "stderr.log",
        )

        validated_course, issues = _validate_mutation_output(
            mode=mode,
            target_json_path=paths.target_json_path,
            baseline_snapshot=baseline_snapshot,
            expected_id=course_id,
            expected_title=title,
            expected_description=description,
            expected_course_root=course_root,
            courses_by_id_root=paths.courses_by_id_root,
        )
        if validated_course is not None:
            return CourseMutationResult(
                mode=mode,
                course=validated_course,
                target_json_path=paths.target_json_path,
                run_dir=paths.run_dir,
                attempts=attempt,
            )

        corrective_issues = issues

    rendered_issues = "\n".join(f"- {issue}" for issue in corrective_issues)
    raise RuntimeError(
        f"Course {mode} failed after {_MAX_ATTEMPTS} attempts:\n{rendered_issues}"
    )


def _build_mutation_paths(
    *,
    workspace_root: Path,
    course_id: str,
    mode: CourseMutationMode,
) -> CourseMutationPaths:
    runtime_root = workspace_root / ".runtime"
    courses_by_id_root = runtime_root / "courses" / "by-id"
    target_json_path = courses_by_id_root / f"{course_id}.json"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = runtime_root / "runs" / "courses" / f"{timestamp}-{mode}-{course_id}"

    return CourseMutationPaths(
        courses_by_id_root=courses_by_id_root,
        target_json_path=target_json_path,
        run_dir=run_dir,
    )


def _snapshot_course_json_files(courses_by_id_root: Path) -> dict[Path, bytes]:
    return {
        path.resolve(): path.read_bytes()
        for path in sorted(courses_by_id_root.glob("*.json"))
        if path.is_file()
    }


def _diff_snapshots(
    *,
    before: dict[Path, bytes],
    after: dict[Path, bytes],
) -> _SnapshotDiff:
    before_paths = set(before)
    after_paths = set(after)

    created = tuple(sorted(after_paths - before_paths))
    deleted = tuple(sorted(before_paths - after_paths))
    modified = tuple(
        sorted(
            path
            for path in before_paths & after_paths
            if before[path] != after[path]
        )
    )

    return _SnapshotDiff(
        created=created,
        modified=modified,
        deleted=deleted,
    )


def _validate_mutation_output(
    *,
    mode: CourseMutationMode,
    target_json_path: Path,
    baseline_snapshot: dict[Path, bytes],
    expected_id: str,
    expected_title: str,
    expected_description: str,
    expected_course_root: Path,
    courses_by_id_root: Path,
) -> tuple[CourseContext | None, tuple[str, ...]]:
    current_snapshot = _snapshot_course_json_files(courses_by_id_root)
    diff = _diff_snapshots(
        before=baseline_snapshot,
        after=current_snapshot,
    )

    issues: list[str] = []
    target_json_path = target_json_path.resolve()

    if mode == "add":
        if target_json_path not in diff.created:
            issues.append(f"Target course JSON was not created: {target_json_path}")
    else:
        if target_json_path not in diff.modified:
            issues.append(f"Target course JSON was not modified: {target_json_path}")

    extra_created = tuple(path for path in diff.created if path != target_json_path)
    extra_modified = tuple(path for path in diff.modified if path != target_json_path)
    extra_deleted = tuple(path for path in diff.deleted if path != target_json_path)

    if mode == "add" and diff.modified:
        issues.append(
            "No existing course JSON files may be modified during add: "
            + ", ".join(str(path) for path in diff.modified)
        )

    if diff.deleted:
        deleted_paths = ", ".join(str(path) for path in diff.deleted)
        issues.append(f"No course JSON files may be deleted: {deleted_paths}")

    if extra_created or extra_modified or extra_deleted:
        touched_paths = [
            *[str(path) for path in extra_created],
            *[str(path) for path in extra_modified],
            *[str(path) for path in extra_deleted],
        ]
        issues.append(
            "Only the target course JSON may change. Revert extra changes: "
            + ", ".join(touched_paths)
        )

    if not target_json_path.exists():
        issues.append(f"Target course JSON does not exist: {target_json_path}")
        return None, tuple(issues)

    try:
        course = CourseContext.from_json(context_json_path=target_json_path)
    except ValidationError as error:
        rendered_errors = json.dumps(
            error.errors(include_url=False),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        issues.append(f"Target course JSON is invalid:\n{rendered_errors}")
        return None, tuple(issues)

    _append_exact_match_issue(
        issues,
        field_name="id",
        expected=expected_id,
        actual=course.id,
    )
    _append_exact_match_issue(
        issues,
        field_name="title",
        expected=expected_title,
        actual=course.title,
    )
    _append_exact_match_issue(
        issues,
        field_name="description",
        expected=expected_description,
        actual=course.description,
    )
    _append_exact_match_issue(
        issues,
        field_name="course_root",
        expected=expected_course_root,
        actual=course.course_root,
    )

    if issues:
        return None, tuple(issues)

    return course, ()


def _append_exact_match_issue(
    issues: list[str],
    *,
    field_name: str,
    expected: object,
    actual: object,
) -> None:
    if actual != expected:
        issues.append(f"{field_name} must stay exactly `{expected}`, got `{actual}`")


def _compose_prompt(
    *,
    base_prompt: str,
    corrective_issues: tuple[str, ...],
) -> str:
    if not corrective_issues:
        return base_prompt

    issues_block = "\n\n".join(corrective_issues)
    return (
        f"{base_prompt}\n\n"
        "Предыдущая попытка не прошла автоматическую проверку.\n"
        "Исправь только проблемы ниже и затем снова приведи "
        "целевой JSON в корректное состояние.\n\n"
        f"{issues_block}\n\n"
        "Не меняй другие course JSON."
    )
