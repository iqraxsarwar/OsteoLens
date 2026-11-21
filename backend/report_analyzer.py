"""Local, source-grounded extraction for uploaded bone imaging reports.

No external language model is called. Summaries and answers quote source
sentences; terminology definitions are general references shown only for terms
present in the uploaded report.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
import re
import uuid
from typing import Any


MAX_REPORT_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_EXTRACTED_CHARACTERS = 300_000
MAX_LIVE_REPORTS = 20


class ReportProcessingError(ValueError):
    """Expected user-facing error for unsupported or unreadable documents."""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class SourcePage:
    page_number: int
    text: str
    method: str


_TERM_DEFINITIONS = {
    "osteosarcoma": "A malignant bone tumour in which the tumour cells produce bone-like tissue.",
    "chondrosarcoma": "A malignant tumour arising from cartilage-forming cells.",
    "osteochondroma": "A usually benign bone growth with a cartilage cap.",
    "giant cell tumor": "A bone tumour type that is generally non-cancerous but can behave locally aggressively.",
    "giant cell tumour": "A bone tumour type that is generally non-cancerous but can behave locally aggressively.",
    "simple bone cyst": "A fluid-filled cavity within bone; the report's wording determines its relevance in this case.",
    "osteofibroma": "A term for a bone lesion containing bone and fibrous tissue; interpretation depends on the report context.",
    "lytic lesion": "An area that appears less dense because bone has been removed or replaced.",
    "sclerotic lesion": "An area that appears denser or whiter than surrounding bone on an image.",
    "cortical destruction": "Damage or loss of the hard outer layer of a bone.",
    "periosteal reaction": "New bone formation along the outer bone surface in response to irritation or injury.",
    "soft tissue mass": "A lump or abnormal area in tissue around a bone.",
    "pathologic fracture": "A break through bone weakened by an underlying condition.",
    "biopsy": "A procedure that removes a small tissue sample for examination.",
    "metastasis": "Spread of disease from its original site to another part of the body.",
    "mri": "Magnetic resonance imaging, which uses magnetic fields and radio waves to create detailed images.",
    "ct": "Computed tomography, which combines X-ray measurements into cross-sectional images.",
    "radiograph": "An image made using X-rays.",
}

_ANATOMY_TERMS = (
    "distal femur", "proximal femur", "femur", "distal tibia", "proximal tibia",
    "tibia", "fibula", "humerus", "radius", "ulna", "pelvis", "acetabulum",
    "clavicle", "scapula", "rib", "spine", "vertebra", "calcaneus", "metacarpal",
    "metatarsal", "phalange", "knee", "hip", "shoulder", "wrist", "ankle",
)
_DIAGNOSIS_TERMS = (
    "osteosarcoma", "chondrosarcoma", "osteochondroma", "giant cell tumor",
    "giant cell tumour", "simple bone cyst", "osteofibroma",
    "synovial osteochondroma", "multiple osteochondromas", "other benign tumor",
    "other benign tumour", "other malignant tumor", "other malignant tumour",
    "bone tumor", "bone tumour", "neoplasm",
)
_FINDING_CUES = (
    "finding", "lesion", "mass", "tumor", "tumour", "fracture", "lytic", "sclerotic",
    "cortical", "periosteal", "mineralization", "mineralisation", "calcification",
    "marrow", "destruction", "erosion", "expansion", "soft tissue", "radiograph",
    "x-ray", "xray", "imaging", "lucency", "opacity",
)
_CHARACTERISTIC_CUES = (
    "well-defined", "well defined", "ill-defined", "ill defined", "expansile", "expansile",
    "aggressive", "non-aggressive", "cortical", "medullary", "sclerotic", "lytic",
    "mineralized", "mineralised", "size", "cm", "mm", "margin", "matrix", "heterogeneous",
)
_RECOMMENDATION_CUES = (
    "recommend", "recommendation", "follow-up", "follow up", "followup", "correlate",
    "consider", "biopsy", "surveillance", "further evaluation", "refer", "referral",
    "mri", "ct scan", "orthopedic oncology", "orthopaedic oncology",
)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could",
    "did", "do", "does", "for", "from", "give", "has", "have", "how", "i", "in", "is",
    "it", "me", "of", "on", "or", "please", "show", "tell", "that", "the", "this", "to",
    "was", "were", "what", "when", "where", "which", "who", "why", "with", "would",
    "describe", "described", "describes", "finding", "findings", "report", "reports", "state", "states", "mention", "mentions",
}


def _clean_page_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(char if char in "\n\t\f" or ord(char) >= 32 else " " for char in text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _decode_text_file(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            decoded = content.decode(encoding)
            if "\x00" in decoded:
                raise ReportProcessingError("The TXT file appears to contain binary data, not readable text.", 415)
            return decoded
        except UnicodeDecodeError:
            continue
    raise ReportProcessingError("The TXT file encoding is not supported. Save it as UTF-8 and try again.", 415)


def _extract_pdf_pages(content: bytes) -> tuple[list[SourcePage], str, str, list[str]]:
    try:
        import fitz
    except ImportError as exc:
        raise ReportProcessingError("PDF support is unavailable. Install the backend requirements, including PyMuPDF.", 503) from exc

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ReportProcessingError("This PDF is unreadable or damaged. Please export a valid PDF and try again.", 415) from exc
    if document.needs_pass:
        document.close()
        raise ReportProcessingError("This PDF is password-protected. Remove the password before uploading it.", 415)
    if len(document) == 0:
        document.close()
        raise ReportProcessingError("This PDF contains no pages.", 422)
    if len(document) > MAX_PDF_PAGES:
        page_count = len(document)
        document.close()
        raise ReportProcessingError(f"This PDF has {page_count} pages; the limit is {MAX_PDF_PAGES} pages.", 413)

    pages: list[SourcePage] = []
    warnings: list[str] = []
    ocr_attempted = False
    ocr_completed = False
    for index, page in enumerate(document):
        text = _clean_page_text(page.get_text("text", sort=True))
        method = "embedded_text"
        if not text:
            ocr_attempted = True
            try:
                ocr_text_page = page.get_textpage_ocr(language="eng", dpi=200, full=True)
                text = _clean_page_text(page.get_text("text", textpage=ocr_text_page, sort=True))
                method = "tesseract_ocr" if text else "ocr_no_text"
                ocr_completed = ocr_completed or bool(text)
            except Exception as exc:
                method = "ocr_unavailable"
                detail = str(exc).splitlines()[0][:180]
                warnings.append(
                    f"Page {index + 1} has no embedded text and OCR could not run. "
                    "Install the Tesseract OCR executable and make it available on PATH to read scanned pages. "
                    f"Technical detail: {detail}"
                )
        pages.append(SourcePage(index + 1, text, method))
    document.close()

    if not any(page.text for page in pages):
        if warnings:
            raise ReportProcessingError(warnings[0])
        raise ReportProcessingError("No readable text was found in the PDF. It may be blank or scanned; OCR could not recover text.")
    if any(not page.text for page in pages):
        warnings.append("Some PDF pages have no extracted text. Review the original file; the analysis may be incomplete.")
    methods = {page.method for page in pages}
    if "tesseract_ocr" in methods and "embedded_text" in methods:
        extraction_method = "embedded_text_and_ocr"
    elif "tesseract_ocr" in methods:
        extraction_method = "ocr"
    else:
        extraction_method = "embedded_text"
    if ocr_attempted and not ocr_completed:
        ocr_status = "unavailable_or_no_text"
    elif ocr_completed:
        ocr_status = "completed"
    elif ocr_attempted:
        ocr_status = "attempted_no_text"
    else:
        ocr_status = "not_needed"
    return pages, extraction_method, ocr_status, warnings


def _sentences(pages: list[SourcePage]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for page in pages:
        text = re.sub(r"\s+", " ", page.text).strip()
        for item in re.split(r"(?<=[.!?])\s+", text):
            sentence = item.strip(" \t\n•-")
            if len(sentence) >= 12:
                output.append({"text": sentence, "page_number": page.page_number})
    return output


def _find_terms(text: str, terms: tuple[str, ...] | list[str]) -> list[str]:
    matches: list[tuple[int, int, str]] = []
    for term in set(terms):
        pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
        matches.extend((match.start(), match.end(), match.group(0)) for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    selected: list[tuple[int, int, str]] = []
    for candidate in matches:
        if any(candidate[0] < existing[1] and existing[0] < candidate[1] for existing in selected):
            continue
        selected.append(candidate)
    return sorted({item[2] for item in selected}, key=str.casefold)


def _sentences_matching(sentences: list[dict[str, Any]], cues: tuple[str, ...]) -> list[dict[str, Any]]:
    return [sentence.copy() for sentence in sentences if any(cue in sentence["text"].casefold() for cue in cues)]


def analyze_extracted_pages(pages: list[SourcePage]) -> dict[str, Any]:
    text = "\n\n".join(page.text for page in pages if page.text).strip()
    if not text:
        raise ReportProcessingError("No readable report text was extracted. Analysis was not generated.")
    if len(text) > MAX_EXTRACTED_CHARACTERS:
        raise ReportProcessingError(f"The extracted report exceeds the {MAX_EXTRACTED_CHARACTERS:,}-character processing limit.", 413)

    sentences = _sentences(pages)
    anatomy = _find_terms(text, _ANATOMY_TERMS)
    diagnoses = _find_terms(text, _DIAGNOSIS_TERMS)
    characteristics = _sentences_matching(sentences, _CHARACTERISTIC_CUES)
    findings = _sentences_matching(sentences, _FINDING_CUES)
    recommendations = _sentences_matching(sentences, _RECOMMENDATION_CUES)

    terminology: list[dict[str, Any]] = []
    highlighted_terms = set(anatomy + diagnoses)
    for term, definition in _TERM_DEFINITIONS.items():
        if not re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE):
            continue
        source = next((sentence for sentence in sentences if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", sentence["text"], re.IGNORECASE)), None)
        if source:
            terminology.append({
                "term": term,
                "general_definition": definition,
                "definition_type": "general terminology, not a case-specific interpretation",
                "source_excerpt": source["text"],
                "page_number": source["page_number"],
            })
            highlighted_terms.add(term)

    summary_candidates: list[dict[str, Any]] = findings + recommendations
    for diagnosis in diagnoses:
        summary_candidates.extend(
            sentence for sentence in sentences
            if diagnosis.casefold() in sentence["text"].casefold()
        )
    if not summary_candidates:
        summary_candidates = sentences[:6]
    summary_statements: list[dict[str, Any]] = []
    seen_sentences: set[str] = set()
    for sentence in summary_candidates:
        key = sentence["text"].casefold()
        if key not in seen_sentences:
            seen_sentences.add(key)
            summary_statements.append(sentence.copy())
        if len(summary_statements) >= 8:
            break

    highlight_phrases: list[str] = []
    for value in list(highlighted_terms) + [cue for cue in _RECOMMENDATION_CUES if cue in text.casefold()]:
        actual = _find_terms(text, (value,))
        if actual and actual[0] not in highlight_phrases:
            highlight_phrases.append(actual[0])

    missing_information = []
    if not anatomy:
        missing_information.append("Anatomical location is not explicitly identifiable in the extracted text.")
    if not diagnoses:
        missing_information.append("No supported tumour type or diagnosis term was explicitly identified.")
    if not findings:
        missing_information.append("No imaging-finding sentence was identified by the report-text rules.")
    if not recommendations:
        missing_information.append("No recommendation or follow-up instruction was explicitly identified.")

    return {
        "extracted_findings": {
            "anatomical_location": anatomy,
            "imaging_findings": findings,
            "mentioned_diagnosis_terms": diagnoses,
            "reported_characteristics": characteristics,
            "recommendations_and_follow_up": recommendations,
            "missing_or_unclear": missing_information,
        },
        "terminology": terminology,
        "summary": {
            "method": "extractive; statements are copied from the uploaded report",
            "statements": summary_statements,
            "notice": "Source text only. This is not a diagnosis or a replacement for clinician interpretation.",
        },
        "highlight_phrases": highlight_phrases,
        "sentence_index": sentences,
    }


def process_report(filename: str, content: bytes, *, retain_session: bool = True) -> dict[str, Any]:
    safe_name = (filename or "").replace("\\", "/").split("/")[-1]
    suffix = safe_name.rsplit(".", 1)[-1].casefold() if "." in safe_name else ""
    if not safe_name or suffix not in {"pdf", "txt"}:
        raise ReportProcessingError("Upload a PDF or TXT file.", 415)
    if not content:
        raise ReportProcessingError("The uploaded document is empty.", 422)
    if len(content) > MAX_REPORT_BYTES:
        raise ReportProcessingError(f"The file exceeds the {MAX_REPORT_BYTES // (1024 * 1024)} MB upload limit.", 413)

    if suffix == "txt":
        text = _clean_page_text(_decode_text_file(content))
        pages = [SourcePage(1, text, "plain_text")]
        extraction_method = "plain_text"
        ocr_status = "not_applicable"
        warnings: list[str] = []
    else:
        if not content.startswith(b"%PDF-"):
            raise ReportProcessingError("The file extension is PDF, but its contents are not a valid PDF.", 415)
        pages, extraction_method, ocr_status, warnings = _extract_pdf_pages(content)

    result = analyze_extracted_pages(pages)
    report_id = uuid.uuid4().hex
    page_results = [{"page_number": page.page_number, "text": page.text, "method": page.method} for page in pages]
    full_text = "\n\n".join(page["text"] for page in page_results if page["text"]).strip()
    response = {
        "report_id": report_id,
        "document": {
            "filename": safe_name,
            "format": suffix.upper(),
            "byte_size": len(content),
            "page_count": len(pages),
            "extraction_method": extraction_method,
            "ocr_status": ocr_status,
            "page_methods": [{"page_number": page.page_number, "method": page.method} for page in pages],
            "warnings": warnings,
        },
        "original_text": full_text,
        "pages": page_results,
        **{key: value for key, value in result.items() if key != "sentence_index"},
    }
    if retain_session:
        _REPORT_SESSIONS[report_id] = {"pages": pages, "sentences": result["sentence_index"], "analysis": result}
        while len(_REPORT_SESSIONS) > MAX_LIVE_REPORTS:
            _REPORT_SESSIONS.popitem(last=False)
    return response


_REPORT_SESSIONS: OrderedDict[str, dict[str, Any]] = OrderedDict()


def restore_report_session(report_result: dict[str, Any]) -> None:
    """Rebuild a report Q&A session from locally persisted extracted content."""
    report_id = str(report_result.get("report_id") or "")
    pages = [
        SourcePage(int(item["page_number"]), str(item.get("text") or ""), str(item.get("method") or "stored"))
        for item in report_result.get("pages", [])
        if isinstance(item, dict) and "page_number" in item
    ]
    if not report_id or not pages:
        raise ReportProcessingError("Stored report text is unavailable for questions.", 422)
    analysis = analyze_extracted_pages(pages)
    _REPORT_SESSIONS[report_id] = {"pages": pages, "sentences": analysis["sentence_index"], "analysis": analysis}


def clear_report_session(report_id: str) -> None:
    _REPORT_SESSIONS.pop(report_id, None)


def select_report_context(report_result: dict[str, Any], question: str, limit: int = 8) -> dict[str, Any]:
    """Return source sentences from an explicitly selected uploaded report.

    This is a report-only lexical passage selector, separate from the medical
    literature vector retrieval used by the RAG assistant.
    """
    pages = [
        SourcePage(int(item["page_number"]), str(item.get("text") or ""), str(item.get("method") or "stored"))
        for item in report_result.get("pages", [])
        if isinstance(item, dict) and "page_number" in item
    ]
    query_tokens = {
        token for token in re.findall(r"[a-z0-9]+", (question or "").casefold())
        if token not in _STOP_WORDS and len(token) > 1
    }
    ranked: list[tuple[int, dict[str, Any]]] = []
    for sentence in _sentences(pages):
        sentence_tokens = set(re.findall(r"[a-z0-9]+", sentence["text"].casefold()))
        overlap = len(query_tokens & sentence_tokens)
        if overlap:
            ranked.append((overlap, sentence))
    ranked.sort(key=lambda item: (-item[0], len(item[1]["text"])))
    excerpts = [item.copy() for _, item in ranked[:limit]]
    document = report_result.get("document") or {}
    return {
        "report_id": report_result.get("report_id"),
        "filename": document.get("filename", "uploaded report"),
        "excerpts": excerpts,
        "excerpt_text": "\n".join(f"[page {item['page_number']}] {item['text']}" for item in excerpts),
        "has_matching_passages": bool(excerpts),
    }


def answer_report_question(report_id: str, question: str) -> dict[str, Any]:
    session = _REPORT_SESSIONS.get(report_id)
    if session is None:
        raise ReportProcessingError("This report session has expired. Upload the report again to ask questions.", 404)
    query = (question or "").strip()
    if not query:
        raise ReportProcessingError("Enter a question about the uploaded report.", 422)
    if len(query) > 500:
        raise ReportProcessingError("Questions must be 500 characters or fewer.", 413)

    query_tokens = {
        token for token in re.findall(r"[a-z0-9]+", query.casefold())
        if token not in _STOP_WORDS and len(token) > 1
    }
    q = query.casefold()
    if "diagnos" in q or "tumor" in q or "tumour" in q:
        query_tokens.update(re.findall(r"[a-z0-9]+", " ".join(session["analysis"]["extracted_findings"]["mentioned_diagnosis_terms"]).casefold()))
    if any(term in q for term in ("follow", "recommend", "next step", "what next")):
        query_tokens.update({"recommend", "follow", "consider", "biopsy", "surveillance", "correlate"})

    ranked: list[tuple[int, dict[str, Any]]] = []
    for sentence in session["sentences"]:
        sentence_tokens = set(re.findall(r"[a-z0-9]+", sentence["text"].casefold()))
        overlap = query_tokens & sentence_tokens
        if overlap:
            ranked.append((len(overlap), sentence))
    ranked.sort(key=lambda item: (-item[0], len(item[1]["text"])))
    excerpts = []
    seen: set[str] = set()
    for _score, sentence in ranked:
        key = sentence["text"].casefold()
        if key not in seen:
            seen.add(key)
            excerpts.append(sentence.copy())
        if len(excerpts) == 3:
            break

    term_definition = None
    for term, definition in _TERM_DEFINITIONS.items():
        if term in q and any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", page.text, re.IGNORECASE) for page in session["pages"]):
            term_definition = {"term": term, "general_definition": definition, "definition_type": "general terminology"}
            break

    if not excerpts:
        answer = "The uploaded report does not contain enough matching text to answer this question."
        answer_status = "not_found_in_source"
    else:
        answer = "The uploaded report states: " + " ".join(f'“{item["text"]}”' for item in excerpts)
        answer_status = "source_excerpt"
        if term_definition:
            answer += f" General terminology: {term_definition['general_definition']} This definition is not a case-specific interpretation."
    return {
        "report_id": report_id,
        "question": query,
        "answer": answer,
        "answer_status": answer_status,
        "source_excerpts": excerpts,
        "general_terminology": term_definition,
        "method": "extractive sentence retrieval from this report; no external model or medical record lookup",
        "notice": "This explanation is informational and is not a medical diagnosis.",
    }
