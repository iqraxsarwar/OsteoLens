"""Read-only audit of BTXRD LabelMe JSON to source-image joins.

The audit reports observed file joins and annotation geometry only. It does not
create labels, repair annotations, train localization, or assess clinical truth.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


def _normalized_column(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _source_flag(value: Any) -> bool | None:
    if value is None:
        return None
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "y"}:
        return True
    if raw in {"0", "false", "no", "n"}:
        return False
    return None


def _source_label(row: dict[str, Any], columns: dict[str, str]) -> str | None:
    for key in ("classification", "class", "broad_class", "diagnosis"):
        if key in columns:
            raw = str(row.get(columns[key]) or "").strip().lower()
            if raw in {"normal", "normal bone"}:
                return "Normal"
            if "benign" in raw:
                return "Benign"
            if "malignant" in raw:
                return "Malignant"
    benign = _source_flag(row.get(columns["benign"])) if "benign" in columns else None
    malignant = _source_flag(row.get(columns["malignant"])) if "malignant" in columns else None
    tumor = _source_flag(row.get(columns["tumor"])) if "tumor" in columns else None
    if benign is True and malignant is True:
        return None
    if malignant is True:
        return "Malignant"
    if benign is True:
        return "Benign"
    if tumor is False:
        return "Normal"
    return None


def _valid_points(shape: dict[str, Any]) -> bool:
    shape_type = str(shape.get("shape_type") or "").casefold()
    required = 3 if shape_type == "polygon" else 2 if shape_type == "rectangle" else None
    points = shape.get("points")
    if required is None or not isinstance(points, list) or len(points) < required:
        return False
    try:
        return all(
            isinstance(point, (list, tuple))
            and len(point) >= 2
            and math.isfinite(float(point[0]))
            and math.isfinite(float(point[1]))
            for point in points
        )
    except (TypeError, ValueError):
        return False


def _points_within_image(shape: dict[str, Any], width: int, height: int) -> bool:
    try:
        return all(
            0 <= float(point[0]) <= width and 0 <= float(point[1]) <= height
            for point in shape.get("points", [])
        )
    except (TypeError, ValueError, IndexError):
        return False


def audit_labelme_dataset(dataset_root: str | Path) -> dict[str, Any]:
    """Audit annotation joins, source class coverage, geometry and dimensions.

    Expected dataset layout may be nested, but must contain directories named
    `images` and `Annotations` (case-insensitive). `dataset.csv` is optional;
    without recognizable source IDs/classes, those coverage counts are null.
    """
    root = Path(dataset_root).resolve()

    discovered_dirs: list[Path] = []
    for current, dirs, _ in os.walk(root):
        dirs.sort()
        discovered_dirs.extend(Path(current) / name for name in dirs)
    image_dirs = [path for path in discovered_dirs if path.name.casefold() == "images"]
    annotation_dirs = [path for path in discovered_dirs if path.name.casefold() == "annotations"]
    if not image_dirs or not annotation_dirs:
        raise FileNotFoundError("Dataset root must contain images/ and Annotations/ directories.")

    image_paths = sorted(
        path for images_dir in image_dirs for path in images_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".mpo"}
    )
    image_index: dict[str, list[Path]] = defaultdict(list)
    for path in image_paths:
        image_index[path.stem.casefold()].append(path)

    accepted_metadata_names = {"dataset.csv", "dataset.xlsx", "dataset.xls"}
    metadata_paths = [
        path for path in root.rglob("*")
        if path.is_file() and path.name.casefold() in accepted_metadata_names
    ]
    metadata_path = metadata_paths[0] if metadata_paths else None
    if len(metadata_paths) > 1:
        image_parent_dirs = {path.parent for path in image_dirs}
        siblings = [path for path in metadata_paths if path.parent in image_parent_dirs]
        if len(siblings) == 1:
            metadata_path = siblings[0]
        else:
            raise ValueError("Multiple supported dataset metadata files were found; refusing to infer which labels belong to this image tree.")
    metadata_audit: dict[str, Any] = {
        "metadata_file": str(metadata_path.relative_to(root)) if metadata_path else None,
        "image_id_column": None,
        "columns": [],
        "class_mapping": "unavailable",
        "rows": None,
        "source_class_counts": {},
        "rows_without_resolved_class": None,
    }
    class_by_image: dict[str, list[str | None]] = defaultdict(list)
    metadata_image_keys: list[str] = []
    if metadata_path:
        if metadata_path.suffix.casefold() == ".csv":
            with metadata_path.open("r", encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
        else:
            try:
                import pandas as pd

                frame = pd.read_excel(metadata_path)
                rows = frame.where(pd.notna(frame), None).to_dict(orient="records")
            except Exception as exc:
                raise RuntimeError(
                    f"Could not read metadata file {metadata_path.name}; install pandas and the matching Excel reader."
                ) from exc
        columns = {
            _normalized_column(column): column
            for column in (rows[0].keys() if rows else [])
        }
        metadata_audit["columns"] = [str(column) for column in (rows[0].keys() if rows else [])]
        id_column = next(
            (columns[key] for key in ("image_id", "image", "filename") if key in columns),
            None,
        )
        label_columns = {"classification", "class", "broad_class", "diagnosis", "benign", "malignant", "tumor"}
        metadata_audit["rows"] = len(rows)
        metadata_audit["image_id_column"] = id_column
        has_source_labels = bool(label_columns & set(columns))
        if id_column and has_source_labels:
            metadata_audit["class_mapping"] = "explicit source class/diagnosis or benign/malignant/tumor flags"
            class_counts: Counter[str] = Counter()
            unresolved_classes = 0
            for row in rows:
                image_value = str(row.get(id_column) or "").replace("\\", "/")
                key = Path(image_value).stem.casefold()
                if key:
                    metadata_image_keys.append(key)
                    label = _source_label(row, columns)
                    class_by_image[key].append(label)
                    if label is None:
                        unresolved_classes += 1
                    else:
                        class_counts[label] += 1
            metadata_audit["source_class_counts"] = dict(class_counts)
            metadata_audit["rows_without_resolved_class"] = unresolved_classes
        elif not id_column:
            metadata_audit["class_mapping"] = "unavailable: no recognized image ID column"
        elif not has_source_labels:
            metadata_audit["class_mapping"] = "unavailable: no recognized source class columns"
            for row in rows:
                image_value = str(row.get(id_column) or "").replace("\\", "/")
                key = Path(image_value).stem.casefold()
                if key:
                    metadata_image_keys.append(key)

    metadata_key_counts = Counter(metadata_image_keys)
    metadata_audit["matched_metadata_image_count"] = sum(
        1 for key in metadata_key_counts if len(image_index.get(key, [])) == 1
    )
    metadata_audit["duplicate_image_id_rows"] = sum(count for count in metadata_key_counts.values() if count > 1)
    metadata_audit["metadata_ids_missing_image"] = sorted(
        key for key in metadata_key_counts if key not in image_index
    )
    metadata_audit["metadata_ids_with_ambiguous_image_stem"] = sorted(
        key for key in metadata_key_counts if len(image_index.get(key, [])) > 1
    )
    metadata_audit["image_files_missing_metadata_id"] = sorted(
        path.name for key, paths in image_index.items() if key not in metadata_key_counts for path in paths
    )

    annotation_paths = sorted(
        path for annotations_dir in annotation_dirs for path in annotations_dir.rglob("*")
        if path.is_file() and path.suffix.lower() == ".json"
    )
    shape_types: Counter[str] = Counter()
    shape_labels: Counter[str] = Counter()
    shape_label_categories: dict[str, str] = {}
    semantic_label_groups: Counter[str] = Counter()
    label_by_source_class: Counter[str] = Counter()
    shape_type_by_source_class: Counter[str] = Counter()
    valid_geometry_by_source_class: Counter[str] = Counter()
    source_class_annotation_counts: Counter[str] = Counter()
    format_counts: Counter[str] = Counter()
    issues: Counter[str] = Counter()
    annotation_records: list[dict[str, Any]] = []
    malformed: list[dict[str, str]] = []
    orphan_annotations: list[str] = []
    ambiguous_annotations: list[str] = []
    matched_images: set[str] = set()
    image_annotation_counts: Counter[str] = Counter()
    image_audit_records: list[dict[str, Any]] = []
    unreadable_images: list[str] = []
    for image_path in image_paths:
        relative_image = str(image_path.relative_to(root))
        try:
            with Image.open(image_path) as source_image:
                source_image.verify()
            with Image.open(image_path) as source_image:
                dimensions = [source_image.width, source_image.height]
                image_format = source_image.format
                format_counts[str(image_format or "unknown")] += 1
                readable = True
                error = None
        except (OSError, UnidentifiedImageError) as exc:
            dimensions, image_format, readable, error = None, None, False, str(exc)
            unreadable_images.append(relative_image)
            issues["unreadable_image"] += 1
        image_audit_records.append({
            "image": relative_image, "image_id": image_path.name,
            "dimensions": dimensions, "format": image_format,
            "readable": readable, "error": error,
        })

    for annotation_path in annotation_paths:
        relative_annotation = str(annotation_path.relative_to(root))
        try:
            document = json.loads(annotation_path.read_text(encoding="utf-8-sig"))
            if not isinstance(document, dict) or not isinstance(document.get("shapes"), list):
                raise ValueError("Expected LabelMe JSON object with a shapes list.")
            if any(not isinstance(shape, dict) for shape in document["shapes"]):
                raise ValueError("Each entry in shapes must be a JSON object.")
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            issues["invalid_json"] += 1
            malformed.append({"annotation": relative_annotation, "error": str(exc)})
            continue

        filename_stem = Path(annotation_path.stem).stem.casefold()
        source_image_path = str(document.get("imagePath") or "").replace("\\", "/")
        candidate_keys = {filename_stem}
        if source_image_path:
            candidate_keys.add(Path(source_image_path).stem.casefold())
        matched_paths = {
            str(candidate.resolve()): candidate
            for key in candidate_keys
            for candidate in image_index.get(key, [])
        }

        if len(matched_paths) == 1:
            matched_image = next(iter(matched_paths.values()))
            matched_images.add(str(matched_image.resolve()))
            join_status = "matched"
            try:
                with Image.open(matched_image) as source_image:
                    actual_size: list[int] | None = [source_image.width, source_image.height]
                json_width, json_height = document.get("imageWidth"), document.get("imageHeight")
                json_size = [json_width, json_height]
                if json_width is None and json_height is None:
                    dimensions_match = None
                    dimension_status = "unavailable_in_json"
                    issues["annotation_dimensions_missing"] += 1
                elif json_width is None or json_height is None:
                    dimensions_match = False
                    dimension_status = "incomplete_in_json"
                    issues["annotation_dimensions_incomplete"] += 1
                else:
                    dimensions_match = json_size == actual_size
                    dimension_status = "match" if dimensions_match else "mismatch"
                if dimensions_match is False:
                    issues["dimension_mismatch"] += 1
            except (OSError, UnidentifiedImageError):
                actual_size = None
                dimensions_match = False
                dimension_status = "matched_image_unreadable"
                issues["unreadable_matched_image"] += 1
            image_id: str | None = matched_image.name
        elif len(matched_paths) > 1:
            matched_image = None
            join_status = "ambiguous"
            actual_size = None
            dimensions_match = None
            dimension_status = "not_checked_unmatched"
            image_id = None
            ambiguous_annotations.append(relative_annotation)
            issues["ambiguous_join"] += 1
        else:
            matched_image = None
            join_status = "orphan"
            actual_size = None
            dimensions_match = None
            dimension_status = "not_checked_unmatched"
            image_id = None
            orphan_annotations.append(relative_annotation)
            issues["unmatched_annotation"] += 1

        source_label_values = class_by_image.get(matched_image.stem.casefold(), []) if matched_image else []
        source_label = source_label_values[0] if len(source_label_values) == 1 else None
        if len(source_label_values) > 1:
            issues["duplicate_metadata_ids"] += 1
        if source_label:
            source_class_annotation_counts[source_label] += 1

        usable_geometry = 0
        geometry_out_of_bounds = 0
        for shape in document["shapes"]:
            shape_type = str(shape.get("shape_type") or "missing").casefold()
            shape_label = str(shape.get("label") or "missing")
            shape_types[shape_type] += 1
            shape_labels[shape_label] += 1
            shape_type_by_source_class[f"{source_label or 'unresolved'}::{shape_type}"] += 1
            normalized_label = shape_label.strip().casefold()
            if re.search(r"tumou?r|neoplasm|lesion|mass", normalized_label):
                semantic_group = "label_text_suggests_lesion_or_tumour"
            elif normalized_label in {"normal", "background", "bone"}:
                semantic_group = "generic_or_normal_label"
            elif normalized_label == "missing":
                semantic_group = "missing_label"
            else:
                semantic_group = "other_label_requires_review"
            semantic_label_groups[semantic_group] += 1
            shape_label_categories[shape_label] = semantic_group
            label_by_source_class[f"{source_label or 'unresolved'}::{shape_label}"] += 1
            if shape_type in {"polygon", "rectangle"} and _valid_points(shape):
                usable_geometry += 1
                valid_geometry_by_source_class[source_label or "unresolved"] += 1
                if actual_size and not _points_within_image(shape, actual_size[0], actual_size[1]):
                    geometry_out_of_bounds += 1
                    issues["localization_geometry_out_of_image_bounds"] += 1
            elif shape_type in {"polygon", "rectangle"}:
                issues["invalid_localization_geometry"] += 1

        annotation_records.append({
            "annotation": relative_annotation,
            "imagePath": document.get("imagePath"),
            "matched_image": image_id,
            "join_status": join_status,
            "source_label_if_resolved": source_label,
            "json_dimensions": [document.get("imageWidth"), document.get("imageHeight")],
            "actual_image_dimensions": actual_size,
            "dimensions_match": dimensions_match,
            "dimension_status": dimension_status,
            "shape_count": len(document["shapes"]),
            "usable_polygon_or_rectangle_count": usable_geometry,
            "geometry_out_of_image_bounds_count": geometry_out_of_bounds,
        })
        if matched_image is not None:
            image_annotation_counts[str(matched_image.resolve())] += 1

    metadata_label_available = metadata_audit["class_mapping"].startswith("explicit")
    labels_by_image = {
        key: values[0] for key, values in class_by_image.items() if len(values) == 1
    }
    tumor_image_keys = {
        key for key, label in labels_by_image.items() if label in {"Benign", "Malignant"}
    }
    normal_image_keys = {key for key, label in labels_by_image.items() if label == "Normal"}
    annotated_stems = {Path(path).stem.casefold() for path in matched_images}
    tumor_missing = sorted(tumor_image_keys - annotated_stems) if metadata_label_available else None
    normal_annotated = sorted(normal_image_keys & annotated_stems) if metadata_label_available else None
    class_coverage = {}
    if metadata_label_available:
        for label in ("Normal", "Benign", "Malignant"):
            class_keys = {key for key, value in labels_by_image.items() if value == label}
            annotated_keys = class_keys & annotated_stems
            class_coverage[label] = {
                "metadata_image_count": len(class_keys),
                "annotated_image_count": len(annotated_keys),
                "unannotated_image_count": len(class_keys - annotated_keys),
                "annotation_coverage_fraction": len(annotated_keys) / len(class_keys) if class_keys else None,
            }

    localization_geometry = sum(
        record["usable_polygon_or_rectangle_count"] for record in annotation_records
    )
    lesion_named_shapes = sum(
        shape_labels[label] for label in shape_labels
        if re.search(r"tumou?r|neoplasm|lesion|mass", label, flags=re.IGNORECASE)
    )
    if localization_geometry == 0:
        localization_assessment = "not_supported_by_valid_rectangle_or_polygon_geometry"
    elif lesion_named_shapes == 0:
        localization_assessment = "geometry_exists_but_labels_do_not_explicitly_suggest_tumour_or_lesion"
    else:
        localization_assessment = "candidate_geometry_and_lesion_like_label_text_found_but_clinical_semantics_unverified"

    for image_record in image_audit_records:
        image_path = root / image_record["image"]
        record_key = str(image_path.resolve())
        image_record["annotation_count"] = image_annotation_counts.get(record_key, 0)
        image_record["has_annotation"] = image_record["annotation_count"] > 0
        source_values = class_by_image.get(Path(image_record["image_id"]).stem.casefold(), [])
        image_record["source_label_if_resolved"] = (
            source_values[0] if len(source_values) == 1 else None
        )

    return {
        "status": "completed",
        "dataset_root": str(root),
        "image_directories": [str(path.relative_to(root)) for path in image_dirs],
        "annotation_directories": [str(path.relative_to(root)) for path in annotation_dirs],
        "metadata_audit": metadata_audit,
        "image_file_count": len(image_paths),
        "image_count_by_format": dict(format_counts),
        "unreadable_images": unreadable_images,
        "image_records": image_audit_records,
        "duplicate_image_stems": {
            key: [str(path.relative_to(root)) for path in values]
            for key, values in image_index.items() if len(values) > 1
        },
        "annotation_json_count": len(annotation_paths),
        "valid_annotation_count": len(annotation_records),
        "unique_images_matched": len(matched_images),
        "images_without_annotation_count": len(image_paths) - len(matched_images),
        "images_without_annotations": [
            str(path.relative_to(root)) for path in image_paths
            if str(path.resolve()) not in matched_images
        ],
        "orphan_annotations": orphan_annotations,
        "ambiguous_annotations": ambiguous_annotations,
        "malformed_annotations": malformed,
        "source_tumor_records_missing_annotation": tumor_missing,
        "source_normal_records_with_annotation": normal_annotated,
        "source_class_annotation_coverage": class_coverage if metadata_label_available else None,
        "annotation_counts_by_source_class": dict(source_class_annotation_counts),
        "shape_type_counts": dict(shape_types),
        "shape_label_counts": dict(shape_labels),
        "shape_label_interpretation_heuristic": {
            label: {"count": shape_labels[label], "text_category": category}
            for label, category in sorted(shape_label_categories.items())
        },
        "shape_label_counts_by_source_class": dict(label_by_source_class),
        "shape_type_counts_by_source_class": dict(shape_type_by_source_class),
        "valid_rectangle_or_polygon_counts_by_source_class": dict(valid_geometry_by_source_class),
        "shape_label_text_categories": dict(semantic_label_groups),
        "issues": dict(issues),
        "records": annotation_records,
        "annotation_records": annotation_records,
        "localization_assessment": localization_assessment,
        "localization_semantics_limit": (
            "Shape geometry and label strings are structural evidence only. LabelMe labels do not, by themselves, "
            "prove that the drawn region is a tumour boundary; clinical meaning requires annotation protocol/source "
            "documentation and expert review. No localization suitability or accuracy is claimed by this audit."
        ),
        "interpretation_limit": (
            "Join/geometry audit only; it does not establish annotation clinical validity "
            "or localization-model performance."
        ),
    }
