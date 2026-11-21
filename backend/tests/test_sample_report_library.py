import json
from pathlib import Path
import shutil
import unittest

from backend.report_analyzer import ReportProcessingError, process_report


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_ROOT = ROOT / "sample_reports"
SYNTHETIC_NOTICE = "SYNTHETIC TEST DOCUMENT"


class SampleReportLibraryTests(unittest.TestCase):
    def test_published_case_library_has_more_than_thirty_licensed_readable_sources(self):
        sources = json.loads((ROOT / "src/data/openAccessReports.json").read_text(encoding="utf-8"))
        self.assertGreater(len(sources), 30)
        self.assertEqual(len({item["id"] for item in sources}), len(sources))
        for item in sources:
            self.assertEqual(item["license"], "CC BY 4.0")
            content = (ROOT / "public" / item["path"].lstrip("/")).read_bytes()
            result = process_report(item["id"] + ".txt", content)
            self.assertIn(item["url"], result["original_text"])
            self.assertIn(item["title"], result["original_text"])
            self.assertIn("CC BY 4.0", result["original_text"])

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((SAMPLE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    def test_library_has_many_distinct_synthetic_scenarios_and_formats(self):
        documents = self.manifest["documents"]
        self.assertEqual(self.manifest["unique_scenarios"], 25)
        self.assertGreaterEqual(len(documents), 25)
        self.assertTrue(all(item["source_status"].startswith("synthetic") for item in documents))
        self.assertTrue(all(item["license"] == "Project-created synthetic content" for item in documents))
        self.assertTrue(all((SAMPLE_ROOT / item["path"]).is_file() for item in documents))
        self.assertTrue(any(item["format"] == "TXT" for item in documents))
        self.assertTrue(any(item["format"] == "PDF" for item in documents))
        self.assertTrue(any(item["format"] == "image-only PDF" for item in documents))
        self.assertEqual((SAMPLE_ROOT / "synthetic/incomplete/empty_report.txt").stat().st_size, 0)

    def test_text_reports_are_readable_and_processed_from_their_actual_contents(self):
        txt_paths = [SAMPLE_ROOT / item["path"] for item in self.manifest["documents"] if item["format"] == "TXT"]
        self.assertEqual(len(txt_paths), 25)
        observed_texts = set()
        for path in txt_paths:
            source = path.read_text(encoding="utf-8")
            self.assertIn(SYNTHETIC_NOTICE, source, path.name)
            result = process_report(path.name, source.encode("utf-8"))
            self.assertEqual(result["original_text"], source.strip())
            self.assertTrue(result["report_id"])
            observed_texts.add(result["original_text"])
        self.assertEqual(len(observed_texts), 25)

    def test_text_pdf_variants_extract_notice_and_source_text(self):
        pdf_paths = [SAMPLE_ROOT / item["path"] for item in self.manifest["documents"] if item["format"] == "PDF"]
        for path in pdf_paths:
            result = process_report(path.name, path.read_bytes())
            self.assertIn(SYNTHETIC_NOTICE, result["original_text"], path.name)
            self.assertEqual(result["document"]["format"], "PDF")

    def test_scanned_style_pdf_uses_ocr_or_returns_an_explicit_error(self):
        scan_path = SAMPLE_ROOT / "synthetic/scanned_ocr/simple_bone_cyst_scanned_style.pdf"
        if shutil.which("tesseract"):
            result = process_report(scan_path.name, scan_path.read_bytes())
            self.assertTrue(result["original_text"].strip())
        else:
            with self.assertRaises(ReportProcessingError) as raised:
                process_report(scan_path.name, scan_path.read_bytes())
            self.assertRegex(str(raised.exception).lower(), "ocr")

    def test_empty_fixture_is_rejected_instead_of_summarized(self):
        path = SAMPLE_ROOT / "synthetic/incomplete/empty_report.txt"
        with self.assertRaises(ReportProcessingError):
            process_report(path.name, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
