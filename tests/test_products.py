async def test_create_product_requires_auth(client):
    r = await client.post(
        "/api/v1/products", json={"name": "Чайник", "price": "1990.00"}
    )
    assert r.status_code == 401
