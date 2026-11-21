"""Run the 24-question RAG review set against the local API for human auditing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
API_URL = "http://127.0.0.1:8000"
QUESTIONS = Path(__file__).with_name("rag_eval_questions.json")
OUTPUT = Path(__file__).with_name("data") / "rag_eval_latest.json"


def run_evaluation() -> dict:
    cases = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    results = []
    for item in cases:
        payload = {"question": item["question"], "conversation": item.get("conversation", [])}
        if item.get("case_id"):
            payload["case_id"] = item["case_id"]
        response = requests.post(f"{API_URL}/api/assistant/chat", json=payload, timeout=240)
        response.raise_for_status()
        answer = response.json()
        excerpts = " ".join(source.get("excerpt", "") for source in answer.get("citations", [])).casefold()
        required = item.get("evidence_terms", [])
        results.append({
            "id": item["id"], "category": item["category"], "question": item["question"],
            "status": answer.get("status"), "answer": answer.get("answer"),
            "citation_records": answer.get("citations", []),
            "citation_urls_present": all(bool(source.get("url")) for source in answer.get("citations", [])),
            "expected_evidence_terms_found_in_cited_excerpts": [term for term in required if term.casefold() in excerpts],
            "expected_evidence_terms": required,
            "expected_status": item.get("expected_status"),
            "retrieval": answer.get("retrieval"),
            "review": {"retrieval_relevant": None, "answer_supported": None, "citations_correct": None, "insufficient_evidence_handled": None, "reviewer_notes": ""},
        })
        print(f"{item['id']} [{answer.get('status')}]: {item['question']}")
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "question_count": len(results),
              "evaluation_type": "retrieval and response review; human judgments remain unfilled",
              "results": results}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved review report:", OUTPUT)
    print("This runner does not score medical accuracy automatically. Complete the review fields against source passages.")
    return report


if __name__ == "__main__":
    run_evaluation()
