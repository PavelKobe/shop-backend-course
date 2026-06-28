# M12 — Celery + RabbitMQ: фоновые задачи

> **Цель:** выносить долгие операции (например отправку письма о заказе) в фон,
> чтобы пользователь не ждал, а получал быстрый ответ.

---

## 🟦 Теория

Когда покупатель оформляет заказ, мы хотим отправить ему письмо. Но отправка
письма может занять секунды, а пользователь не должен столько ждать ответа.
Решение: положить задачу «отправить письмо» в **очередь** и ответить пользователю
сразу, а письмо отправит отдельный процесс позже.

Участники:

- **Celery** — система фоновых задач для Python: ты пишешь обычную функцию,
  помечаешь её `@celery.task`, и её можно запускать «в фоне».
- **Брокер (RabbitMQ)** — очередь, через которую задачи передаются от приложения
  к воркеру. Приложение кладёт задачу, воркер забирает.
- **Backend результата (Redis)** — куда воркер кладёт результат выполнения (если
  он нужен). Redis у нас уже есть из M11.
- **Worker** — отдельный процесс, который крутится рядом и выполняет задачи.

> **Пайплайн задач, а не «агент».** Здесь нам нужен именно простой конвейер
> «положил задачу → воркер выполнил». Никакого цикла принятия решений не требуется
> — это важно понимать, чтобы не усложнять архитектуру там, где не нужно.

---

## 🟧 Методология

- **В задачу передавай простые данные (id), а не объекты** SQLAlchemy — их нельзя
  сериализовать в очередь.
- **Задачи делай идемпотентными** — повторный запуск не должен ломать данные
  (важно, потому что брокер может доставить задачу повторно при сбое).
- **Не запускай тяжёлое в обработчике запроса** — только ставь задачу в очередь.
- **RabbitMQ и worker — отдельные сервисы** в docker-compose.

---

## 🟩 Практика

**Шаг 1.** Установи и добавь RabbitMQ в `docker-compose.yml`:

```bash
pip install "celery>=5.3" "flower>=2.0"
```

```yaml
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"     # порт брокера
      - "15672:15672"   # веб-панель управления
```

Добавь в `app/core/config.py`:

```python
    broker_url: str = "amqp://guest:guest@localhost:5672//"
    result_backend: str = "redis://localhost:6379/1"
```

**Шаг 2.** Приложение Celery — `app/tasks/celery_app.py`:

```python
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "shop",
    broker=settings.broker_url,
    backend=settings.result_backend,
)
celery_app.conf.task_track_started = True
# чтобы Celery нашёл задачи
celery_app.autodiscover_tasks(["app.tasks"])
```

**Шаг 3.** Сама задача — `app/tasks/email.py`:

```python
import time

from app.tasks.celery_app import celery_app


@celery_app.task
def send_order_email(order_id: int, email: str) -> str:
    # здесь была бы реальная отправка через SMTP/Resend
    time.sleep(2)  # имитируем долгую операцию
    print(f"[email] Письмо о заказе #{order_id} отправлено на {email}")
    return f"sent:{order_id}"
```

**Шаг 4.** Поставь задачу при оформлении заказа — в `app/api/v1/cart.py`,
в обработчике `checkout`, после успешного создания заказа:

```python
from app.tasks.email import send_order_email

@router.post("/checkout", response_model=OrderRead)
async def checkout(user=Depends(get_current_user), service=Depends(get_cart_service)):
    try:
        order = await service.checkout(user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # .delay() ставит задачу в очередь и сразу возвращает управление
    send_order_email.delay(order.id, user.email)
    return order
```

`.delay(...)` — это и есть «запустить в фоне». Ответ пользователю уходит мгновенно,
письмо отправится воркером.

**Шаг 5.** Запусти воркер (в отдельном терминале, окружение активировано):

```bash
celery -A app.tasks.celery_app:celery_app worker --loglevel=info
```

Подними RabbitMQ и Redis (`docker compose up -d rabbitmq redis`), оформи заказ —
в логах воркера через ~2 секунды появится строка об отправке письма.

**Шаг 6.** Мониторинг через Flower (веб-панель задач):

```bash
celery -A app.tasks.celery_app:celery_app flower
# открой http://localhost:5555
```

Веб-панель RabbitMQ доступна на `http://localhost:15672` (логин/пароль
`guest`/`guest`).

> Сервис `celery-worker` мы добавим в финальный `docker-compose.yml` в M15, чтобы
> воркер поднимался вместе со всем магазином.

---

> **Итог модуля.** Долгие операции уехали в фон через Celery + RabbitMQ: ответ
> пользователю мгновенный, письма шлёт воркер. Магазин функционально завершён.
> Осталось сделать его надёжным: тесты, качество кода и продакшен-сборка.

**Дальше:** [M13 — Тестирование: Pytest](M13-pytest.md)
