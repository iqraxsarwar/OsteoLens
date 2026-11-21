import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TrainingPackageTests(unittest.TestCase):
    def test_notebook_is_valid_json_and_has_no_saved_fake_outputs(self):
        notebook = json.loads((ROOT / "osteolens_colab.ipynb").read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        self.assertGreaterEqual(len(notebook["cells"]), 12)
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])

    def test_notebook_python_cells_parse(self):
        notebook = json.loads((ROOT / "osteolens_colab.ipynb").read_text(encoding="utf-8"))
        for number, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            python_lines = [line for line in source.splitlines() if not line.startswith(("%", "!"))]
            ast.parse("\n".join(python_lines), filename=f"notebook-cell-{number}")

    def test_metadata_visual_review_notebook_is_valid_and_parses(self):
        notebook = json.loads((ROOT / "btxrd_metadata_visual_review_colab.ipynb").read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        self.assertIn("MyDrive/OsteoLensRuns/BTXRD/BTXRD.zip", "".join(notebook["cells"][2]["source"]))
        for number, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            self.assertIsNone(cell["execution_count"])
            self.assertEqual(cell["outputs"], [])
            source = "".join(cell["source"])
            python_lines = [line for line in source.splitlines() if not line.startswith(("%", "!"))]
            ast.parse("\n".join(python_lines), filename=f"review-notebook-cell-{number}")

    def test_inference_module_parses_without_requiring_torch_import(self):
        source = (ROOT / "src" / "inference.py").read_text(encoding="utf-8")
        ast.parse(source, filename="training/src/inference.py")
        self.assertIn("def load_model(", source)
        self.assertIn("def predict_image_bytes(", source)
        self.assertIn('"probabilities_calibrated": False', source)
        self.assertIn('"confidence_kind": "maximum_uncalibrated_softmax_score"', source)

    def test_checkpoint_loader_uses_scoped_torchversion_allowlist(self):
        source = (ROOT / "src" / "inference.py").read_text(encoding="utf-8")
        self.assertIn("from torch.torch_version import TorchVersion", source)
        self.assertIn("torch.serialization.safe_globals([TorchVersion])", source)
        self.assertIn("weights_only=True", source)
        self.assertNotIn("weights_only=False", source)

    def test_package_does_not_include_a_trained_checkpoint(self):
        self.assertFalse(any(ROOT.rglob("*.pth")))
        self.assertFalse(any(ROOT.rglob("*.pt")))


if __name__ == "__main__":
    unittest.main()
