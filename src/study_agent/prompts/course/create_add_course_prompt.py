from __future__ import annotations

from pathlib import Path

from study_agent.prompts.course.common.blocks import (
    build_course_json_contract_block,
    build_course_json_mutation_rules_block,
    build_course_root_structure_block,
    validate_absolute_path,
    validate_prompt_text_field,
)


def create_add_course_prompt(
    *,
    course_id: str,
    title: str,
    description: str,
    course_root: Path,
    target_json_path: Path,
    courses_by_id_root: Path,
) -> str:
    course_id = validate_prompt_text_field(course_id, field_name="course_id")
    title = validate_prompt_text_field(title, field_name="title")
    description = validate_prompt_text_field(description, field_name="description")
    course_root = validate_absolute_path(course_root, field_name="course_root")
    target_json_path = validate_absolute_path(
        target_json_path,
        field_name="target_json_path",
    )
    courses_by_id_root = validate_absolute_path(
        courses_by_id_root,
        field_name="courses_by_id_root",
    )

    course_structure_block = build_course_root_structure_block()
    contract_block = build_course_json_contract_block()
    mutation_rules_block = build_course_json_mutation_rules_block(
        mode="add",
        target_json_path=target_json_path,
        courses_by_id_root=courses_by_id_root,
    )

    return f"""
Ты добавляешь курс в каталог Study Agent.

Режим:
add course

Рабочая директория уже установлена в корень курса:
{course_root}

Входные данные курса:
- id: {course_id}
- title: {title}
- description: {description}
- course_root: {course_root}

Проверь курс и собери references по реально существующим полезным файлам.

Структура курса:
{course_structure_block}

Создай course JSON:
{target_json_path}

Каталог всех course JSON:
{courses_by_id_root}

Формат целевого JSON:
{contract_block}

{mutation_rules_block}

Итоговый JSON должен в точности содержать:
- id = {course_id}
- title = {title}
- description = {description}
- course_root = {course_root}

references можешь заполнить по результатам анализа курса.
""".strip()
