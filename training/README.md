# OsteoLens Phase 3 — Colab training guide

This package prepares a reproducible BTXRD ResNet-18 training run. The notebook verifies the archive metadata against the public Figshare API, then downloads directly into Colab's temporary `/content` storage and checks its expected byte size, MD5 and every ZIP member CRC. Dataset inspection and audit outputs run in `/content` without Google Drive. Google Drive is mounted only at the training stage to preserve run outputs. The full archive is not stored in this repository or downloaded to your laptop. The trained checkpoint has since been made available locally under `../models/checkpoints/`; report metrics were supplied by the project owner and are not independently reproduced by this training-preparation package.

## Run it in Google Colab

1. Open [Google Colab](https://colab.research.google.com/) and upload/open `osteolens_colab.ipynb` (`File → Upload notebook`). The notebook itself is small; no dataset transfer from your computer is needed.
2. Choose `Runtime → Change runtime type → T4 GPU` (or another GPU if available). You do not need to connect Google Drive for download, inspection, or split review.
3. Run cells 1–8 in order. Cell 3 installs helper libraries and leaves Colab's PyTorch/torchvision build intact. Cell 4 queries the Figshare public article API and confirms the exact article/file IDs, expected size, MD5, and API-provided download URL before downloading. It shows progress, retries transient failures, resumes `.part` downloads with HTTP Range when supported, rejects empty/incomplete responses, verifies the ZIP CRCs, and safely extracts under `/content`. A failed exhausted download removes incomplete files; rerunning begins cleanly.
4. Review the outputs through cell 8: actual metadata columns/labels and counts, image matches/readability, annotation counts and examples, completeness check, and split manifest. Audit files are saved locally in `/content/OsteoLensRuns/BTXRD/`. Missing labels or annotations are reported, not invented.
5. Inspect the preprocessing sample and split in cells 9–10. When satisfied, edit `CONFIRM_TRAINING = False` to `True` in cell 1, then run cells 12–15 in order. Cell 12 mounts Drive and copies the audit/split files there before training. The training gate prevents accidental training before review. Training may take a long time; keep the Colab session active.
6. Cell 15 writes the final checkpoint, class map, preprocessing config, metrics, test predictions, training history and confusion-matrix image to Drive. Download these from Drive only if you need a local copy. Do not treat scores as clinical probabilities or diagnoses.

Do not use `Runtime → Run all` before reviewing the audit and split. With the default training flag, the notebook deliberately raises at the training cell and does not start fitting.

## What the data audit checks

The notebook discovers the actual extracted folder names rather than assuming a fixed ZIP layout. It searches for JPEG/JPG images, `dataset.csv` / `.xlsx` / `.xls`, and LabelMe JSON files. It reports the actual class counts, missing/unreferenced/duplicate image files, unreadable images, malformed annotations, annotation shape labels/types/dimensions, and tumor-labeled records without a matching JSON. It requires a one-to-one, readable, labeled set of 3,746 source records before training; 3,746 is a verification target, not an assumed result. Annotation files are audited but are not used as invented classification labels or localization targets in Phase 3.

The splitter uses a source patient/subject ID only if such a field is present and complete. Otherwise it groups exact and visually near-duplicate images (SHA-256 and pHash). This cannot guarantee that different views from the same unidentified patient stay together. Group overlap and per-split class representation are checked; if stratified grouped splits cannot satisfy all classes, the notebook stops and asks for review rather than weakening the split silently.

## Dataset, source, and license

The archive is retrieved from the [official BTXRD Figshare record](https://doi.org/10.6084/m9.figshare.27865398.v1), article ID `27865398`, file ID `50653575`. The notebook verifies the recorded expected size `840474929`, MD5 `59132a5036d030580ccade8add8f13df`, and API-provided HTTPS URL against the live public API before downloading. It fails closed if these differ; do not edit the pins unless the official API record is reviewed. Dataset paper: [Scientific Data, 2025](https://www.nature.com/articles/s41597-024-04311-y). Figshare identifies the dataset as CC BY 4.0; retain attribution and verify any redistribution terms before sharing source images or derived packages.

The separate `../src/data/cases.json` and `../public/images/btxrd/` contain 30 provenance-tracked website browsing records only. They are not the full training set and are never used by this notebook. See the repository's `DATA_SOURCES.md` for their individual provenance.

## Model and inference contract

The notebook fine-tunes ResNet-18 with a newly trained three-class head for the source classes `Normal`, `Benign`, and `Malignant`. ImageNet weights initialize the feature extractor; the resulting classification outputs are trained against BTXRD labels and are not ImageNet predictions. Weighted cross entropy addresses training-set class imbalance. A fixed seed, grouped train/validation/test manifests, early stopping on validation macro-F1, held-out classification report, confusion matrix, sensitivity/recall, specificity, and one-vs-rest ROC-AUC (when defined) are saved. Metrics must only be reported after a real Colab run completes.

`src/inference.py` loads the checkpoint with `load_model()` using the saved preprocessing configuration and generates image-byte predictions plus Grad-CAM. The local FastAPI endpoint in `../backend/main.py` verifies the selected case image checksum before inference. It requires PyTorch/torchvision and the real `.pth` checkpoint; the checkpoint is stored under `../models/checkpoints/` in this workspace and remains excluded from Git.

## Dependencies and unresolved limits

`requirements.txt` documents notebook helper, inference and future-serving dependencies. The Colab notebook installs only the helper libraries so it does not overwrite the runtime's CUDA-matched PyTorch. Training needs network access for the first ResNet-18 ImageNet weight fetch. Colab storage, GPU availability, RAM, and session durations vary; resource checks stop when the available disk/RAM/GPU memory do not meet the notebook's conservative thresholds. The source archive remains temporary and must be downloaded again after its runtime is discarded.

The project owner has supplied a Phase 3 report with held-out test metrics; the checkpoint is now present under `../models/checkpoints/osteolens_btxrd_resnet18.pth`. Its archive metadata was inspected without executing the model: ResNet-18, class order Normal/Benign/Malignant, 256 input size, ImageNet normalization, best epoch 14, and `patient_independent_split_verified: false`. The report metrics were not independently recomputed because this workspace has no PyTorch runtime or saved `evaluation_metrics.json`/split manifest. The output remains research-only, uncalibrated, without external or clinical validation.

## BTXRD metadata and annotation review (Phase 4 follow-up)

Use `btxrd_metadata_visual_review_colab.ipynb` to read the original `MyDrive/OsteoLensRuns/BTXRD/BTXRD.zip` archive without moving it to the laptop. It verifies the archive before copying/extracting selected audit inputs to Colab `/content`, reuses `src/labelme_audit.py`, and saves the metadata reconciliation, actual image overlays, detailed JSON, and summary in `MyDrive/OsteoLensRuns/Phase4Verification/`. It runs on CPU and does not train a model or overwrite the successful verification outputs. The exact metadata filename/schema and class match counts are determined from the archive at run time; do not infer them from the paper's record count. The overlays require a human clinical reviewer before treating boxes or polygons as tumour boundaries.
