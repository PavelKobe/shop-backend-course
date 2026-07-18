# Code Quality Commands

Памятка для запуска Ruff, Mypy и pre-commit в Windows PowerShell.

## 1. Активировать виртуальное окружение

```powershell
.\.venv\Scripts\Activate.ps1
```

После активации в начале строки терминала должно появиться `(.venv)`.

## 2. Ruff: линтер

Проверить весь проект:

```powershell
ruff check .
```

Проверить и автоматически исправить безопасные ошибки:

```powershell
ruff check . --fix
```

Если окружение не активировано, запускай напрямую:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe check . --fix
```

## 3. Ruff: форматтер

Отформатировать весь проект:

```powershell
ruff format .
```

Если окружение не активировано:

```powershell
.\.venv\Scripts\ruff.exe format .
```

## 4. Mypy: проверка типов

Проверить типы в приложении:

```powershell
mypy app
```

Если окружение не активировано:

```powershell
.\.venv\Scripts\mypy.exe app
```

## 5. pre-commit

Установить git hook один раз после настройки проекта:

```powershell
pre-commit install
```

Проверить конфиг:

```powershell
pre-commit validate-config
```

Запустить все проверки по всем файлам:

```powershell
pre-commit run --all-files
```

После `pre-commit install` проверки будут запускаться автоматически перед каждым
`git commit`.

## 6. Рекомендуемый порядок перед коммитом

```powershell
ruff check . --fix
ruff format .
mypy app
pre-commit run --all-files
```

Если всё прошло без ошибок, можно делать коммит:

```powershell
git add .
git commit -m "fix: описание изменений"
```
