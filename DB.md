# База данных — шпаргалка

Всё про PostgreSQL в этом проекте: как устроено, как запускать, чем и как
подключаться, как переключаться между Docker-БД и нативным PostgreSQL и что
делать, если `/health/db` отдаёт 500.

---

## Что где

БД запускается **в Docker-контейнере** (см. [docker-compose.yml](docker-compose.yml)):

| Параметр | Значение |
|---|---|
| Образ | `postgres:16` |
| Имя контейнера | `shop-backend-course-db-1` |
| Пользователь | `shop` |
| Пароль | `shop` |
| База | `shop` |
| Порт (хост → контейнер) | `5432 → 5432` |
| Том с данными | `pgdata` (данные переживают пересоздание контейнера) |

Строка подключения приложения — в [.env](.env):

```
DATABASE_URL=postgresql+asyncpg://shop:shop@localhost:5432/shop
```

Драйвер `asyncpg` (async), движок и сессии — в [app/core/db.py](app/core/db.py),
настройки читаются через [app/core/config.py](app/core/config.py).

---

## Запуск и остановка БД

```powershell
docker compose up -d          # поднять БД в фоне
docker compose ps             # статус (ждём health: healthy)
docker compose stop db        # остановить (данные сохраняются)
docker compose start db       # снова запустить
docker compose down           # удалить контейнер (том pgdata остаётся)
docker compose down -v        # удалить ВМЕСТЕ с данными (том pgdata тоже) — осторожно!
```

Логи и здоровье:

```powershell
docker compose logs -f db
docker inspect -f "{{.State.Health.Status}}" shop-backend-course-db-1
```

---

## Чем подключаться

К контейнерной БД можно обращаться **любым клиентом** — контейнер пробрасывает
порт `5432` на хост, поэтому база видна как обычный `localhost:5432`. `exec` в
контейнер — лишь один из способов, не единственный.

Единые реквизиты для всех клиентов:

```
Host:     localhost   (или 127.0.0.1)
Port:     5432
Database: shop
User:     shop
Password: shop
```

### pgAdmin

1. ПКМ на **Servers** → **Register** → **Server…**
2. **General** → Name: любое (напр. `Shop Docker`)
3. **Connection**: Host `localhost`, Port `5432`, Maintenance database `shop`,
   Username `shop`, Password `shop` (галочка *Save password*)
4. **Save** — таблицы появятся в `shop → Schemas → public` после миграций (M04+).

### DBeaver

Новое соединение → PostgreSQL → те же Host/Port/Database/User/Password → Finish.

### psql

Из контейнера (ничего ставить не нужно):

```powershell
docker exec -it shop-backend-course-db-1 psql -U shop -d shop
```

С хоста, если установлен нативный клиент PostgreSQL:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U shop -h localhost -p 5432 -d shop
```

Полезные команды внутри `psql`: `\l` — список баз, `\dt` — таблицы, `\d table` —
структура таблицы, `\q` — выход.

---

## Проверка работоспособности

Эндпоинт приложения (см. [app/main.py](app/main.py)):

```powershell
uvicorn app.main:app --reload
# затем открыть http://127.0.0.1:8000/health/db  → должно вернуть {"db":1}
```

Быстрая проверка напрямую:

```powershell
docker exec shop-backend-course-db-1 psql -U shop -d shop -c "SELECT 1;"
```

---

## Переключение: Docker-БД ↔ нативный PostgreSQL

> На порту `5432` одновременно работает **только один** Postgres. На этой машине
> установлен ещё и нативный PostgreSQL 16 (служба `postgresql-x64-16`); он
> остановлен, автозапуск переведён в `Manual`, порт занимает контейнер курса.

**Откатиться на нативный PostgreSQL** (PowerShell **от администратора**):

```powershell
docker compose stop db            # освободить 5432
Start-Service postgresql-x64-16   # поднять нативный PG
# подключение: & "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -p 5432
```

**Вернуться на Docker-БД курса:**

```powershell
Stop-Service postgresql-x64-16    # (админ) освободить 5432
docker compose up -d              # поднять контейнер на 5432
```

Данные нативного PG лежат отдельно в `C:\Program Files\PostgreSQL\16\data` и при
переключении не трогаются. Держи в голове, к какому Postgres сейчас подключён
pgAdmin — реквизиты у контейнера (`shop/shop`) и нативного (`postgres/…`) разные.

---

## Если `/health/db` отдаёт 500

**Причина №1 — порт 5432 занят нативным PostgreSQL.** Тогда клиенты с
`localhost:5432` попадают в нативный PG (где нет пользователя/базы `shop`) и
получают `asyncpg ConnectionDoesNotExistError` / `WinError 64/10054`. При этом
`psql` внутри контейнера и healthcheck зелёные. Кто занимает порт:

```powershell
Get-NetTCPConnection -LocalPort 5432 -State Listen | Select-Object OwningProcess
Get-Service postgresql*        # если Running — это нативный PG, останови его (см. выше)
```

**Причина №2 — сервер не перезапущен после правки `.env`.** Флаг `--reload`
следит только за `.py`-файлами; после изменения `.env` перезапусти uvicorn
вручную (Ctrl+C → заново) и запускай его **из корня проекта**.

**Зомби-процессы (Windows).** Фоновые `uvicorn --reload` иногда остаются жить
(обычный kill не убивает дерево WatchFiles), держат порт 8000, и новый сервер
молча не стартует. Снять:

```powershell
taskkill /F /T /PID <pid>
```
