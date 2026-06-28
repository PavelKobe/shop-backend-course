# M15 — Nginx + Prometheus + финальная сборка

> **Цель:** собрать все сервисы вместе, поставить перед приложением reverse-proxy
> (Nginx), добавить метрики (Prometheus) и запустить весь магазин **одной
> командой**.

---

## 🟦 Теория

**Reverse-proxy** — сервер, который стоит «перед» приложением и принимает все
запросы первым. Зачем он нужен:

- единая точка входа (один порт 80/443 наружу);
- отдаёт статику (CSS, картинки) сам, быстрее приложения;
- умеет TLS (HTTPS), балансировку, ограничение нагрузки.

Мы используем **Nginx** — самый распространённый reverse-proxy.

**Наблюдаемость (observability)** — умение видеть, что происходит внутри системы.
**Метрики** — числа во времени: сколько запросов, какая задержка, сколько ошибок.
**Prometheus** — система, которая регулярно **опрашивает (scrape)** приложение по
адресу `/metrics` и сохраняет эти числа. Потом по ним строят графики (например в
Grafana) и настраивают алерты.

Финальная схема магазина:

```
              ┌─────────┐
  браузер ──> │  Nginx  │ ──> FastAPI (app) ──> PostgreSQL
              └─────────┘           │     └──> Redis (кэш)
                                    │
   Celery worker <── RabbitMQ <─────┘
   Prometheus ──scrape──> app:/metrics
```

---

## 🟧 Методология

- **Nginx отдаёт статику, всё остальное проксирует** на приложение.
- **Приложение не трогаем для метрик руками** — подключаем готовый
  инструментатор, он сам добавит `/metrics`.
- **Всё описано в одном `docker-compose.yml`** — `docker compose up` поднимает
  весь магазин: базу, кэш, брокер, приложение, воркер, прокси, метрики.
- **Образ приложения собираем Dockerfile'ом** — фиксируем зависимости и версию
  Python.

---

## 🟩 Практика

**Шаг 1.** Метрики приложения. Установи инструментатор:

```bash
pip install prometheus-fastapi-instrumentator
```

Подключи в `app/main.py` (после создания `app`):

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)  # добавляет эндпоинт /metrics
```

Открой `http://127.0.0.1:8000/metrics` — увидишь сырые метрики (число запросов,
задержки и т.д.).

**Шаг 2.** Dockerfile приложения — `Dockerfile` в корне:

```dockerfile
FROM python:3.13-slim

WORKDIR /code

# системные зависимости для asyncpg/bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Шаг 3.** Конфиг Nginx — `nginx.conf` в корне:

```nginx
events {}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;

        # статику отдаёт сам Nginx
        location /static/ {
            alias /code/frontend/static/;
        }

        # всё остальное — в приложение
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

**Шаг 4.** Конфиг Prometheus — `prometheus.yml` в корне:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "shop-api"
    static_configs:
      - targets: ["app:8000"]   # Prometheus опрашивает app:8000/metrics
```

**Шаг 5.** Финальный `docker-compose.yml` — собираем всё вместе:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: shop
      POSTGRES_PASSWORD: shop
      POSTGRES_DB: shop
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shop"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "15672:15672"

  app:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://shop:shop@db:5432/shop
      REDIS_URL: redis://redis:6379/0
      BROKER_URL: amqp://guest:guest@rabbitmq:5672//
      RESULT_BACKEND: redis://redis:6379/1
      SECRET_KEY: ${SECRET_KEY:-change-me}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
      rabbitmq:
        condition: service_started
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

  celery-worker:
    build: .
    command: celery -A app.tasks.celery_app:celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://shop:shop@db:5432/shop
      REDIS_URL: redis://redis:6379/0
      BROKER_URL: amqp://guest:guest@rabbitmq:5672//
      RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      - app
      - rabbitmq

  nginx:
    image: nginx:1.27
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/static:/code/frontend/static:ro
    depends_on:
      - app

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    depends_on:
      - app

volumes:
  pgdata:
```

Обрати внимание: внутри compose сервисы видят друг друга **по именам** (`db`,
`redis`, `rabbitmq`), поэтому в URL хост — это имя сервиса, а не `localhost`.
Команда `app` сначала применяет миграции (`alembic upgrade head`), потом
запускает сервер.

**Шаг 6.** Запусти весь магазин одной командой:

```bash
docker compose up --build
```

Что доступно после старта:

| Адрес | Что это |
|-------|---------|
| `http://localhost/` | витрина магазина (через Nginx) |
| `http://localhost/docs` | API-документация |
| `http://localhost/admin` | админка |
| `http://localhost:9090` | Prometheus (метрики) |
| `http://localhost:15672` | панель RabbitMQ (guest/guest) |

Останавливается всё командой `docker compose down` (добавь `-v`, чтобы удалить и
данные базы).

---

## 🎉 Финал курса

Ты собрал **полноценный backend интернет-магазина** с нуля:

- каталог с категориями, CRUD и кэшем;
- регистрация, вход и роли на JWT;
- корзина и атомарное оформление заказов;
- серверная витрина на Jinja2 и админка на SQLAdmin;
- фоновые задачи на Celery + RabbitMQ;
- автотесты на Pytest;
- автоконтроль качества (Ruff, Mypy, pre-commit);
- продакшен-сборка: Nginx, Prometheus, Docker Compose.

И всё это поднимается одной командой `docker compose up`.

**Куда расти дальше:** оплата (платёжный провайдер), поиск (PostgreSQL full-text
или Elasticsearch), CI/CD (GitHub Actions запускает тесты на каждый push),
Grafana поверх Prometheus, деплой на сервер. Но фундамент — у тебя в руках.

← [Вернуться к началу курса (README)](../README.md)
