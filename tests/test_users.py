from fastapi.testclient import TestClient


def test_get_current_user_profile(client: TestClient, auth_headers, test_user):
    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == test_user.email


def test_get_quota(client: TestClient, auth_headers):
    response = client.get("/api/v1/users/quota", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["remaining"] == 50
    assert data["total"] == 50
    assert data["plan_type"] == "free"


def test_get_profile(client: TestClient, auth_headers, test_user):
    response = client.get("/api/v1/users/profile", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == test_user.email
    assert "ocr_quota_reset_date" in response.json()
