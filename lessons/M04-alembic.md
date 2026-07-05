# M04 — Alembic: миграции базы

> **Цель:** научиться управлять схемой БД версиями — создавать таблицы и
> изменять их через миграции, а не руками.

---

## 🟦 Теория

Схема базы со временем меняется: добавляются таблицы, столбцы, индексы. Если
менять базу руками, на втором ПК (или у коллеги) она окажется другой. **Миграции**
решают это: каждое изменение схемы — отдельный пронумерованный файл, который
можно применить и откатить.

**Alembic** — инструмент миграций для SQLAlchemy. Ключевые понятия:

- **Ревизия** — один файл миграции с уникальным id и ссылкой на предыдущую
  (`down_revision`). Так выстраивается цепочка версий.
- **`upgrade()`** — что сделать при применении (создать таблицу).
- **`downgrade()`** — как откатить (удалить таблицу).
- **`autogenerate`** — Alembic сам сравнивает твои модели с реальной базой и
  пишет черновик миграции.

---

## 🟧 Методология

- **Каждое изменение модели → новая миграция.** Не правь уже применённые файлы.
- **Всегда читай сгенерированный файл глазами.** `autogenerate` — помощник, а не
  истина: он иногда пропускает переименования или типы.
- **Имя миграции — осмысленное:** `-m "create products table"`.
- **На второй машине схема ставится одной командой** `alembic upgrade head` —
  ради этого всё и затевалось.

---

## 🟩 Практика

**Шаг 1.** Установи и инициализируй Alembic:

```bash
pip install alembic
alembic init -t async alembic
```

Шаблон `-t async` сразу создаёт асинхронную заготовку. Появится папка `alembic/`
и файл `alembic.ini`.

**Шаг 2.** В `alembic.ini` убери жёсткую строку подключения — мы возьмём её из
настроек. Найди строку `sqlalchemy.url = ...` и оставь её пустой:

```ini
sqlalchemy.url =
```

**Шаг 3.** Настрой `alembic/env.py`, чтобы он знал про наши модели и брал URL из
конфигурации. Ключевые правки (добавь импорты сверху и подставь metadata/URL):

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context

from app.core.config import get_settings
from app.models.base import Base
# ВАЖНО: импортируем все модели, чтобы autogenerate их «увидел»
from app.models.product import Product  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
```

> Главное, что мы сделали: (1) подставили `database_url` из настроек,
> (2) задали `target_metadata = Base.metadata`, (3) импортировали модель
> `Product`. Без импорта моделей Alembic их не найдёт.

**Шаг 4.** Сгенерируй первую миграцию (база из M03 должна быть запущена):

```bash
alembic revision --autogenerate -m "create products table"
```

В `alembic/versions/` появится файл. **Открой его** и проверь, что в `upgrade()`
создаётся таблица `products` со столбцами `id`, `name`, `price`, `description`.

**Шаг 5.** Применить миграцию:

```bash
alembic upgrade head
```

`head` — это «самая свежая ревизия». Теперь таблица реально создана в PostgreSQL.

**Полезные команды:**

```bash
alembic current          # на какой ревизии сейчас база
alembic history          # вся цепочка миграций
alembic downgrade -1     # откатить на одну ревизию назад
alembic upgrade head     # накатить все до последней
```

**Шаг 6.** Проверь, что таблица создана:

```bash

```

Увидишь описание столбцов таблицы `products`.

---

> **Итог модуля.** Схема базы теперь под контролем версий. На любом ПК достаточно
> `alembic upgrade head`, чтобы получить идентичную структуру. Дальше расширим
> доменную модель: добавим категории и связи.

**Дальше:** [M05 — Доменная модель: товары, категории, связи](M05-доменная-модель.md)
