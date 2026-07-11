# План реализации Study Agent

## 1. Каркас проекта
- Создать `domain`, `application`, `ports`, `adapters`, `prompts`, `skills`, `cli`, `tests`.
- Настроить `uv`, `ruff`, `pytest`, `mypy`.
- Добавить полностью игнорируемую `.runtime/`.

## 2. Базовые сущности
- `FileRef`: root, relative path, hash, media type.
- `CourseSpec`: id, title, root, instructions.
- `MaterialSpec`: id, course, kind, source, chunking strategy.
- `AssignmentSpec`: id, course, statement, data, starter files, outputs.
- `TaskSpec`: id, assignment, number, statement, dependencies.

## 3. Runtime
- `HomeworkRun`: run id, assignment, current stage, status, fix iteration.
- Создавать `.runtime/runs/<run-id>/`.
- Хранить JSON-состояния каждой стадии и рабочие файлы.

## 4. Реестр курсов
- Регистрировать абсолютный путь внешней папки курса.
- Загружать структуру курса и assignments.
- Проверять обязательные папки и права доступа.

## 5. Ingestion материалов
- `MaterialChunk`: material id, text, pages, section, markdown, page images.
- PDF разбивать по страницам.
- Сохранять текст и PNG страниц в `.runtime/courses/`.
- Markdown и текст тоже превращать в chunks.

## 6. Retrieval
- `SearchResult`: chunk id, source, snippet, score, pages.
- Реализовать SQLite FTS5.
- Команды: `search`, `show`, `related`.
- Embeddings пока не добавлять.

## 7. Контракты стадий
- `TheoryPack`: запросы, выдержки, источники, `theory.md`.
- `AssignmentPlan`: связи задач, work units, шаги, проверки.
- `SolutionRevision`: parent, файлы, прочитанные источники, команды.
- `ReviewReport`: passed, findings, severity, location, advice.
- `FixPlan`: findings, target files, действия, проверки.

## 8. Codex adapter
- `AgentExecutor`: start, continue, cwd, prompt, read roots, write roots.
- Отдельные роли: retriever, planner, implementer, reviewer, fix planner, fixer.
- Reviewer работает read-only.
- Implementer и fixer пишут только в workspace.

## 9. Стадии
- Каждая стадия читает входной контракт.
- Каждая стадия пишет JSON и короткий Markdown.
- Стадии не вызывают друг друга напрямую.
- Все prompts хранить отдельно и версионировать.

## 10. Pipeline
```text
theory → planning → implementation → validation → review
       → fix planning → fixing → validation → review → finalization
```
- Ограничить число fix-итераций.
- Сначала обычный Python coordinator.
- LangGraph добавить после рабочего MVP.

## 11. Notebook pipeline
```text
solution.py → Jupytext → solution.ipynb → NBClient → validation
```
- Запускать через `uv` из корня курса.
- Проверять чистый kernel, ошибки, execution counts и пути.
- Нормализовать только технические metadata.

## 12. Валидаторы
- Python: `ruff`, `pytest`.
- Notebook: `nbformat`, NBClient.
- LaTeX: сборка PDF.
- Проверка outputs и запрета изменений `source/`.
- Запрет финализации при blocker/major findings.

## 13. Finalizer
- Только finalizer пишет в `solution/` и `submission/`.
- Копировать только прошедшие validation и review артефакты.
- Сохранять hash опубликованных файлов.

## 14. CLI
- `course add`
- `ingest`
- `solve`
- `resume`
- `inspect`
- `validate`

## 15. Первый end-to-end тест
- Один курс.
- PDF-лекция.
- Две связанные домашки.
- Прошлое решение как контекст.
- Новая домашка с notebook.
- Полный pipeline, один review/fix и публикация.
