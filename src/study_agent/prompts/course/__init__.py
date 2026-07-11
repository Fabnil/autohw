"""Prompt builders for course mutation stages."""

from study_agent.prompts.course.create_add_course_prompt import create_add_course_prompt
from study_agent.prompts.course.create_update_course_prompt import (
    create_update_course_prompt,
)

__all__ = [
    "create_add_course_prompt",
    "create_update_course_prompt",
]
