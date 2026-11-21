import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / "models" / "checkpoints" / "osteolens_btxrd_resnet18.pth"
HAS_TORCH_STACK = all(importlib.util.find_spec(name) for name in ("torch", "torchvision", "PIL", "numpy"))


@unittest.skipUnless(HAS_TORCH_STACK, "PyTorch/torchvision are required to run real checkpoint inference")
class GradCamCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from training.src.inference import load_model

        if not CHECKPOINT.is_file():
            raise unittest.SkipTest("The trained checkpoint is not available in this workspace")
        cls.bundle = load_model(CHECKPOINT, device="cpu")
        cls.records = json.loads((ROOT / "src" / "data" / "cases.json").read_text(encoding="utf-8"))["cases"]

    def test_checkpoint_metadata_matches_expected_resnet_contract(self):
        self.assertEqual(self.bundle.class_names, ("Normal", "Benign", "Malignant"))
        self.assertEqual(self.bundle.input_size, 256)
        self.assertEqual(self.bundle.model_version, "btxrd-resnet18-seed42")

    def test_invalid_checkpoint_is_rejected(self):
        from training.src.inference import InvalidCheckpointError, load_model

        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid_path = Path(temporary_directory) / "invalid.pth"
            invalid_path.write_bytes(b"not a PyTorch checkpoint")
            with self.assertRaises(InvalidCheckpointError):
                load_model(invalid_path, device="cpu")

    def test_five_distinct_cases_generate_case_specific_gradcam(self):
        from training.src.inference import generate_gradcam_image_bytes

        chosen = []
        for label in ("Normal", "Benign", "Malignant"):
            record = next(item for item in self.records if item["classification"] == label)
            chosen.append(record)
        for record in self.records:
            if record not in chosen and len(chosen) < 5:
                chosen.append(record)

        results = []
        for record in chosen:
            image_path = ROOT / "public" / "images" / "btxrd" / record["image_id"]
            image_bytes = image_path.read_bytes()
            self.assertEqual(hashlib.sha256(image_bytes).hexdigest(), record["sha256"])
            result = generate_gradcam_image_bytes(image_bytes, self.bundle)
            self.assertIn(result["prediction"], self.bundle.class_names)
            self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0, places=5)
            self.assertEqual(result["localization"]["status"], "unavailable")
            for key in ("gradcam_heatmap_data_url", "gradcam_overlay_data_url"):
                self.assertTrue(result[key].startswith("data:image/png;base64,"))
                base64.b64decode(result[key].split(",", 1)[1], validate=True)
            results.append(result)

        self.assertEqual(len(chosen), 5)
        self.assertGreater(
            len({item["gradcam_heatmap_data_url"] for item in results}),
            1,
            "Different source images must not receive one shared heatmap.",
        )

    def test_invalid_image_bytes_are_rejected(self):
        from training.src.inference import UnsupportedImageError, generate_gradcam_image_bytes

        with self.assertRaises(UnsupportedImageError):
            generate_gradcam_image_bytes(b"not an image", self.bundle)


if __name__ == "__main__":
    unittest.main()
