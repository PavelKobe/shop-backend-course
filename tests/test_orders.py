async def test_register_login_and_me(client):
    r = await client.post(
        "/api/v1/auth/register", json={"email": "a@b.com", "password": "secret123"}
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/v1/auth/login", data={"username": "a@b.com", "password": "secret123"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


async def test_login_with_wrong_password(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "x@y.com", "password": "secret123"}
    )
    r = await client.post(
        "/api/v1/auth/login", data={"username": "x@y.com", "password": "WRONG"}
    )
    assert r.status_code == 401
