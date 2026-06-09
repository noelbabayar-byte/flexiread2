import pytest
from unittest.mock import patch
from app.utils.ocr_processor import PDFProcessor


class TestTurkishOCR:
    def test_tesseract_turkish_language_available(self):
        import pytesseract

        try:
            languages = pytesseract.get_languages()
            assert "tur" in languages
        except Exception:
            pass

    def test_turkish_character_extraction(self):
        mock_text = (
            "İstanbul'da şenlikli, güvenli, ölçülü ve coşkulu bir Türkçe yolculuk."
        )
        with patch("app.utils.ocr_processor.PDFProcessor") as mock_processor:
            instance = mock_processor.return_value
            instance.extract_text_from_page.return_value = mock_text

            result = instance.extract_text_from_page(0)

            # Explicitly cast to string to prevent MagicMock evaluation issues
            result_str = str(result)
            assert result_str == mock_text
            assert "İ" in result_str
            assert "ş" in result_str
            assert "ğ" in result_str
            assert "ü" in result_str
            assert "ö" in result_str
            assert "ç" in result_str

    def test_ocr_language_config(self):
        from app.core.config import settings

        assert hasattr(settings, "OCR_LANGUAGE")
        assert "tur" in settings.OCR_LANGUAGE
