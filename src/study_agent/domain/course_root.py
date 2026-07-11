from __future__ import annotations

from pathlib import Path

from pathspec import GitIgnoreSpec

from common.validation.paths import validate_absolute_existing_directory_path

_ALLOWED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        "assignments",
        "instructions",
        "materials",
    }
)
_ALLOWED_FILE_NAMES = frozenset(
    {
        ".gitignore",
        "pyproject.toml",
        "uv.lock",
    }
)


def validate_course_root_structure(course_root: Path) -> Path:
    course_root = validate_absolute_existing_directory_path(course_root)
    gitignore_spec = _load_gitignore_spec(course_root)

    for entry in course_root.iterdir():
        if entry.name in _ALLOWED_DIRECTORY_NAMES:
            if not entry.is_dir():
                raise ValueError(
                    f"course_root entry must be a directory: {entry}"
                )
            continue

        if entry.name in _ALLOWED_FILE_NAMES:
            if not entry.is_file():
                raise ValueError(
                    f"course_root entry must be a file: {entry}"
                )
            continue

        if _is_allowed_by_gitignore(
            entry=entry,
            gitignore_spec=gitignore_spec,
        ):
            continue

        raise ValueError(f"Unexpected top-level entry in course_root: {entry}")

    return course_root


def _load_gitignore_spec(course_root: Path) -> GitIgnoreSpec | None:
    gitignore_path = course_root / ".gitignore"
    if not gitignore_path.exists():
        return None

    return GitIgnoreSpec.from_lines(
        gitignore_path.read_text(encoding="utf-8").splitlines()
    )


def _is_allowed_by_gitignore(
    *,
    entry: Path,
    gitignore_spec: GitIgnoreSpec | None,
) -> bool:
    if gitignore_spec is None:
        return False

    relative_name = entry.name
    if entry.is_dir():
        relative_name = f"{relative_name}/"

    return bool(gitignore_spec.match_file(relative_name))
