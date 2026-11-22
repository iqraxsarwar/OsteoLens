"""Local API for verified case inference and Grad-CAM generation."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Literal
from threading import Lock

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.public_access import PublicAccessMiddleware, PUBLIC_MODE, PUBLIC_ORIGIN
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ConfigDict
from backend.privacy import PrivacyGuardMiddleware, privacy_status, QUESTIONS, operator_config, release_issues

if PUBLIC_MODE and release_issues(operator_config()):
    raise RuntimeError('Public deployment is blocked until the controller, contact, technical-data basis and provider review are completed. See PRIVACY_REVIEW.md.')

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_MANIFEST_PATH = PROJECT_ROOT / "src" / "data" / "cases.json"
PUBLIC_IMAGE_DIR = (PROJECT_ROOT / "public" / "images" / "btxrd").resolve()
DEFAULT_CHECKPOINT = PROJECT_ROOT / "models" / "checkpoints" / "osteolens_btxrd_resnet18.pth"
CHECKPOINT_PATH = Path(os.environ.get("OSTEOLENS_MODEL_PATH", DEFAULT_CHECKPOINT)).resolve()
API_VERSION = "osteolens-inference-0.1.0"

# Windows registry MIME mappings can otherwise serve the PDF worker as text/plain.
mimetypes.add_type('text/javascript', '.mjs')

app = FastAPI(title="OsteoLens Research Inference API", version=API_VERSION,
              docs_url=None if PUBLIC_MODE else "/docs", redoc_url=None if PUBLIC_MODE else "/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[PUBLIC_ORIGIN] if PUBLIC_MODE else ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(PublicAccessMiddleware)
app.add_middleware(PrivacyGuardMiddleware)
_inference_lock = Lock()


@app.exception_handler(RequestValidationError)
async def private_validation_error(_request, _exception):
    return JSONResponse({'detail':'Invalid research selection.'}, status_code=422)


@app.get('/api/privacy')
def get_privacy_status():
    return privacy_status()


class ResearchSelection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question_id: Literal['compare_tumours','imaging','transition','benign_malignant','case_summary','heatmap','source_label','limitations'] | None = None
    question: str | None = Field(default=None, min_length=1, max_length=1200)
    source_id: str | None = Field(default=None, max_length=40)
    language: Literal['en','tr'] = 'en'
    case_id: str | None = Field(default=None, pattern=r'^BTXRD-IMG[0-9]{6}$')


@app.post('/api/assistant/research')
def selected_research_question(selection: ResearchSelection):
    from backend.rag_assistant import answer_question, RAGUnavailable
    from backend.report_analyzer import select_report_context
    if bool(selection.question_id) == bool(selection.question and selection.question.strip()):
        raise HTTPException(422, 'Provide a question or a suggested question identifier.')
    if selection.source_id and selection.case_id:
        raise HTTPException(422, 'Choose one report or image context.')
    if selection.case_id and selection.case_id not in _get_cases():
        raise HTTPException(422, 'Select an available source case.')
    if selection.question_id in {'case_summary','source_label','limitations'} and not selection.case_id:
        raise HTTPException(422, 'Select a source case first.')
    question = selection.question.strip() if selection.question else QUESTIONS[selection.question_id]
    report_context = None
    if selection.source_id:
        report = analyze_published_example(selection.source_id)
        search_question = question
        if selection.language == 'tr':
            from backend.language import english_search_query
            try: search_question = english_search_query(question)
            except RAGUnavailable as exc:
                raise HTTPException(503, 'Research service unavailable. Please try again later.') from exc
        report_context = select_report_context(report, search_question)
        # Broad report requests should use actual source sentences, not retrieve
        # generic literature just because the report lacks the word "summary".
        import re
        if re.search(r'\b(summary|summarize|summarise|findings|overview)\b', search_question, re.I):
            excerpts = report['summary']['statements'][:5]
            report_context.update(excerpts=excerpts,
                excerpt_text='\n'.join(f"[page {item['page_number']}] {item['text']}" for item in excerpts),
                has_matching_passages=bool(excerpts))
        report_context['published_source'] = report['source']
    try:
        return answer_question(question, case_id=selection.case_id, report_context=report_context,
            model_result=_analysis_context_by_case.get(selection.case_id or ''), language=selection.language)
    except RAGUnavailable as exc:
        raise HTTPException(503, 'Research service unavailable. Please try again later.') from exc
    except ValueError as exc:
        raise HTTPException(422, 'Question context is invalid. Check the selected source or case.') from exc


@app.post('/api/reports/examples/{source_id}')
def analyze_published_example(source_id: str):
    from backend.report_analyzer import process_report, clear_report_session
    sources = json.loads((PROJECT_ROOT/'src/data/openAccessReports.json').read_text(encoding='utf-8'))
    source = next((item for item in sources if item['id'] == source_id), None)
    if not source: raise HTTPException(404, 'Published example not found.')
    directory = (PROJECT_ROOT/'public/case_reports').resolve()
    path = (directory / (source_id+'.txt')).resolve()
    if path.parent != directory: raise HTTPException(404, 'Published example not found.')
    result = process_report(source_id+'.txt', path.read_bytes(), retain_session=False)
    clear_report_session(result['report_id'])
    result.pop('report_id', None)
    return {**result, 'source':source, 'persistence':{'saved':False}, 'mode':'published_examples_only'}


@app.post('/api/privacy/erase-session')
def erase_previous_session():
    from backend.public_access import report_owner
    from backend.report_store import list_reports, delete_report
    from backend.report_analyzer import clear_report_session
    count = 0
    if PUBLIC_MODE and report_owner.get() != 'local':
        for item in list_reports():
            delete_report(item['report_id'])
            clear_report_session(item['report_id'])
            count += 1
    response = JSONResponse({'deleted_reports':count,'scope':'this browser session only'})
    response.delete_cookie('osteolens_session',path='/api',secure=True,httponly=True,samesite='lax')
    return response


class ReportQuestion(BaseModel):
    language: Literal['en', 'tr'] = 'en'
    report_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=500)


class AssistantQuestion(BaseModel):
    language: Literal['en', 'tr'] = 'en'
    question: str = Field(min_length=1, max_length=1200)
    case_id: str | None = Field(default=None, max_length=80)
    report_id: str | None = Field(default=None, max_length=64)
    conversation: list[dict[str, str]] = Field(default_factory=list, max_length=6)


class ReportAssociation(BaseModel):
    case_id: str | None = Field(default=None, max_length=80)

_model_bundle: Any | None = None
_case_index: dict[str, dict[str, Any]] | None = None
_analysis_context_by_case: dict[str, dict[str, Any]] = {}


def _get_model() -> Any:
    global _model_bundle
    if _model_bundle is None:
        if not CHECKPOINT_PATH.is_file():
            raise HTTPException(
                status_code=503,
                detail=f"Trained model checkpoint is unavailable: {CHECKPOINT_PATH}",
            )
        try:
            from training.src.inference import load_model

            _model_bundle = load_model(CHECKPOINT_PATH)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"The model checkpoint could not be loaded: {exc}",
            ) from exc
    return _model_bundle


def _get_cases() -> dict[str, dict[str, Any]]:
    global _case_index
    if _case_index is None:
        try:
            document = json.loads(CASE_MANIFEST_PATH.read_text(encoding="utf-8"))
            records = document["cases"]
            _case_index = {record["case_id"]: record for record in records}
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=500, detail=f"Case manifest is invalid: {exc}") from exc
    return _case_index


def _verified_case_image(case_id: str) -> tuple[dict[str, Any], bytes]:
    record = _get_cases().get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown case ID: {case_id}")
    image_path = (PUBLIC_IMAGE_DIR / str(record.get("image_id", ""))).resolve()
    if image_path.parent != PUBLIC_IMAGE_DIR or not image_path.is_file():
        raise HTTPException(status_code=404, detail=f"Source image is missing for {case_id}.")
    image_bytes = image_path.read_bytes()
    actual_sha256 = hashlib.sha256(image_bytes).hexdigest()
    if actual_sha256.lower() != str(record.get("sha256", "")).lower():
        raise HTTPException(
            status_code=409,
            detail=f"Source image checksum does not match the case manifest for {case_id}.",
        )
    return record, image_bytes


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": (
            "model_loaded" if _model_bundle is not None
            else "checkpoint_present" if CHECKPOINT_PATH.is_file()
            else "checkpoint_missing"
        ),
        "api_version": API_VERSION,
        **({"checkpoint_path": str(CHECKPOINT_PATH)} if not PUBLIC_MODE else {}),
        "checkpoint_present": CHECKPOINT_PATH.is_file(),
        "model_loaded": _model_bundle is not None,
        "case_count": len(_get_cases()),
        "localization": "unavailable; annotation files and localization weights are not present in this workspace",
    }


@app.post("/api/analyze/{case_id}")
def analyze_case(case_id: str) -> dict[str, Any]:
    record, image_bytes = _verified_case_image(case_id)
    try:
        from training.src.inference import generate_gradcam_image_bytes

        # Grad-CAM registers hooks and performs backward passes on a shared model.
        with _inference_lock:
            result = generate_gradcam_image_bytes(image_bytes, _get_model())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Image analysis failed for {case_id}: {exc}") from exc
    response = {
        "status": "complete",
        "case_id": case_id,
        "image_id": record["image_id"],
        "source_sha256": record["sha256"],
        **result,
    }
    _analysis_context_by_case[case_id] = {
        "case_id": case_id,
        "image_id": record["image_id"],
        "prediction": result.get("prediction"),
        "confidence": result.get("confidence"),
        "probabilities": result.get("probabilities"),
        "model_version": result.get("model_version"),
        "analysis_status": "complete",
        "probabilities_calibrated": result.get("probabilities_calibrated", False),
        "gradcam_available": bool(result.get("gradcam_heatmap_data_url") or result.get("gradcam_overlay_data_url")),
    }
    return response


@app.post("/api/reports/analyze")
async def analyze_uploaded_report(file: UploadFile = File(...), case_id: str | None = Form(default=None)) -> dict[str, Any]:
    from backend.report_analyzer import ReportProcessingError, process_report
    from backend.report_store import ReportStoreError, save_report, validate_case_id

    try:
        from backend.report_analyzer import MAX_REPORT_BYTES

        content = await file.read(MAX_REPORT_BYTES + 1)
        if len(content) > MAX_REPORT_BYTES:
            raise ReportProcessingError(f"The file exceeds the {MAX_REPORT_BYTES // (1024 * 1024)} MB upload limit.", 413)
        try:
            validated_case_id = validate_case_id(case_id)
        except ReportStoreError as exc:
            raise ReportProcessingError(str(exc), 422) from exc
        result = process_report(file.filename or "", content)
        try:
            stored = save_report(result, content, validated_case_id)
        except ReportStoreError as exc:
            from backend.report_analyzer import clear_report_session

            clear_report_session(result["report_id"])
            raise ReportProcessingError(str(exc), 422) from exc
        result["persistence"] = {"stored_locally": True, **stored}
        return result
    except ReportProcessingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    finally:
        await file.close()


@app.get("/api/reports")
def list_uploaded_reports(case_id: str | None = None) -> dict[str, Any]:
    from backend.report_store import ReportStoreError, list_reports

    try:
        return {"reports": list_reports(case_id)}
    except ReportStoreError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/reports/item/{report_id}")
def get_uploaded_report(report_id: str) -> dict[str, Any]:
    from backend.report_store import ReportStoreError, get_report

    try:
        record, analysis = get_report(report_id)
        return {**analysis, "persistence": {"stored_locally": True, **record}}
    except ReportStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/reports/{report_id}/association")
def update_report_association(report_id: str, association: ReportAssociation) -> dict[str, Any]:
    from backend.report_store import ReportStoreError, update_case_association

    try:
        return update_case_association(report_id, association.case_id)
    except ReportStoreError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.delete("/api/reports/{report_id}")
def delete_uploaded_report(report_id: str) -> dict[str, Any]:
    from backend.report_analyzer import clear_report_session
    from backend.report_store import ReportStoreError, delete_report

    try:
        result = delete_report(report_id)
        clear_report_session(report_id)
        return result
    except ReportStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/assistant/status")
def rag_assistant_status() -> dict[str, Any]:
    from backend.rag_assistant import assistant_status

    return assistant_status()


@app.post("/api/assistant/chat")
def ask_rag_assistant(request: AssistantQuestion) -> dict[str, Any]:
    from backend.rag_assistant import RAGUnavailable, answer_question
    from backend.report_analyzer import select_report_context
    from backend.report_store import ReportStoreError, get_report

    try:
        report_context = None
        if request.report_id:
            if not request.case_id:
                raise HTTPException(status_code=422, detail="Select the associated case before including its report context.")
            try:
                report_record, report_analysis = get_report(request.report_id)
            except ReportStoreError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            if report_record.get("case_id") != request.case_id:
                raise HTTPException(status_code=422, detail="The selected report is not associated with this Case ID.")
            report_context = select_report_context(report_analysis, request.question)
        return answer_question(
            request.question,
            case_id=request.case_id,
            model_result=_analysis_context_by_case.get(request.case_id or ""),
            report_context=report_context,
            conversation=request.conversation,
            language=request.language,
        )
    except RAGUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/reports/ask")
def ask_about_uploaded_report(request: ReportQuestion) -> dict[str, Any]:
    from backend.report_analyzer import ReportProcessingError, answer_report_question, restore_report_session
    from backend.report_store import ReportStoreError, get_report

    try:
        try:
            get_report(request.report_id)
        except ReportStoreError as exc:
            raise ReportProcessingError(str(exc), 404) from exc
        if request.language == 'tr':
            from backend.language import english_search_query
            from backend.rag_assistant import RAGUnavailable
            try:
                request.question = english_search_query(request.question)
            except RAGUnavailable as exc:
                raise ReportProcessingError('Türkçe soru çeviri hizmeti şu anda kullanılamıyor.', 503) from exc
        try:
            return answer_report_question(request.report_id, request.question)
        except ReportProcessingError as exc:
            if exc.status_code != 404:
                raise
            _record, analysis = get_report(request.report_id)
            restore_report_session(analysis)
        return answer_report_question(request.report_id, request.question)
    except ReportProcessingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


if (PROJECT_ROOT / 'dist').is_dir():
    app.mount('/', StaticFiles(directory=PROJECT_ROOT / 'dist', html=True), name='website')
