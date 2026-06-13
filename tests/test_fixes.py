"""
Regression tests for the critical-issue fixes:

- Refresh token rotation + revocation of the presented token
- get_book_content returning the actual processed content from S3
- Atomic claim on process so concurrent calls cannot double-enqueue
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.v1.endpoints import books as books_module
from app.models.book import Book, BookStatus


def _login(client: TestClient, test_user) -> dict:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    assert res.status_code == 200
    return res.json()


def test_refresh_rotates_and_revokes_old_token(client: TestClient, test_user):
    tokens = _login(client, test_user)
    old_refresh = tokens["refresh_token"]

    res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    # Rotation: a brand-new refresh token is issued.
    assert body["refresh_token"] != old_refresh

    # The presented refresh token is now revoked and cannot be replayed.
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401


def test_refresh_rejected_for_inactive_user(client: TestClient, test_user, db):
    tokens = _login(client, test_user)
    test_user.is_active = False
    db.commit()

    res = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert res.status_code == 401


def test_get_book_content_returns_pages(
    client: TestClient, auth_headers, test_user, db
):
    book = Book(
        title="Doc",
        original_filename="doc.pdf",
        status=BookStatus.COMPLETED,
        progress_percentage=100,
        total_pages=2,
        processed_pages=2,
        original_pdf_url="s3://flexiread-test/uploads/doc.pdf",
        parsed_content_url="s3://flexiread-test/processed/u/b/content.json",
        user_id=test_user.id,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    fake_content = {
        "metadata": {"title": "Doc", "author": "Tester"},
        "summary": {"total_pages": 2, "ocr_pages": 1},
        "pages": [
            {
                "page_number": 1,
                "text": "Hello world.",
                "method": "direct",
                "confidence": 1.0,
            },
            {"page_number": 2, "text": "OCR page.", "method": "ocr", "confidence": 0.8},
        ],
    }

    with patch.object(
        books_module.s3_storage, "download_json", return_value=fake_content
    ):
        res = client.get(f"/api/v1/books/{book.id}/content", headers=auth_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["total_pages"] == 2
    assert data["metadata"]["author"] == "Tester"
    assert len(data["pages"]) == 2
    assert data["pages"][0]["page_number"] == 1


def test_duplicate_process_returns_409(client: TestClient, auth_headers, test_user, db):
    book = Book(
        title="ToProcess",
        original_filename="x.pdf",
        status=BookStatus.PENDING,
        original_pdf_url="s3://flexiread-test/uploads/x.pdf",
        user_id=test_user.id,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    fake_task = MagicMock()
    fake_task.id = "task-123"

    with patch.object(books_module.process_pdf_task, "delay", return_value=fake_task):
        first = client.post(f"/api/v1/books/process/{book.id}", headers=auth_headers)
        second = client.post(f"/api/v1/books/process/{book.id}", headers=auth_headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
