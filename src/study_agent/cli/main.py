"""CLI entry point for Study Agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from study_agent.application.add_course import AddCourseCommand, add_course
from study_agent.application.update_course import UpdateCourseCommand, update_course


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Study Agent CLI."""
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as error:
        code = error.code
        return code if isinstance(code, int) else 1

    if getattr(args, "command", None) is None:
        parser.print_help()
        return 0

    workspace_root = Path.cwd().resolve()

    try:
        if args.command == "add" and args.entity == "course":
            result = asyncio.run(
                add_course(
                    AddCourseCommand(
                        id=args.id,
                        title=args.title,
                        description=args.description,
                        course_root=Path(args.course_root),
                    ),
                    workspace_root=workspace_root,
                )
            )
            print(f"Added course JSON: {result.target_json_path}")
            return 0

        if args.command == "update" and args.entity == "course":
            result = asyncio.run(
                update_course(
                    UpdateCourseCommand(
                        id=args.id,
                        description=args.description,
                    ),
                    workspace_root=workspace_root,
                )
            )
            print(f"Updated course JSON: {result.target_json_path}")
            return 0
    except (ValidationError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="study-agent")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add")
    add_subparsers = add_parser.add_subparsers(dest="entity", required=True)
    add_course_parser = add_subparsers.add_parser("course")
    add_course_parser.add_argument("--id", required=True)
    add_course_parser.add_argument("--title", required=True)
    add_course_parser.add_argument("--description", required=True)
    add_course_parser.add_argument("--course-root", required=True)

    update_parser = subparsers.add_parser("update")
    update_subparsers = update_parser.add_subparsers(dest="entity", required=True)
    update_course_parser = update_subparsers.add_parser("course")
    update_course_parser.add_argument("--id", required=True)
    update_course_parser.add_argument("--description", required=True)

    return parser


def run() -> int:
    """Console-script entry point."""
    return main()
