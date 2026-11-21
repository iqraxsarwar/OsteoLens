# OsteoLens — project roadmap

**Tagline:** Bone imaging, understood.  
**Purpose:** Final-year academic research prototype for bone radiograph exploration. It is not a diagnostic product.

## 1. Current build and realistic scope

The first frontend exists in this repository. It has six synthetic linked teaching cases, case search and filters, a dark image-viewing mock, illustrative ROI and score, linked case text, and a case-grounded assistant interaction. The sample radiograph is generated interface artwork. The cases, descriptions, scores, overlays, and assistant replies are synthetic UI data; no BTXRD data, trained model, report parser, external knowledge corpus, or LLM is connected.

The complete vision is too large for one student to implement and validate in a single semester. The defensible MVP is a reproducible BTXRD binary classifier (normal vs tumour), documented evaluation, linked case library, FastAPI inference service, and a React case viewer that clearly reports limitations. A three-class normal/benign/malignant experiment is a stretch goal, not a promised result. Add localisation only if annotation handling and time permit. Use the provided masks/boxes for measured localisation when feasible; never present Grad-CAM as a tumour contour. RAG/report analysis are secondary and should follow the imaging path.

**Research evidence and implication.** BTXRD contains 3,746 radiographs (1,879 normal and 1,867 tumour) and includes image labels, bounding boxes, and masks; inspect its actual CSV and annotation files before deciding target labels. The dataset paper describes data from multiple centers and a histology/two-expert confirmed subset, but the dataset must not be casually treated as a patient-level independent cohort. Build a grouping audit before splitting. [BTXRD data paper](https://www.nature.com/articles/s41597-024-04311-y). A 2025 systematic review included 325 studies and found average reporting alignment of 28.9/53 CLAIM items and 5.1/30 FUTURE-AI items, placing the area largely at proof-of-concept stage. That supports a small, transparent, reproducible project over a large feature list. [Systematic review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11976239/). A multicenter knee-radiograph study demonstrates that localization and detection are technically possible, but its performance is not transferable to this smaller dataset or student model. [Knee tumor detection study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11320541/).

### Scope tiers

| Tier | Deliverable |
|---|---|
| MVP (commit to this) | Case library with stable same-case IDs; image viewer; BTXRD acquisition/manifest tooling; binary classifier baseline; case-grouped evaluation; FastAPI endpoint; frontend inference result with model/version and limitations; unit/API/integration checks; research report. |
| Strong final-year project | Compare transfer-learning backbones; class-imbalance experiment; calibrated uncertainty/review-needed state; detection or mask evaluation using BTXRD annotations; Grad-CAM shown only as a qualitative attention explanation; clinical advisor review; Dockerized demo. |
| Optional | Three-way subtype prediction; OCR/PDF report extraction; citation-backed RAG over a small vetted corpus; PDF case summary; deployable hosted demo. Attempt only after model and case linkage work. |

## 2. Research and dataset investigation

### Research review (Weeks 1–2; student, advisor consulted)

1. Read the BTXRD dataset paper, the systematic review, and at least two task-specific bone X-ray model studies. Extract population, modality, label source, split unit, architecture, external test, metrics, and explainability method into a comparison sheet.
2. Add studies on metadata, XAI, and vision-language models only to frame future work. Do not infer that a vision-language model is a validated bone tumour classifier.
3. Use published performance as context, not a target copied across datasets. Report your own task and cohort precisely.
4. Deliver: literature matrix; one-page gap statement; preregistered/dated experiment plan; risk and intended-use statement.

Published work includes a multicenter knee X-ray detector with localization and external testing, but it is a different cohort and task. A 2024 study explores metadata plus imaging and is useful when discussing leakage and clinical covariates. [Metadata/multimodal bone-tumour study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11490032/).

### BTXRD acquisition and inspection (Weeks 2–3; student)

1. Obtain only from the dataset's [Figshare DOI](https://doi.org/10.6084/m9.figshare.27865398); archive the download URL, retrieval date, checksum, version, and licence text. Keep images out of Git. Confirm the current record's rights and attribution terms directly before sharing images, derived files, or weights; do not infer reuse rights just from “publicly available.”
2. Inventory `dataset.csv`, images, and JSON annotations. Check counts, missing files, duplicate hashes/perceptual duplicates, dimensions, image decode failures, annotation-image joins, label counts, anatomy and view distribution, and possible patient/case identifiers.
3. Determine whether multiple images/views belong to the same patient or lesion. Split by patient/case group where supported. If linkage is unavailable, document the limitation and construct the strongest defensible proxy grouping (e.g. exact duplicates and metadata-linked views); never claim an independent patient split without evidence.
4. Inspect class definitions before use. The paper's aggregate normal/tumour totals do not automatically support benign-vs-malignant labels for every record. Verify subtype coverage and missing/ambiguous labels.
5. Produce `dataset_card.md`, `manifest.csv` containing relative path, source image ID, target, group ID, anatomy, projection, annotation availability, and exclusions; quality-control summary; license/attribution note; and a script that validates the manifest.

### MedPix feasibility (Weeks 2–4; student)

Treat MedPix as a possible separate teaching-case source, not as an extension of BTXRD labels. Run a small feasibility sample: query candidate bone tumour terms; record case ID, image modality/projection, associated case text, date/source link, and visible reuse/credit terms; verify the image and narrative are part of the same case. MedPix is known as an NLM teaching-image/case resource, but do not assume it has enough bone radiographs with compatible text or unrestricted rights. Check the rights/credit statement attached to each item and NLM terms with the institution before redistribution. Preserve source URLs and identifiers; hotlinking is not a substitute for permission. If permissions or dependable stable linkage are uncertain, use BTXRD images with its own metadata and create synthetic UI examples only for the demo; do not attach unrelated MedPix text. Deliver: feasibility spreadsheet, inclusion/exclusion rules, written decision.

## 3. AI model development

### Environment and sequence

- Python 3.11/3.12 virtual environment; PyTorch, torchvision, pandas, Pillow/OpenCV, scikit-learn, matplotlib/seaborn, and optionally Albumentations. Pin dependencies in `requirements.txt`/lock file; record Python, CUDA, library versions, random seeds, and hardware.
- Begin with data validation and a simple image-level binary baseline. Train on a CPU-capable small subset to validate the pipeline; use GPU/Colab/Kaggle only when needed and permitted. No cloud GPU is required to build the web prototype.
- Recommended first model: ImageNet-pretrained ResNet18 or EfficientNet-B0, replace classification head with 2 logits, resize/pad consistently, normalize consistently, train head then selectively fine-tune. Save best checkpoint based on validation criterion and save class mapping/preprocessing/config alongside weights.
- Split before augmentation, at group level. Keep the test set sealed until model selection is finished. Avoid image-level random splits when multiple views of a case could cross sets. No test-time tuning.
- Use mild, clinically plausible augmentations (small rotations/translations, crop/brightness variation). Avoid vertical flips and aggressive transformations that alter anatomy or erase lesions. Log examples of all transforms.
- Address imbalance with class weights or a weighted sampler; compare to unweighted baseline. Do not duplicate data across train/test. State whether reported metrics are image-level or case-level.

### Tasks and evaluation

1. **Classification first:** normal vs tumour. Report confusion matrix, sensitivity/recall, specificity, precision, F1, ROC-AUC and PR-AUC with confidence intervals where feasible. Include per-class support and threshold-selection method. Report calibration/uncertainty if implemented. Analyze false negatives and false positives with advisor input.
2. **Three class only if valid labels:** normal / benign / malignant. Evaluate per-class recall and confusion matrix. The malignant class is small; avoid a headline accuracy score and clearly show uncertainty from small sample size.
3. **Localization second:** use provided boxes with a detector such as a small YOLO configuration only if data conversion is reliable. Evaluate IoU and detection precision/recall at explicitly stated thresholds. State that dataset annotations may not be available for all normal images and that a box detector is a separate task from classification.
4. **Segmentation optional:** train a small U-Net only if masks are clean, sufficient, and time remains. Report Dice/IoU against masks, not Grad-CAM overlap as if it were segmentation.
5. **Explainability:** generate Grad-CAM for the classifier and show it with a label that says “model attention explanation.” It is qualitative and not a clinical boundary. Compare visually with ground-truth annotations only as a research analysis.
6. **Model artifact:** checkpoint + preprocessing configuration + class names + model version + training manifest hash + evaluation JSON. No patient identifiers in logs.

Milestone: reproducible command trains/evaluates the baseline, outputs metrics and figures, and reloads the saved checkpoint for single-image inference.

## 4. Case library and data model

Use SQLite for the demonstrator (PostgreSQL if multi-user hosted use is actually needed). Suggested entities:

```text
Case(id, source, source_case_id, title, anatomy, projection, age_band?, sex?, text_status, rights_note, created_at)
Image(id, case_id FK, relative_path, sha256, modality, view, width, height, annotation_path?, source_url)
CaseText(id, case_id FK, text, text_type, source_url, rights_note, is_synthetic, reviewed_by, reviewed_at)
Analysis(id, case_id FK, image_id FK, model_version, task, prediction_json, created_at, status)
Document(id, case_id FK nullable, title, source_url, license_note, checksum, extraction_status)
```

Foreign keys are mandatory. An analysis request includes `case_id` and `image_id`; backend verifies `Image.case_id == requested case_id` before loading file or text. Never accept independent image and report dropdown selections. Missing case text is represented as “No linked description available,” not silently filled from another case. Log source, image checksum, license, text provenance, and synthetic status. For real medical case data, minimize age/sex detail and remove identifiers.

### API sketch (FastAPI)

- `GET /api/v1/cases?query=&anatomy=&status=&page=` → case metadata, never raw unfiltered filesystem paths.
- `GET /api/v1/cases/{case_id}` → same-case metadata, image references, linked description and source provenance.
- `GET /api/v1/cases/{case_id}/images/{image_id}` → access-controlled image bytes after FK verification.
- `POST /api/v1/cases/{case_id}/analyze` body `{image_id, task}` → validates linkage, returns job/result ID and versioned prediction.
- `GET /api/v1/analyses/{analysis_id}` → outputs and limitations.
- Optional `POST /api/v1/cases/{case_id}/ask` body `{question}` → retrieval restricted to that case and approved source corpus, returns answer plus citations.
- Optional `POST /api/v1/reports/extract` → upload with size/type limits, retention policy, consent/permission, OCR only if text extraction fails.

Return explicit errors for missing image, mismatched case/image, unsupported image, missing model, and no linked text. Include model version and `research_only: true` in every inference response.

## 5. Report analysis and RAG (optional after image workflow)

### Report analyzer

Use `pypdf` for text-first PDFs; detect sparse/empty extraction and use Tesseract OCR only if necessary. Extract text, normalize whitespace, preserve page references, and let the user inspect source text. Traditional code should identify sections and explicit terms, dates, units, and negation with transparent rules. An LLM can simplify/summarize only after extraction, with a prompt to use supplied text only and preserve uncertainty. Display source snippets and “not present in report” for missing facts. Never infer diagnosis from image classification or invent a formal radiologist report. A generated summary is not a replacement report.

### RAG assistant

Start with a small, vetted, versioned set of open-access clinical education/guideline sources whose reuse terms permit the intended handling. Store source title, URL, author/publisher, date, licence, retrieval date, and extracted chunk IDs. Extract/clean with `pypdf`; chunk by headings/paragraphs; embed using a local sentence-transformer model; begin with SQLite FTS or Chroma local. Add vector search only if retrieval tests show a need. Prompt with retrieved snippets and selected case text; require citations for sourced claims and an explicit no-answer when evidence is absent. Do not let broad medical retrieval claim facts about the selected case. Keep the image model separate from the LLM.

Evaluate a hand-written question set: answerability, source recall@k, citation correctness, unsupported-claim rate, and refusal on missing evidence. A small evaluation with human review is more defensible than claiming clinical-grade safety. Any hosted LLM sends prompts externally; disclose this, minimize transmitted data, and prefer synthetic/demo text unless approved privacy terms exist.

## 6. Web app, infrastructure, and division of work

### Frontend pages

1. Worklist: search/filter, case pattern/status, explicit teaching/research labels.
2. Case workspace: dark image canvas, pan/zoom/window-level controls if supported, selected image, linked case description, overlays toggle, model result/version/uncertainty, source and limitations.
3. Report tab: original extracted text beside any generated plain-language explanation.
4. Knowledge/assistant panel: selected-case grounding, cited sources, no-answer state.
5. About/method page: data provenance, intended use, model card and evaluation.

The current React/Vite interface implements the first pass of the worklist/workspace visual flow. Replace generated X-ray art and static records only after data permission and image-to-case manifest exist. Use responsive design and keyboard-accessible controls.

### Practical stack

| Need | Suggested option | Essential? | Cost/licensing note |
|---|---|---:|---|
| UI | React + Vite (already built) | Yes | Open source; local development free. Google Fonts currently load via network; bundle fonts locally or add system fallback for offline deployments. |
| API | FastAPI + Pydantic | Yes for real inference | Open source; local service is free. |
| Database | SQLite + SQLModel/SQLAlchemy | Yes for provenance/library | Open source; no managed cost for a single-user demo. |
| ML | PyTorch + torchvision | Yes | Open source; training compute depends on hardware. Start CPU/small GPU; optional hosted notebooks have quotas and changing terms. |
| Image viewer | HTML canvas/custom React initially; Cornerstone only if DICOM becomes required | Basic viewer yes | Add DICOM stack only for actual DICOM needs; BTXRD is JPEG according to its paper. |
| Experiment tracking | CSV/JSON + Git commit/hash first; MLflow optional | Basic logs yes | Local MLflow is open source; hosted tracking not needed initially. |
| RAG | Local embeddings + SQLite FTS/Chroma | Optional | Local/open source; hosted embeddings/LLM incur usage costs and data-transfer terms. |
| PDF/OCR | pypdf; Tesseract optional | Optional | Open source; avoid OCR until PDFs are in scope. |
| Storage | Local `data/` excluded from Git; model artifacts separately | Yes | Free locally; cloud object storage costs and permissions need assessment. |
| Packaging | Docker Compose (UI + API) | Strong stretch | Open source; hosting/container costs vary. |
| Hosting/monitoring | Local demo first; only then a small managed host | Optional | Free tiers change; never promise a free tier or upload sensitive case data without review. |

### Work split and integration gates

- **Student (owner):** literature, permissions, dataset manifest, model pipeline, API contract, UI, integration, evaluation, thesis and demo.
- **Technical collaborator:** take a bounded module such as dataset parser/annotation conversion or API image inference, with a written interface and shared branch/PR. They must not independently change label semantics or dataset split policy.
- **Clinical advisor:** review label wording, case descriptions, uncertainty and user flow at milestone meetings; no expectation to label the entire dataset or provide patient scans.
- **Gate A:** dataset manifest and case-image linkage approved before model training/UI real data.
- **Gate B:** stable model input/output schema and saved checkpoint before frontend inference integration.
- **Gate C:** evaluation and advisor feedback documented before external demo.

## 7. Clinical advisor and claims

Meet at project start, after scope/data inspection, after first model outputs, before final UI freeze, and before the final demonstration (about five focused sessions). Ask: which wording sounds diagnostic; what uncertainty and missing views should be surfaced; what image quality problems matter; what constitutes a useful localization display; what a trainee might misunderstand; and whether the output overstates the evidence. Ask them to review synthetic examples initially and a small permitted sample later. Record date, questions, feedback, decisions, and changes in `documentation/clinical_advisor_log.md`.

Do not claim clinical validation, diagnostic accuracy in practice, or readiness to guide care. A test split from a research dataset is internal retrospective evaluation, not prospective or external clinical validation. Do not collect hospital records unless ethics, institutional approval, data-use agreements, security and project supervision explicitly cover it; private data is not required for this scope.

## 8. Evaluation and completion criteria

- **Data QA:** all manifest image paths resolve; image IDs unique; annotations join to intended images; split groups do not cross splits; every exclusion is logged.
- **Model:** training is reproducible; held-out test used once; report all preselected metrics with class support and confusion matrix; compare baseline and candidate; include errors, subgroup caveats, and threshold rationale. Select thresholds from validation according to the intended research question, not arbitrary medical cutoffs.
- **Localization:** report box/mask metrics with threshold definitions and sample counts; demonstrate no claim that heatmaps are segmentation.
- **API:** valid image returns schema; mismatched case/image rejected; missing model/asset handled; response includes model version and research-only flag.
- **Frontend:** case selection updates image, narrative, and analysis as one atomic case; no stale result after selection; absent narrative clearly shown; works at target desktop and laptop widths.
- **Assistant (if built):** citations resolve; answer supported by cited text; empty retrieval yields refusal; no case cross-contamination; manually reviewed test set and failure examples documented.
- **Security/privacy:** enforce file size/type and path safety; do not log raw medical text; remove identifiers; document retention; inspect dependencies and secrets before any hosted deployment.
- **User acceptance:** 3–5 classmates/advisors can select a case, identify its linked text, find the model limitations, and explain why the score is not a diagnosis. This is usability feedback, not clinical validation.

Use the CLAIM checklist to structure reporting and the review's recommendations for intended setting, reproducibility, explainability, and bias considerations. Report exact cohort/split/task so other students can reproduce the result.

## 9. Sixteen-week implementation roadmap

Assumption: roughly 8–12 hours/week during term. Shift weeks to match the university calendar; do not compress data permission and evaluation gates.

| Week | Objective and concrete work | Owner / tools | End-of-week demonstration |
|---:|---|---|---|
| 1 | Confirm scope, advisor, risk register, user stories; map MVP vs stretch; start literature matrix. | Student; advisor meeting | Scope one-pager and intended-use statement. |
| 2 | Read BTXRD paper/review/task studies; inspect dataset record and reuse terms; download only after terms are recorded. MedPix feasibility sample. | Student | Literature matrix, rights checklist, MedPix decision in progress. |
| 3 | Inventory BTXRD files, labels, annotations, duplicates, quality and case grouping; draft dataset card. | Student/collaborator; Python/pandas | Data QA report and manifest prototype, no model yet. |
| 4 | Finalize task labels and group split; freeze train/validation/test manifest; write case schema and API contract. Decide MedPix include/exclude. | Both; advisor reviews terminology | Split audit, schema, source/permission decision. |
| 5 | Implement reproducible loaders/transforms and visual QA grid; establish baseline training script and environment lock. | Student; PyTorch | Batch and augmentation inspection; reproducible training command. |
| 6 | Train binary baseline; log config, loss, metrics; choose checkpoint via validation only. | Student | First validation curves and saved checkpoint. |
| 7 | Evaluate held-out test once; error review, subgroup counts, imbalance comparison; revise only based on validation. | Student/advisor reviews errors | Model evaluation report draft and confusion matrix. |
| 8 | Add calibration/uncertainty/review-needed exploration; document if insufficient time or evidence. | Student | Example prediction with model version and uncertainty limitations. |
| 9 | Convert/verify boxes; run small detector experiment or decide to stop at classification. | Student + collaborator | Annotation overlay QA and go/no-go memo. |
| 10 | Evaluate localization if go; compare boxes to annotations; optionally test segmentation only if masks and compute support it. | Student | Localization metric table and honest failure examples. |
| 11 | Implement FastAPI case and inference endpoints; validate case-image FK; load checkpoint once; add versioned schema. | Collaborator API / student integration | Swagger demo predicts one permitted sample; mismatch request rejected. |
| 12 | Connect React worklist/viewer to case API; replace demo art only with permitted images; atomically update same-case text. | Both | Click case → matching image, linked text, analysis, source. |
| 13 | Add report extraction only if genuine linked documents and permissions exist; otherwise improve plain-text case panel. | Student | Source text and any parsed text are distinguishable; extraction limitations shown. |
| 14 | Optional small cited RAG corpus, answerable/unanswerable test questions; or use week for UI/usability polish. | Student | Citation shown for supported question; no-evidence question refused. |
| 15 | Integration, API/UI/data/privacy checks; advisor review; Docker/local demo; finalize model card and documentation. | Both + advisor | Clean-run demo and completed checklist. |
| 16 | Freeze scope; write evaluation/limitations, final presentation, backup demo data and video/screenshots; rehearse. | Student | Reproducible final demonstration and submitted project package. |

### Dependencies and stop rules

Do not start RAG before the case IDs and provenance are stable. Do not connect real images before source rights and case links are recorded. Do not start detection/segmentation before classification pipeline and annotation QA work. If Weeks 1–4 reveal no defensible group split or usable label mapping, change the contribution to dataset audit + UI + a carefully qualified baseline rather than claiming generalizable diagnosis. If the model result is weak, present it honestly; a sound evaluation and safe interface remain valid software engineering contributions.

## 10. Final deliverables checklist

- React application and run instructions; FastAPI service if model integration completed.
- Dataset manifest, preparation/validation scripts, dataset card, source/license notes; no dataset dump in Git.
- Versioned model checkpoint and full config, only if redistribution terms permit; otherwise reproducible training instructions and a locally generated artifact.
- Evaluation report with split methodology, metrics, subgroup/uncertainty and error analysis.
- Case library with immutable linkage, provenance and missing-data behavior.
- Optional report/RAG modules with source citations and evaluation.
- Architecture/API documentation, dependency lock, test evidence, privacy/security notes.
- Literature review, advisor log, limitations, final poster/slides and demonstrated end-to-end scenario.
