import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.report_analyzer import ReportProcessingError, answer_report_question, process_report


REPORT_TEXT = (
    "Radiograph of the distal femur demonstrates a 4 cm lytic lesion with a narrow zone of transition. "
    "The report mentions osteosarcoma in the differential. Recommend MRI and orthopedic oncology follow-up."
)


class ReportAnalyzerTests(unittest.TestCase):
    def test_txt_extracts_explicit_source_findings_and_source_only_summary(self):
        result = process_report("sample.txt", REPORT_TEXT.encode("utf-8"))
        self.assertEqual(result["original_text"], REPORT_TEXT)
        self.assertEqual(result["extracted_findings"]["anatomical_location"], ["distal femur"])
        self.assertEqual(result["extracted_findings"]["mentioned_diagnosis_terms"], ["osteosarcoma"])
        self.assertTrue(result["extracted_findings"]["recommendations_and_follow_up"])
        summary_text = " ".join(item["text"] for item in result["summary"]["statements"])
        self.assertIn("Radiograph of the distal femur", summary_text)
        self.assertEqual(result["summary"]["method"], "extractive; statements are copied from the uploaded report")
        self.assertEqual(result["terminology"][0]["definition_type"], "general terminology, not a case-specific interpretation")

    def test_question_answers_quote_only_matching_uploaded_report(self):
        result = process_report("sample.txt", REPORT_TEXT.encode("utf-8"))
        found = answer_report_question(result["report_id"], "What follow-up is recommended?")
        self.assertEqual(found["answer_status"], "source_excerpt")
        self.assertIn("Recommend MRI and orthopedic oncology follow-up.", found["answer"])
        absent = answer_report_question(result["report_id"], "What was the patient's blood pressure?")
        self.assertEqual(absent["answer_status"], "not_found_in_source")
        self.assertIn("does not contain enough matching text", absent["answer"])

    def test_empty_binary_and_unsupported_documents_return_clear_errors(self):
        for filename, content in (("empty.txt", b""), ("image.txt", b"\x00\x01\x02"), ("record.docx", b"text"), ("bad.pdf", b"not a pdf")):
            with self.subTest(filename=filename), self.assertRaises(ReportProcessingError):
                process_report(filename, content)

    def test_pdf_extracts_text_when_pymupdf_is_available(self):
        try:
            import pymupdf as fitz
        except ImportError:
            self.skipTest("PyMuPDF is not installed in this local runtime")
        document = fitz.open()
        page = document.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 520, 220), REPORT_TEXT, fontsize=11)
        pdf_bytes = document.tobytes()
        document.close()
        result = process_report("source.pdf", pdf_bytes)
        self.assertEqual(result["document"]["format"], "PDF")
        self.assertIn("osteosarcoma", result["original_text"].casefold())
        self.assertEqual(result["document"]["page_count"], 1)

    def test_legacy_upload_and_report_question_endpoints_are_disabled(self):
        client = TestClient(app)
        response = client.post("/api/reports/analyze", files={"file": ("sample.txt", REPORT_TEXT.encode(), "text/plain")})
        self.assertEqual(response.status_code, 403, response.text)
        self.assertNotIn(REPORT_TEXT, response.text)
        question = client.post("/api/reports/ask", json={"report_id": "0"*32, "question": "What does it say about the lesion?"})
        self.assertEqual(question.status_code, 403, question.text)
        bad = client.post("/api/reports/analyze", files={"file": ("scan.docx", b"doc", "application/octet-stream")})
        self.assertEqual(bad.status_code, 403)


if __name__ == "__main__":
    unittest.main()
