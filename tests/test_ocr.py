from pathlib import Path

import fitz

from app.utils.ocr_processor import PDFProcessor, process_pdf_file


def test_pdf_processor_extracts_direct_text(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "FlexiRead direct text extraction test " * 3)
    document.save(pdf_path)
    document.close()

    with PDFProcessor(str(pdf_path)) as processor:
        page_data = processor.process_page(0)

    assert page_data["method"] == "direct"
    assert "FlexiRead" in page_data["text"]


def test_process_pdf_file_returns_pages_and_summary(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "FlexiRead PDF processing integration test " * 3)
    document.save(pdf_path)
    document.close()

    result, error = process_pdf_file(str(pdf_path))

    assert error is None
    assert result["summary"]["total_pages"] == 1
    assert len(result["pages"]) == 1
    assert result["pages"][0]["method"] == "direct"
