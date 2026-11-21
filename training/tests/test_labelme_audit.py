import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from training.src.labelme_audit import audit_labelme_dataset


class LabelMeAuditTests(unittest.TestCase):
    def test_image_join_dimensions_and_source_class_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            images = root / "images"
            annotations = root / "Annotations"
            images.mkdir(); annotations.mkdir()
            Image.new("RGB", (64, 48), color=(40, 80, 120)).save(images / "IMG000001.jpeg")
            Image.new("RGB", (64, 48), color=(90, 20, 30)).save(images / "IMG000002.jpeg")
            (root / "dataset.csv").write_text(
                "image_id,benign,malignant,tumor\nIMG000001.jpeg,0,0,0\nIMG000002.jpeg,1,0,1\n",
                encoding="utf-8",
            )
            (annotations / "IMG000002.json").write_text(json.dumps({
                "imagePath": "../images/IMG000002.jpeg",
                "imageWidth": 64,
                "imageHeight": 48,
                "shapes": [{"label": "lesion", "shape_type": "polygon", "points": [[1, 2], [3, 4], [5, 2]]}],
            }), encoding="utf-8")

            report = audit_labelme_dataset(root)

            self.assertEqual(report["image_file_count"], 2)
            self.assertEqual(report["unique_images_matched"], 1)
            self.assertEqual(report["source_tumor_records_missing_annotation"], [])
            self.assertEqual(report["source_normal_records_with_annotation"], [])
            row = report["records"][0]
            self.assertEqual(row["join_status"], "matched")
            self.assertEqual(row["matched_image"], "IMG000002.jpeg")
            self.assertTrue(row["dimensions_match"])
            self.assertEqual(row["dimension_status"], "match")
            self.assertEqual(row["usable_polygon_or_rectangle_count"], 1)
            self.assertEqual(report["shape_label_text_categories"]["label_text_suggests_lesion_or_tumour"], 1)
            self.assertIn("clinical meaning requires annotation protocol/source documentation", report["localization_semantics_limit"])
            self.assertEqual(report["source_class_annotation_coverage"]["Benign"]["annotated_image_count"], 1)
            metadata = report["metadata_audit"]
            self.assertEqual(metadata["metadata_file"], "dataset.csv")
            self.assertEqual(metadata["columns"], ["image_id", "benign", "malignant", "tumor"])
            self.assertEqual(metadata["matched_metadata_image_count"], 2)

    def test_missing_dimensions_and_invalid_shape_entries_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            images = root / "images"; annotations = root / "Annotations"
            images.mkdir(); annotations.mkdir()
            Image.new("RGB", (30, 20)).save(images / "sample.png")
            (annotations / "sample.json").write_text(
                json.dumps({"shapes": ["not-a-shape-object"]}), encoding="utf-8"
            )
            report = audit_labelme_dataset(root)
            self.assertEqual(report["image_file_count"], 1)
            self.assertEqual(report["annotation_json_count"], 1)
            self.assertEqual(report["malformed_annotations"][0]["annotation"].replace("\\", "/"), "Annotations/sample.json")
            self.assertEqual(report["images_without_annotation_count"], 1)
            self.assertEqual([p.replace("\\", "/") for p in report["images_without_annotations"]], ["images/sample.png"])

    def test_orphan_annotation_is_reported_without_inventing_join(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "images").mkdir(); (root / "Annotations").mkdir()
            (root / "Annotations" / "IMG999999.json").write_text(
                json.dumps({"shapes": []}), encoding="utf-8"
            )
            report = audit_labelme_dataset(root)
            self.assertEqual(Path(report["orphan_annotations"][0]).as_posix(), "Annotations/IMG999999.json")
            self.assertEqual(report["unique_images_matched"], 0)


if __name__ == "__main__":
    unittest.main()
