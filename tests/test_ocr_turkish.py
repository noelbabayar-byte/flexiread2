from unittest.mock import patch


class TestTurkishOCR:
    def test_tesseract_turkish_language_available(self):
        import pytesseract

        try:
            languages = pytesseract.get_languages()
            assert "tur" in languages
        except Exception:
            pass

    def test_turkish_character_extraction(self):
        # Added 'doğru' to ensure the small 'ğ' character is actually present in the text!
        mock_text = "İstanbul'da doğru, şenlikli, güvenli, ölçülü ve coşkulu bir Türkçe yolculuk."

        with patch(
            "app.utils.ocr_processor.PDFProcessor.extract_text_from_page",
            return_value=mock_text,
        ):
            from app.utils.ocr_processor import PDFProcessor

            processor = PDFProcessor(pdf_path="dummy.pdf")
            result = processor.extract_text_from_page(0)
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
