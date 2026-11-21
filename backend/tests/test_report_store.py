import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import report_store
from backend.main import app
from backend.report_analyzer import clear_report_session


ROOT = Path(__file__).resolve().parents[2]
CASE_ID = json.loads((ROOT / "src/data/cases.json").read_text(encoding="utf-8"))["cases"][0]["case_id"]


class ReportStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        data_directory = Path(self.temporary_directory.name) / "private-reports"
        self.data_patch = patch.object(report_store, "REPORT_DATA_DIR", data_directory)
        self.database_patch = patch.object(report_store, "DATABASE_PATH", data_directory / "reports.sqlite3")
        self.data_patch.start()
        self.database_patch.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.database_patch.stop()
        self.data_patch.stop()
        self.temporary_directory.cleanup()

    def test_upload_is_opt_in_linkable_and_can_be_unlinked_or_deleted(self):
        response = self.client.post(
            "/api/reports/analyze",
            files={"file": ("synthetic.txt", b"SYNTHETIC TEST DOCUMENT. The distal femur has a lytic lesion. MRI follow-up is recommended.", "text/plain")},
            data={"case_id": CASE_ID},
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        report_id = result["report_id"]
        self.assertEqual(result["persistence"]["case_id"], CASE_ID)
        self.assertTrue(result["persistence"]["stored_locally"])

        listed = self.client.get("/api/reports", params={"case_id": CASE_ID})
        self.assertEqual([item["report_id"] for item in listed.json()["reports"]], [report_id])
        stored = self.client.get(f"/api/reports/item/{report_id}")
        self.assertEqual(stored.status_code, 200)
        self.assertIn("distal femur", stored.json()["original_text"])

        clear_report_session(report_id)
        question = self.client.post("/api/reports/ask", json={"report_id": report_id, "question": "What does the report say about the distal femur lesion?"})
        self.assertEqual(question.status_code, 200, question.text)
        self.assertEqual(question.json()["answer_status"], "source_excerpt")

        unlinked = self.client.patch(f"/api/reports/{report_id}/association", json={"case_id": None})
        self.assertEqual(unlinked.status_code, 200)
        self.assertIsNone(unlinked.json()["case_id"])
        self.assertEqual(self.client.get("/api/reports", params={"case_id": CASE_ID}).json()["reports"], [])

        deleted = self.client.delete(f"/api/reports/{report_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])
        self.assertFalse((report_store.REPORT_DATA_DIR / report_id).exists())
        self.assertEqual(self.client.get(f"/api/reports/item/{report_id}").status_code, 404)

    def test_unknown_case_is_rejected_without_storing_report(self):
        response = self.client.post(
            "/api/reports/analyze",
            files={"file": ("synthetic.txt", b"SYNTHETIC TEST DOCUMENT with report text.", "text/plain")},
            data={"case_id": "not-a-real-case"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(report_store.list_reports(), [])

    def test_unassociated_upload_does_not_attach_to_any_case(self):
        response = self.client.post(
            "/api/reports/analyze",
            files={"file": ("synthetic.txt", b"SYNTHETIC TEST DOCUMENT with standalone report text.", "text/plain")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["persistence"]["case_id"])
        self.assertEqual(report_store.list_reports(CASE_ID), [])

    def test_rag_cannot_include_report_under_a_different_case_id(self):
        response = self.client.post(
            "/api/reports/analyze",
            files={"file": ("synthetic.txt", b"SYNTHETIC TEST DOCUMENT. The distal femur has a lesion.", "text/plain")},
            data={"case_id": CASE_ID},
        )
        report_id = response.json()["report_id"]
        other_case = json.loads((ROOT / "src/data/cases.json").read_text(encoding="utf-8"))["cases"][1]["case_id"]
        with patch("backend.rag_assistant.answer_question", return_value={"status": "answered", "answer": "ok", "citations": []}) as answer:
            bad = self.client.post("/api/assistant/chat", json={"question": "What does the report say about the distal femur?", "case_id": other_case, "report_id": report_id})
            self.assertEqual(bad.status_code, 422)
            good = self.client.post("/api/assistant/chat", json={"question": "What does the report say about the distal femur?", "case_id": CASE_ID, "report_id": report_id})
        self.assertEqual(good.status_code, 200)
        self.assertTrue(answer.call_args.kwargs["report_context"]["has_matching_passages"])


if __name__ == "__main__":
    unittest.main()
