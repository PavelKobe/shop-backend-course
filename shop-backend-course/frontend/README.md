# Готовый фронтенд (Jinja2)

Эти шаблоны и стиль подготовлены заранее — в модуле **M09** ты подключаешь их к
FastAPI и наполняешь данными из своих сервисов. Самому верстать не нужно.

- `templates/base.html` — каркас с шапкой, корзиной, подвалом; остальные страницы его наследуют.
- `templates/products.html` — витрина каталога (сетка карточек).
- `templates/product.html` — карточка товара с кнопкой «В корзину».
- `templates/cart.html` — корзина с таблицей и оформлением заказа.
- `static/style.css` — чистый адаптивный стиль без фреймворков.

**Подключение в M09:**

```python
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

templates = Jinja2Templates(directory="frontend/templates")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
```
