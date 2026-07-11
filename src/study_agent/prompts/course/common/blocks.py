from __future__ import annotations

from pathlib import Path

from common.validation.strings import validate_non_empty_trimmed_string


def validate_prompt_text_field(
    value: str,
    *,
    field_name: str,
) -> str:
    try:
        return validate_non_empty_trimmed_string(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must not be empty") from error


def validate_absolute_path(
    path: Path,
    *,
    field_name: str,
) -> Path:
    if not path.is_absolute():
        raise ValueError(f"{field_name} must be absolute")

    return path


def build_course_root_structure_block() -> str:
    return """
Допустимая top-level структура курса:
- directories: materials/, assignments/, instructions/, .git/
- files: pyproject.toml, uv.lock, .gitignore
- также допустимы любые top-level entries, которые игнорируются по полным правилам .gitignore

Никакие другие top-level файлы и папки не считай допустимыми.
Внутреннюю структуру внутри корректно названных папок можешь
анализировать свободно, но не придумывай новых top-level требований.
""".strip()


def build_course_json_contract_block() -> str:
    return """
{
  "id": "непустой id курса",
  "title": "непустое название курса",
  "description": "непустое описание курса",
  "course_root": "/абсолютный/путь/к/корню/курса",
  "references": [
    {
      "path": "/абсолютный/путь/к/существующему/файлу",
      "summary": "зачем этот файл нужен",
      "location": "где именно смотреть или null"
    }
  ]
}

Требования:
- не добавляй неизвестные поля;
- все строки должны быть непустыми после trim;
- course_root должен быть абсолютным путем к существующей директории;
- path в references должен быть абсолютным путем к существующему файлу;
- references может быть пустым списком;
- не дублируй одинаковые path внутри references.
""".strip()


def build_course_json_mutation_rules_block(
    *,
    mode: str,
    target_json_path: Path,
    courses_by_id_root: Path,
) -> str:
    mutation_verb = "создай" if mode == "add" else "измени"

    return f"""
Правила изменений:
- {mutation_verb.capitalize()} ровно один целевой course JSON: {target_json_path}
- Не создавай, не изменяй и не удаляй другие course JSON внутри {courses_by_id_root}
- Не меняй id, title и course_root произвольно
- Не завершай работу, пока целевой JSON не приведен к корректному формату
""".strip()
