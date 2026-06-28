# M09 — Jinja2-витрина (шаблоны готовы)

> **Цель:** подключить серверный рендеринг и отдать пользователю готовые
> HTML-страницы магазина. Сами шаблоны и стиль я подготовил — они лежат в
> папке `frontend/`.

---

## 🟦 Теория

До сих пор backend отдавал JSON — это удобно для приложений, но человек хочет
видеть страницу. **Jinja2** — шаблонизатор: берёт HTML-шаблон с «дырками» и
подставляет в них данные из Python. Браузер получает готовый HTML.

Возможности Jinja2, которые мы используем:

- **Вставка значения:** `{{ product.name }}`
- **Цикл:** `{% for p in products %} ... {% endfor %}`
- **Условие:** `{% if cart_count %} ... {% endif %}`
- **Наследование:** один `base.html` с шапкой и подвалом; страницы наследуют его
  через `{% extends "base.html" %}` и переопределяют блоки.

**Статика** (CSS, картинки) на этапе разработки отдаётся через `StaticFiles`.
В проде её эффективнее раздаёт Nginx — это сделаем в M15.

---

## 🟧 Методология

- **Логика — в Python, шаблон — только отображение.** Не считай суммы в шаблоне.
- **Один `base.html`,** остальные страницы наследуют его — единый вид без копипасты.
- **В `TemplateResponse` обязателен `request`** — Jinja2 в FastAPI этого требует.
- **Витрину держим отдельно от API** (`app/web/`), чтобы JSON-API и HTML-страницы
  не путались.

---

## 🟩 Практика

**Шаг 1.** Установи Jinja2 (если ещё нет) и скопируй готовый фронт:

```bash
pip install jinja2
# шаблоны и стиль уже в репозитории — в папке frontend/
# templates/: base.html, products.html, product.html, cart.html
# static/:    style.css
```

Готовые шаблоны разбирать построчно не нужно — они написаны заранее. Достаточно
понимать: `products.html` ждёт переменную `products` (список товаров),
`product.html` — `product`, `cart.html` — `items` и `total`.

**Шаг 2.** Роуты витрины — `app/web/views.py`:

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_product_service
from app.services.product import ProductNotFound, ProductService

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/", response_class=HTMLResponse)
async def shop_index(
    request: Request,
    service: ProductService = Depends(get_product_service),
):
    products = await service.list(limit=100)
    return templates.TemplateResponse(
        "products.html", {"request": request, "products": products}
    )


@router.get("/p/{product_id}", response_class=HTMLResponse)
async def product_page(
    product_id: int,
    request: Request,
    service: ProductService = Depends(get_product_service),
):
    try:
        product = await service.get(product_id)
    except ProductNotFound:
        return templates.TemplateResponse(
            "products.html",
            {"request": request, "products": []},
            status_code=404,
        )
    return templates.TemplateResponse(
        "product.html", {"request": request, "product": product}
    )
```

**Шаг 3.** Подключи статику и витрину в `app/main.py`:

```python
from fastapi.staticfiles import StaticFiles

from app.web import views

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.include_router(views.router)  # без префикса — это корень сайта
```

**Шаг 4.** Запусти и открой в браузере:

- `http://127.0.0.1:8000/` — витрина каталога (карточки товаров);
- `http://127.0.0.1:8000/p/1` — страница товара.

Если каталог пуст — наполни его сидом из M05 или через админку из M10.

> **Как шаблон получает данные.** В `TemplateResponse` мы передаём словарь
> `{"request": ..., "products": products}`. Внутри `products.html` это становится
> переменной `products`, по которой бежит цикл `{% for p in products %}`.

**Что я подготовил за тебя (в `frontend/`):**

- `base.html` — каркас с шапкой, ссылкой на корзину и подвалом.
- `products.html` — адаптивная сетка карточек товаров.
- `product.html` — карточка товара с кнопкой «В корзину».
- `cart.html` — таблица корзины с кнопкой «Оформить заказ».
- `style.css` — чистый адаптивный стиль без фреймворков.

Корзину на странице (`cart.html`) можно подключить так же, как каталог: добавь
роут `/cart`, который берёт позиции из `CartService` и рендерит шаблон. Это
хорошая самостоятельная практика — все нужные кусочки у тебя уже есть.

---

> **Итог модуля.** У магазина появилось человеческое лицо: серверный рендеринг
> через Jinja2 с готовыми шаблонами и стилем. Покупатель видит каталог и товары в
> браузере. Теперь дадим админу удобный инструмент управления.

**Дальше:** [M10 — SQLAdmin: админка](M10-sqladmin.md)
