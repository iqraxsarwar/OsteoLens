# OsteoLens local research API

The React viewer calls this local FastAPI service to load the saved ResNet-18 checkpoint, verify the selected sample image against `src/data/cases.json`, and produce model scores plus a Grad-CAM heatmap and overlay. The API does not create detection boxes or segmentation masks. Those require a separately trained and evaluated localization model.

## Requirements

- Python with a PyTorch/torchvision pair compatible with each other and the checkpoint. The checkpoint uses ResNet-18, has classes ordered `Normal`, `Benign`, `Malignant`, and expects 256×256 aspect-preserving padding with ImageNet normalization. These values are checked by `training/src/inference.py` when loading the model.
- The checkpoint at `models/checkpoints/osteolens_btxrd_resnet18.pth`, or set `OSTEOLENS_MODEL_PATH` to its location. Checkpoints are ignored by Git and are not included automatically in a clone.
- Install the listed runtime dependencies from the repository root: `python -m pip install -r backend/requirements.txt`. This includes PyTorch and torchvision; choose a build compatible with your Python and CUDA runtime. PyTorch needs substantial disk space; this workspace's current Python does not have it installed.

## Start the services

From the repository root, use two terminals:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
npm run dev
```

The UI calls `POST http://127.0.0.1:8000/api/analyze/{case_id}`. The API reads the corresponding source image from the case manifest and verifies its SHA-256 before inference. `GET http://127.0.0.1:8000/api/health` reports whether the checkpoint file is present.

Select a case and press **Analyze case**. The prediction and uncalibrated class scores are shown separately from the source dataset label. The viewer allows switching between the original X-ray, model-generated Grad-CAM heatmap, and image overlay. The original source image remains available. Grad-CAM is qualitative model attribution; it does not prove tumour presence or define a tumour boundary. Localization remains unavailable until annotation correspondence is inspected and a distinct model is trained and evaluated.

If the server reports a missing dependency, missing checkpoint, incompatible checkpoint, missing image, or checksum mismatch, the API returns an error and the UI displays it. It never substitutes a canned prediction or visualization.

## Validation

Run the frontend tests and build with `npm test` and `npm run build`. The optional model tests in `backend/tests/test_gradcam.py` load the real checkpoint and inspect five distinct manifest images, including all three classes, when PyTorch and torchvision are installed. Those model tests are skipped if the runtime dependencies are absent; a skipped test is not evidence of a successful model run.

The full BTXRD annotation archive is not in this workspace. The dataset paper describes tumour masks and bounding boxes, but this API reports localization as unavailable until the actual LabelMe files and image joins have been checked and a localization model is independently trained and evaluated.

## Phase 5 report analyser

The React **Report analyser** accepts PDF and TXT documents (maximum 20 MB). It posts to `POST /api/reports/analyze`, extracts PDF text with PyMuPDF, and returns the original text, page extraction methods, source-sentence findings, extractive summary, and general terminology definitions only for terms present in the report. Successful uploads and extracted text are stored locally in `backend/data/reports/` with a SQLite metadata index. Association is optional and must be explicitly selected from a manifest Case ID; `GET /api/reports?case_id=...` lists case-linked files. `PATCH /api/reports/{report_id}/association` associates or unlinks a report; `DELETE /api/reports/{report_id}` removes its local file and extracted text. `GET /api/reports/item/{report_id}` reopens saved analysis. The `POST /api/reports/ask` endpoint retrieves matching source sentences and restores its Q&A session from the saved extraction after a backend restart. It does not call an external language model and says when the document has no matching passage.

The local report directory is ignored by Git, but it is **not encrypted or access-controlled**. Upload synthetic/de-identified material only; filenames and document text can contain identifying information. Delete a report through its **Delete saved report** control or the DELETE endpoint. Report context is sent to the RAG model only when a user explicitly selects an associated report and checks the include option for that question; it is never included automatically.

Install the dependencies with `python -m pip install -r backend/requirements.txt`. Scanned-page OCR is optional: PyMuPDF calls Tesseract when the `tesseract` executable and English language data are installed and available on `PATH`. Without Tesseract, scanned pages produce an explicit warning or processing error; the analyser does not fabricate text. Extracted fields use transparent lexical rules and may miss unusual wording. They are research aids, not diagnoses.

Run report tests with `python -m unittest discover -s backend/tests -v`. The PDF extraction test runs only when PyMuPDF is installed; OCR also needs a separately installed Tesseract executable. A skipped local PDF test is not evidence of PDF extraction succeeding in that environment.

## Phase 6 RAG research assistant

The RAG assistant is a separate API/UI feature from Report Analyser. It has two independent local components: Sentence Transformers (`sentence-transformers/all-MiniLM-L6-v2`, Apache-2.0) creates CPU embeddings and Chroma persists vectors in `backend/data/rag/chroma`; Ollama provides local answer generation. It makes no paid API calls and sends no question, case metadata, or image to a remote LLM. The Ollama model and embedding weights must be downloaded locally before the feature reports ready.

### One-time setup

From the repository root:

```powershell
python -m pip install -r backend/rag-requirements.txt
```

Install Ollama using its official installer, then pull the default local text model:

```powershell
ollama pull qwen2.5:0.5b
```

Ollama must be running on `http://127.0.0.1:11434`. The 3B model download is about 2 GB and needs enough RAM to run; check the model's license and your hardware before using it. To select another locally installed Ollama model, set `OSTEOLENS_OLLAMA_MODEL`. Set `OSTEOLENS_OLLAMA_URL` if the local service uses another address.

Build or refresh the local corpus and vector index:

```powershell
python -m backend.rag_ingest --rebuild
```

Ingestion fetches source text, extracts headings/paragraphs, chunks the text, runs the local embedding model, and upserts chunks and provenance into the persistent Chroma collection. It records the fetched source inventory in the ignored `backend/data/rag/` folder. It can take time on CPU and requires internet for the first source/model downloads. The server's `GET /api/assistant/status` reports dependency, index, and local model state. It does not answer until all components are ready.

### Sources and rights

The curated manifest is [rag_sources.json](rag_sources.json). It includes NCI bone cancer/osteosarcoma/Ewing/chondrosarcoma pages and peer-reviewed PMC full texts covering osteosarcoma imaging, giant cell tumour, aneurysmal bone cyst, multimodal imaging, and metadata-aware bone tumour AI. NCI says its text may generally be reused with NCI credit and original-title links; graphics and trademarks have separate restrictions, and this pipeline does not ingest graphics. PMC XML is ingested only when its article license is verified as CC BY 4.0 at ingestion time. Other article licenses, including CC BY-NC-ND, are excluded. Article titles/authors/dates are parsed from each source; unavailable dates are labelled unavailable. See the live [NCI reuse policy](https://www.cancer.gov/policies/copyright-reuse) and [PMC OA BioC service](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/).

### Retrieval, generation, and case context

`POST /api/assistant/chat` embeds the question and retrieves candidate chunks from the Chroma cosine index. A lexical rank-fusion pass supplements, rather than replaces, semantic retrieval. A similarity gate returns an insufficient-evidence response without generation if retrieved evidence is weak. For adequate retrieval, the local Ollama model receives only the retrieved excerpts, recent conversation, and (if selected) structured case fields. The server rejects citations that are not IDs from the retrieved set. The UI renders clickable source title, author/institution, date, license, and retrieved excerpt.

Case context is resolved server-side from `src/data/cases.json`, and includes case/image identifiers, image reference, source label/subtype, anatomy, projection, and available age/sex/center metadata. A model output and Grad-CAM availability are included only after the backend itself has analyzed the same case and image. The original image pixels and heatmap are never passed to the language model. BTXRD has no free-text case report in the current manifest, so `associated_report` remains unavailable. Grad-CAM is described as model attribution, not a tumour boundary. The current app does not have an image-understanding language model.

Conversation turns are held in the browser and sent to the local backend for follow-up context; the server does not persist RAG conversations. Clear conversation removes the browser history. Report Analyser remains a separate feature. Its uploaded report text enters RAG context only for the explicitly selected linked report and question, and report passages are labelled separately from medical literature citations.

### Evaluation and limits

Run backend tests with `python -m unittest discover -s backend/tests -v`. The 24-query review set is in `rag_eval_questions.json`; after installing the local stack and building the index, run `python -m backend.rag_eval`. The report checks that citations resolve to source records and whether requested terms occur in cited excerpts, but it deliberately leaves relevance, answer support, and citation correctness for human review. No live RAG model/index evaluation was possible in the current workspace because Chroma, Sentence Transformers, Ollama, and an ingested index are not present. Do not treat the implementation tests as evidence of medical answer accuracy or mark Phase 6 complete until the 24 questions have been run and reviewed against their linked passages.
