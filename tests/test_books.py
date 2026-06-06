from fastapi.testclient import TestClient

from app.models.book import Book, BookStatus


def test_upload_url(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/books/upload-url",
        json={"filename": "test.pdf", "file_size": 1024, "title": "Test PDF"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert "presigned_url" in data
    assert "s3_key" in data


def test_upload_url_rejects_non_pdf(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/books/upload-url",
        json={"filename": "test.txt", "file_size": 1024},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_get_book_status(client: TestClient, auth_headers, test_user, db):
    book = Book(
        title="Test Book",
        original_filename="test.pdf",
        status=BookStatus.COMPLETED,
        progress_percentage=100,
        total_pages=10,
        processed_pages=10,
        original_pdf_url="s3://flexiread-test/uploads/test.pdf",
        parsed_content_url="s3://flexiread-test/processed/content.json",
        user_id=test_user.id,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    response = client.get(f"/api/v1/books/{book.id}/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["progress_percentage"] == 100
