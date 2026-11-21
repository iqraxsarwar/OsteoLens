"""Inference contract for OsteoLens checkpoints produced by the Colab notebook.

This module does not contain model weights or predictions. It loads a trained
checkpoint and scores the image bytes supplied by a caller (for example, a
FastAPI upload endpoint).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import base64
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps, UnidentifiedImageError
from torchvision import models, transforms


SUPPORTED_CLASSES = ("Normal", "Benign", "Malignant")
SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG"}


class UnsupportedImageError(ValueError):
    """Raised when image bytes cannot be decoded as an accepted raster image."""


class InvalidCheckpointError(RuntimeError):
    """Raised when a checkpoint does not match the inference contract."""


@dataclass(frozen=True)
class ModelBundle:
    model: torch.nn.Module
    device: torch.device
    transform: transforms.Compose
    model_version: str
    class_names: tuple[str, ...]
    input_size: int


def _build_model(num_classes: int) -> torch.nn.Module:
    model = models.resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    return model


def load_model(checkpoint_path: str | Path, device: str | torch.device | None = None) -> ModelBundle:
    """Load a notebook checkpoint with PyTorch's restricted unpickler.

    The training notebook saved ``torch.__version__`` as PyTorch's
    ``TorchVersion`` string subclass. PyTorch 2.6+ does not allow that global
    by default when ``weights_only=True``. Allow only this metadata type for
    this call; do not fall back to unrestricted pickle loading.
    """
    requested_device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    try:
        from torch.torch_version import TorchVersion

        with torch.serialization.safe_globals([TorchVersion]):
            checkpoint: dict[str, Any] = torch.load(
                checkpoint_path, map_location=requested_device, weights_only=True
            )
    except Exception as exc:
        raise InvalidCheckpointError(f"Could not load model checkpoint: {exc}") from exc
    if not isinstance(checkpoint, dict):
        raise InvalidCheckpointError("Checkpoint root must be a metadata dictionary.")

    class_names = tuple(checkpoint.get("class_names", ()))
    if class_names != SUPPORTED_CLASSES:
        raise InvalidCheckpointError(
            f"Checkpoint classes must be {SUPPORTED_CLASSES}; got {class_names}."
        )
    if checkpoint.get("architecture") != "resnet18":
        raise InvalidCheckpointError("Checkpoint architecture must be resnet18.")
    input_size = checkpoint.get("input_size")
    if not isinstance(input_size, int) or input_size < 64:
        raise InvalidCheckpointError("Checkpoint input_size is missing or invalid.")
    preprocessing = checkpoint.get("preprocessing_config")
    expected_preprocessing = {
        "color_conversion": "RGB",
        "resize_method": "aspect_preserving_pad",
        "input_size": input_size,
        "interpolation": "Pillow.Resampling.LANCZOS",
        "padding_rgb": [0, 0, 0],
    }
    if not isinstance(preprocessing, dict) or any(
        preprocessing.get(key) != value for key, value in expected_preprocessing.items()
    ):
        raise InvalidCheckpointError("Checkpoint preprocessing configuration is missing or incompatible.")
    mean = preprocessing.get("normalization_mean")
    std = preprocessing.get("normalization_std")
    if not isinstance(mean, (list, tuple)) or not isinstance(std, (list, tuple)) or len(mean) != 3 or len(std) != 3:
        raise InvalidCheckpointError("Checkpoint normalization mean/std must contain three values each.")

    model = _build_model(len(class_names))
    try:
        model.load_state_dict(checkpoint["state_dict"], strict=True)
    except (KeyError, RuntimeError) as exc:
        raise InvalidCheckpointError(f"Checkpoint weights do not match the model: {exc}") from exc
    model.to(requested_device)
    model.eval()

    transform = transforms.Compose(
        [
            transforms.Lambda(
                lambda image: ImageOps.pad(
                    image,
                    (input_size, input_size),
                    method=Image.Resampling.LANCZOS,
                    color=tuple(preprocessing["padding_rgb"]),
                )
            ),
            transforms.ToTensor(),
            transforms.Normalize(mean=tuple(mean), std=tuple(std)),
        ]
    )
    return ModelBundle(
        model=model,
        device=requested_device,
        transform=transform,
        model_version=str(checkpoint.get("model_version", "unversioned")),
        class_names=class_names,
        input_size=input_size,
    )


def predict_image_bytes(image_bytes: bytes, bundle: ModelBundle) -> dict[str, Any]:
    """Run independent inference for one uploaded image and return raw scores.

    Scores are softmax probabilities, not calibrated clinical probabilities.
    The function intentionally does not emit a diagnosis or confidence warning
    threshold; downstream UI must describe this as research-only model output.
    """
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            if source.format not in SUPPORTED_IMAGE_FORMATS:
                raise UnsupportedImageError(
                    f"Unsupported image format: {source.format or 'unknown'}"
                )
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedImageError("Uploaded bytes are not a readable JPEG or PNG image.") from exc

    tensor = bundle.transform(image).unsqueeze(0).to(bundle.device)
    with torch.inference_mode():
        logits = bundle.model(tensor)
        if logits.ndim != 2 or logits.shape != (1, len(bundle.class_names)):
            raise RuntimeError("Model returned an unexpected output shape.")
        probabilities = torch.softmax(logits[0], dim=0).detach().cpu()

    if not torch.isfinite(probabilities).all():
        raise RuntimeError("Model returned non-finite scores.")
    predicted_index = int(torch.argmax(probabilities).item())
    return {
        "status": "complete",
        "prediction": bundle.class_names[predicted_index],
        "confidence": float(probabilities[predicted_index]),
        "confidence_kind": "maximum_uncalibrated_softmax_score",
        "probabilities": {
            name: float(probabilities[index]) for index, name in enumerate(bundle.class_names)
        },
        "model_version": bundle.model_version,
        "output_kind": "research_model_scores_not_clinical_diagnosis",
        "probabilities_calibrated": False,
    }


def _decode_image_bytes(image_bytes: bytes) -> Image.Image:
    """Decode an accepted image and return its EXIF-corrected RGB pixels."""
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            if source.format not in SUPPORTED_IMAGE_FORMATS:
                raise UnsupportedImageError(
                    f"Unsupported image format: {source.format or 'unknown'}"
                )
            return ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedImageError("Uploaded bytes are not a readable JPEG or PNG image.") from exc


def generate_gradcam_image_bytes(image_bytes: bytes, bundle: ModelBundle) -> dict[str, Any]:
    """Generate a genuine Grad-CAM for the predicted class of one input image.

    Returns image-specific heatmap and overlay PNG data URLs. The letterbox
    padding used by the trained model is removed before outputs are resized to
    the original EXIF-corrected image dimensions. Grad-CAM is a qualitative
    model-attention visualization, not a lesion boundary or diagnosis.
    """
    from matplotlib import colormaps

    image = _decode_image_bytes(image_bytes)
    model = bundle.model
    model.eval()
    target_layer = model.layer4[-1]
    captured: dict[str, torch.Tensor] = {}

    def capture_activation(_module, _inputs, output):
        output.retain_grad()
        captured["activation"] = output

    hook = target_layer.register_forward_hook(capture_activation)
    input_tensor = bundle.transform(image).unsqueeze(0).to(bundle.device)
    try:
        model.zero_grad(set_to_none=True)
        with torch.enable_grad():
            logits = model(input_tensor)
            if logits.ndim != 2 or logits.shape != (1, len(bundle.class_names)):
                raise RuntimeError("Model returned an unexpected output shape for Grad-CAM.")
            probabilities = torch.softmax(logits[0], dim=0).detach().cpu()
            predicted_index = int(torch.argmax(probabilities).item())
            logits[0, predicted_index].backward()
        activation = captured.get("activation")
        if activation is None or activation.grad is None:
            raise RuntimeError("Could not capture gradients for the ResNet-18 Grad-CAM layer.")
        gradients = activation.grad
        weights = gradients.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * activation).sum(dim=1, keepdim=True))
        cam = torch.nn.functional.interpolate(
            cam, size=(bundle.input_size, bundle.input_size), mode="bilinear", align_corners=False
        )[0, 0].detach().cpu().numpy()
    finally:
        hook.remove()
        model.zero_grad(set_to_none=True)

    low, high = float(cam.min()), float(cam.max())
    cam = (cam - low) / (high - low) if high > low else np.zeros_like(cam)
    cam_pixels = Image.fromarray(np.uint8(np.clip(cam * 255, 0, 255)), mode="L")

    # Find the exact non-padding area produced by the saved aspect-preserving pad.
    support = Image.new("L", image.size, color=255)
    padded_support = ImageOps.pad(
        support,
        (bundle.input_size, bundle.input_size),
        method=Image.Resampling.NEAREST,
        color=0,
    )
    content_box = padded_support.getbbox()
    if content_box is None:
        raise RuntimeError("Could not map Grad-CAM back through the saved image preprocessing.")
    cam_pixels = cam_pixels.crop(content_box).resize(image.size, Image.Resampling.BILINEAR)
    cam_values = np.asarray(cam_pixels, dtype=np.float32) / 255.0
    color_values = colormaps["inferno"](cam_values)[..., :3]
    heatmap = Image.fromarray(np.uint8(np.clip(color_values * 255, 0, 255)), mode="RGB")
    overlay = Image.blend(image, heatmap, alpha=0.42)

    def png_data_url(output: Image.Image) -> str:
        buffer = BytesIO()
        output.save(buffer, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    return {
        "prediction": bundle.class_names[predicted_index],
        "confidence": float(probabilities[predicted_index]),
        "confidence_kind": "maximum_uncalibrated_softmax_score",
        "probabilities": {
            name: float(probabilities[index]) for index, name in enumerate(bundle.class_names)
        },
        "model_version": bundle.model_version,
        "input_width": image.width,
        "input_height": image.height,
        "gradcam_heatmap_data_url": png_data_url(heatmap),
        "gradcam_overlay_data_url": png_data_url(overlay),
        "explanation": (
            "Grad-CAM highlights image regions that influenced this model prediction. "
            "It does not locate a confirmed tumour boundary or establish a diagnosis."
        ),
        "localization": {
            "status": "unavailable",
            "reason": "No validated annotation files or localization checkpoint are present in this workspace.",
        },
        "probabilities_calibrated": False,
        "output_kind": "research_model_scores_not_clinical_diagnosis",
    }
