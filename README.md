# Study Agent

Многоэтапный пайплайн вокруг Codex:

```text
theory retrieval -> planning -> implementation -> review -> fix planning -> fixing
```

## Репозиторий агента

```text
study-agent/
├── src/study_agent/
│   ├── domain/        # dataclasses и контракты
│   ├── application/   # стадии и пайплайны
│   ├── ports/         # интерфейсы внешних систем
│   ├── adapters/      # Codex, SQLite, PDF, Jupyter, RAG
│   ├── prompts/       # prompts для стадий
│   ├── skills/        # Codex skills
│   └── cli/           # команды запуска
├── tests/             # тесты
├── docs/              # краткие ADR и схемы
├── .runtime/          # индексы, runs, cache, logs; целиком в gitignore
├── pyproject.toml     # uv-проект агента
└── uv.lock            # фиксируется в Git
```

## Внешняя папка курса

Папка курса может лежать где угодно и регистрируется по абсолютному пути.

```text
course-root/
├── materials/
│   ├── lectures/      # презентации и лекции
│   ├── seminars/      # семинары и примеры
│   ├── textbooks/     # большие учебники для RAG
│   ├── articles/      # статьи
│   ├── references/    # формулы и справочники
│   └── extras/        # прочие материалы
├── assignments/
│   └── <assignment-id>/
│       ├── source/    # условие, данные, starter files; read-only
│       ├── solution/  # проверенное решение для будущего контекста
│       └── submission/# готовые файлы для LMS
├── instructions/      # правила курса и обозначения
├── pyproject.toml     # uv-окружение курса
└── uv.lock            # зависимости курса
```

Все папки внутри `materials/` необязательны.

Python и Jupyter внутри курса запускаются только через `uv` из корня курса.

## Runtime

```text
.runtime/
├── courses/           # индексы и обработанные PDF
├── runs/              # состояния стадий и рабочие файлы
├── cache/             # временный cache
└── logs/              # логи
```

`.runtime/` не содержит единственную копию исходных материалов и может быть удалена.
