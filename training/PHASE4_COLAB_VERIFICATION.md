# Phase 4 Colab verification instructions

This verification package exercises the current Phase 4 backend and Grad-CAM code without changing/retraining the model. It uses the already trained checkpoint in Drive and the existing 30 real BTXRD sample images. It does not contain the full BTXRD archive or a checkpoint.

## Transfer these files

1. `training/phase4_verification_colab.ipynb`
2. `training/phase4_verification_bundle.zip`

The ZIP contains the existing backend and inference code, the case manifest, its 30 sample JPEGs, and the existing Grad-CAM tests. The notebook verifies the ZIP SHA-256 before extraction. The checkpoint remains in Drive at `MyDrive/OsteoLensRuns/BTXRD/osteolens_btxrd_resnet18.pth`; if it is elsewhere, the notebook searches MyDrive for that filename. Before loading, the notebook verifies the exact expected SHA-256 `32ee1c1c2b320865ade06ebdf819c2f6b3cb29e8c695ce9ea3124ecfae440756` and stops if it differs.

The bundle is approximately 7.3 MB. It does not include or copy `BTXRD.zip`, any full-dataset images, or model weights.

## Run the verification

1. Open [Google Colab](https://colab.research.google.com/), choose **File → Upload notebook**, and select `phase4_verification_colab.ipynb`.
2. Choose **Runtime → Change runtime type → GPU** if available. Sign into the Google account containing the checkpoint.
3. Run the notebook from the first cell. Approve the Google Drive mount.
4. When the upload dialog appears, choose `phase4_verification_bundle.zip`.
5. Review the result table and final PASS/FAIL/SKIP lines. The notebook calls the existing FastAPI route `POST /api/analyze/{case_id}` for five different manifest cases, selected to cover source labels Normal, Benign, and Malignant. It verifies image SHA-256 values, backend-loaded checkpoint metadata, model output/class scores, five distinct heatmap hashes, original/heatmap/overlay dimensions, non-identical overlays, invalid image rejection, and unknown case rejection.
6. Inspect `MyDrive/OsteoLensRuns/Phase4Verification/phase4_model_verification.json` and the five heatmap/overlay pairs. This report contains actual inference outputs from that Colab session. Do not describe source labels or uncalibrated scores as clinical diagnoses/probabilities.

The loader remains on `weights_only=True`; the checkpoint metadata includes the PyTorch `torch.torch_version.TorchVersion` string subclass because the training notebook saved `torch.__version__` without converting it to `str`. Inference allowlists only `TorchVersion` within a scoped `torch.serialization.safe_globals` context. No unrestricted pickle loading is used. The notebook first checks the existing Colab PyTorch/torchvision pair and does not install or upgrade either package. The checkpoint records PyTorch `2.14.1+cu130` and torchvision `0.29.1+cu130`. If Colab’s installed pair fails the import/model construction or checkpoint load, use the official CUDA 13.0 wheels only after reviewing the error:

```python
%pip install --index-url https://download.pytorch.org/whl/cu130 torch==2.14.1 torchvision==0.29.1
```

Then restart the runtime and rerun the notebook. PyTorch documents the matching 2.14.1/0.29.1 installation pair and CUDA 13.0 wheel index in its [official version matrix](https://pytorch.org/get-started/previous-versions/). TorchVision’s [0.29.1 release notes](https://github.com/pytorch/vision/releases) identify compatibility with PyTorch 2.14. Do not install the pair if the Colab runtime already loads and runs the checkpoint successfully.

## Optional full BTXRD annotation audit

The project contains only the separate 30-case sample, not the full BTXRD archive or its `Annotations/` directory. The optional final section audits a full extraction if it exists in Colab. It checks LabelMe JSON validity, filename and `imagePath` joins, ambiguous/orphan annotations, source class mapping when recognizable in `dataset.csv`, tumor records lacking annotations, shape types/labels/coordinate validity, and annotation-to-image dimension agreement. The report is saved as `labelme_annotation_matching_audit.json` in the same Drive folder.

To make the full dataset available **only in Colab**, run cells 1, 3, and 4 of the existing `training/osteolens_colab.ipynb` in the same runtime before running the optional audit cell here. Those cells retrieve and verify the official archive and extract it under `/content/BTXRD`; they do not need a laptop copy or a Drive upload. If the runtime has expired, this downloads the archive again to Colab temporary storage. The LabelMe JSON files are inside `BTXRD/Annotations/`; do not copy them into GitHub. Keep the full archive temporary and save only the compact audit report to Drive.

A completed annotation join/geometry audit is not a localization model. Localization should only be proposed after reviewing the report, resolving any join/dimension/geometry issues, and planning a distinct model with a held-out evaluation. The audit does not invent labels for unannotated images and does not treat Grad-CAM as a lesion outline.

## What counts as verification evidence

Phase 4’s model integration is verified only if the saved JSON says `verification: passed`, all five case rows are present, all three source classes are represented, the checkpoint loaded through the backend, all five heatmaps are distinct, and invalid-image/unknown-case checks pass. Any failed test must be investigated; skipped model tests do not count as verification. Annotation audit status may be `skipped` when the full archive is not available, but in that case no localization feasibility conclusion should be presented as an archive audit.
