import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.rag_assistant import (
    MIN_SIMILARITY, RAGUnavailable, _build_case_context, _lexical_score, answer_question,
)
from backend.rag_ingest import _nci_text, _pmc_text, _split_text
from backend.report_analyzer import select_report_context


class FakeEmbedder:
    def encode(self, texts, **kwargs):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeCollection:
    def count(self):
        return 2

    def query(self, **kwargs):
        return {
            "documents": [[
                "Osteosarcoma is a primary malignant bone tumour. Diagnosis uses imaging and biopsy in specialist settings.",
                "Ewing sarcoma is another primary malignant bone tumour that commonly affects children and adolescents.",
            ]],
            "metadatas": [[
                {"title": "Bone Cancer—Health Professional Version", "author_or_institution": "NCI", "url": "https://www.cancer.gov/types/bone/hp", "license": "NCI text reuse policy", "publication_date": "2025", "section": "Diagnosis"},
                {"title": "Ewing Sarcoma Treatment", "author_or_institution": "NCI", "url": "https://www.cancer.gov/types/bone/hp/ewing-treatment-pdq", "license": "NCI text reuse policy", "publication_date": "2025", "section": "General information"},
            ]],
            "distances": [[0.12, 0.18]],
        }


class RAGAssistantTests(unittest.TestCase):
    def test_case_summary_and_heatmap_do_not_require_literature_retrieval(self):
        with patch("backend.rag_assistant._retrieve", side_effect=AssertionError("Unexpected literature lookup")):
            summary = answer_question("Explain the available information for BTXRD-IMG001868.")
            heatmap = answer_question("Explain what the heatmap is showing", case_id="BTXRD-IMG001868",
                                      model_result={"case_id": "BTXRD-IMG001868", "image_id": "IMG001868.jpeg",
                                                    "prediction": "Normal", "confidence": 0.9, "gradcam_available": True})
        self.assertEqual(summary["status"], "answered")
        self.assertIn("BTXRD-IMG001868", summary["answer"])
        self.assertEqual(summary["citations"][0]["citation_id"], "CASE")
        self.assertIn("bright yellow", heatmap["answer"])
        self.assertIn("Normal prediction", heatmap["answer"])
        self.assertFalse(heatmap["case_context"]["visual_image_provided_to_language_model"])

    def test_conflicting_explicit_case_id_is_rejected(self):
        with self.assertRaises(ValueError):
            answer_question("Explain BTXRD-IMG001350", case_id="BTXRD-IMG001868")

    def test_selected_case_context_is_manifest_derived_and_excludes_image_pixels(self):
        context = _build_case_context("BTXRD-IMG001868", {
            "case_id": "BTXRD-IMG001868", "image_id": "IMG001868.jpeg", "prediction": "Normal",
            "confidence": 0.62, "probabilities": {"Normal": 0.62}, "model_version": "test-version",
            "gradcam_available": True,
        })
        self.assertEqual(context["source_label"], "Normal")
        self.assertEqual(context["image_id"], "IMG001868.jpeg")
        self.assertFalse(context["visual_image_provided_to_language_model"])
        self.assertIsNone(context["associated_report"])
        self.assertEqual(context["model_analysis"]["model_version"], "test-version")
        self.assertIn("does not establish a tumour boundary", context["gradcam_note"])

    def test_mismatched_model_result_is_not_attached_to_selected_case(self):
        context = _build_case_context("BTXRD-IMG001868", {
            "case_id": "BTXRD-OTHER", "image_id": "IMG001868.jpeg", "prediction": "Malignant",
        })
        self.assertIsNone(context["model_analysis"])

    def test_explicit_report_context_is_selected_from_matching_source_sentences(self):
        report = {
            "report_id": "0123456789abcdef0123456789abcdef",
            "document": {"filename": "synthetic.txt"},
            "pages": [{"page_number": 2, "method": "plain_text", "text": "The synthetic report states the distal femur contains a lytic lesion. MRI correlation is recommended."}],
        }
        context = select_report_context(report, "What does the distal femur MRI show?")
        self.assertTrue(context["has_matching_passages"])
        self.assertIn("distal femur", context["excerpt_text"])
        self.assertEqual(context["excerpts"][0]["page_number"], 2)
        unrelated = select_report_context(report, "What is the weather? ")
        self.assertFalse(unrelated["has_matching_passages"])

    def test_report_qa_ignores_generic_question_words_when_ranking_passages(self):
        from backend.report_analyzer import answer_report_question, process_report

        report = process_report("qa.txt", b"The distal femur contains a lytic lesion. No aggressive periosteal reaction is described.")
        answer = answer_report_question(report["report_id"], "What finding is described at the distal femur?")
        self.assertEqual(len(answer["source_excerpts"]), 1)
        self.assertIn("distal femur", answer["source_excerpts"][0]["text"].lower())

    def test_unknown_case_and_empty_question_fail_closed(self):
        with self.assertRaises(ValueError):
            _build_case_context("not-a-case", None)
        with self.assertRaises(ValueError):
            answer_question("   ")

    def test_hybrid_lexical_component_reacts_to_domain_terms(self):
        relevant = "Osteosarcoma diagnosis includes biopsy after imaging."
        unrelated = "Follow-up methods for unrelated symptoms and care."
        self.assertGreater(_lexical_score(["osteosarcoma", "biopsy"], relevant), _lexical_score(["osteosarcoma", "biopsy"], unrelated))

    def test_retrieval_gate_returns_insufficient_instead_of_calling_generator(self):
        with patch("backend.rag_assistant._runtime", return_value=(FakeCollection(), FakeEmbedder(), object())), \
             patch("backend.rag_assistant.MIN_SIMILARITY", 0.95), \
             patch("backend.rag_assistant._generate") as generator:
            result = answer_question("Explain osteosarcoma diagnosis")
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["citations"], [])
        generator.assert_not_called()

    def test_generated_citations_must_be_retrieved_source_ids(self):
        with patch("backend.rag_assistant._runtime", return_value=(FakeCollection(), FakeEmbedder(), object())), \
             patch("backend.rag_assistant.MIN_SIMILARITY", MIN_SIMILARITY), \
             patch("backend.rag_assistant._generate", return_value=("Unsupported answer", ["S99"])):
            result = answer_question("Explain osteosarcoma diagnosis")
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["citations"], [])

    def test_report_only_answer_may_cite_only_an_explicit_report_passage(self):
        context = {"report_id": "0123456789abcdef0123456789abcdef", "filename": "synthetic.txt", "excerpts": [],
                   "excerpt_text": "[page 1] The report notes a lesion in the distal femur.", "has_matching_passages": True}
        with patch("backend.rag_assistant._runtime", return_value=(FakeCollection(), FakeEmbedder(), object())), \
             patch("backend.rag_assistant.MIN_SIMILARITY", 0.95), \
             patch("backend.rag_assistant._generate", return_value=("The selected report notes a distal femur lesion [RPT].", ["RPT"])):
            result = answer_question("What location is in the report?", case_id="BTXRD-IMG001868", report_context=context)
        self.assertEqual(result["status"], "answered")
        self.assertEqual([item["citation_id"] for item in result["citations"]], ["RPT"])
        self.assertEqual(result["citations"][0]["source_type"], "uploaded_report")

    def test_inline_citation_markers_must_match_validated_citation_ids(self):
        with patch("backend.rag_assistant._runtime", return_value=(FakeCollection(), FakeEmbedder(), object())), \
             patch("backend.rag_assistant.MIN_SIMILARITY", MIN_SIMILARITY), \
             patch("backend.rag_assistant._generate", return_value=("Claim [S99]", ["S1"])):
            result = answer_question("Explain osteosarcoma diagnosis")
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_pmc_ingestion_requires_exact_reusable_license_and_skips_figures(self):
        xml = b'''<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta>
          <article-title>Bone Imaging Review</article-title><contrib-group><contrib contrib-type="author"><name><given-names>Ada</given-names><surname>Author</surname></name></contrib></contrib-group>
          <pub-date><year>2025</year><month>02</month></pub-date>
          <permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/"><license-p>Creative Commons Attribution 4.0</license-p></license></permissions>
          </article-meta></front><body><sec><title>Imaging</title><p>Radiographs and MRI are used to evaluate a bone lesion and its relationship to surrounding structures.</p>
          <fig><caption><p>Third party caption text must not enter the retrieval corpus.</p></caption></fig></sec></body></article>'''
        source = {"pmcid": "PMC123", "title": "Fallback", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC123/", "institution": "Test"}
        with patch("backend.rag_ingest._fetch", return_value=xml):
            parsed = _pmc_text(source)
        text = " ".join(chunk for _, chunk in parsed["chunks"])
        self.assertEqual(parsed["title"], "Bone Imaging Review")
        self.assertEqual(parsed["publication_date"], "2025-02")
        self.assertEqual(parsed["license"], "CC BY 4.0")
        self.assertIn("Radiographs and MRI", text)
        self.assertNotIn("Third party caption", text)

        restricted = xml.replace(b"licenses/by/4.0", b"licenses/by-nc-nd/4.0").replace(b"Attribution 4.0", b"Attribution-NonCommercial-NoDerivatives 4.0")
        with patch("backend.rag_ingest._fetch", return_value=restricted), self.assertRaises(ValueError):
            _pmc_text(source)

    def test_nci_text_extraction_and_chunking_keep_source_sections(self):
        html = b'''<html><main><h1>Bone Cancer</h1><h2>Diagnosis</h2><p>Diagnostic imaging and specialist review are discussed here for patients with a suspected bone tumour.</p><h2>Navigation</h2><p>Secondary short text is omitted.</p></main></html>'''
        with patch("backend.rag_ingest._fetch", return_value=html):
            parsed = _nci_text({"url": "https://www.cancer.gov/test", "title": "fallback", "institution": "NCI"})
        self.assertEqual(parsed["title"], "Bone Cancer")
        self.assertEqual(parsed["chunks"][0][0], "Diagnosis")
        self.assertTrue(_split_text("Paragraph one. " * 150, max_chars=300, overlap=40))

    def test_api_reports_unconfigured_local_rag_without_fabricating_answer(self):
        client = TestClient(app)
        with patch("backend.rag_assistant.answer_question", side_effect=RAGUnavailable("RAG is not configured.")), \
             patch("backend.rag_assistant.assistant_status", return_value={"ready": False, "indexed_chunks": 0}):
            response = client.post("/api/assistant/chat", json={"question": "Explain osteosarcoma"})
            status = client.get("/api/assistant/status")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["ready"])

    def test_review_suite_covers_twenty_plus_question_types_without_answer_key(self):
        import json
        from pathlib import Path

        suite = json.loads((Path(__file__).parents[1] / "rag_eval_questions.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(suite["questions"]), 20)
        self.assertGreaterEqual(len({item["category"] for item in suite["questions"]}), 8)
        self.assertTrue(any(item.get("conversation") for item in suite["questions"]))
        self.assertTrue(any(item.get("expected_status") == "insufficient_evidence" for item in suite["questions"]))
        self.assertTrue(all("expected_answer" not in item for item in suite["questions"]))


if __name__ == "__main__":
    unittest.main()
