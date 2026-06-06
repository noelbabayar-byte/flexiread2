from fastapi.testclient import TestClient

from app.core.jwt_blacklist import jwt_blacklist
from app.core.security import security_manager


def test_register_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["plan_type"] == "free"
    assert "password_hash" not in data


def test_register_duplicate_email(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": test_user.email, "password": "password123", "full_name": "Test"},
    )

    assert response.status_code == 400


def test_login_success(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401


def test_refresh_token_success(client: TestClient, test_user):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_blacklists_token(client: TestClient, test_user, monkeypatch):
    blacklisted = set()
    monkeypatch.setattr(
        jwt_blacklist, "blacklist_token", lambda jti, exp: blacklisted.add(jti)
    )
    monkeypatch.setattr(jwt_blacklist, "is_blacklisted", lambda jti: jti in blacklisted)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    token = login_response.json()["access_token"]
    payload = security_manager.verify_token(token)

    response = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert payload["jti"] in blacklisted

    me_response = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 401
