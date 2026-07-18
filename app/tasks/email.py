import time

from app.tasks.celery_app import celery_app


@celery_app.task
def send_order_email(order_id: int, email: str) -> str:
    # здесь была бы реальная отправка через SMTP/Resend
    time.sleep(2)  # имитируем долгую операцию
    print(f"[email] Письмо о заказе #{order_id} отправлено на {email}")
    return f"sent:{order_id}"
