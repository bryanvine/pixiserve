"""
ONNX Model management for ML inference.

Downloads and caches models from Hugging Face or direct URLs.
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

import onnxruntime as ort

from app.ml.accelerator import get_onnx_providers

logger = logging.getLogger(__name__)

# Default model cache directory
MODEL_CACHE_DIR = Path(os.environ.get("MODEL_CACHE_DIR", "/app/models"))

# Model configurations
MODELS = {
    # Face detection - RetinaFace (lighter version)
    "retinaface": {
        "url": "https://huggingface.co/onnx-community/retinaface/resolve/main/retinaface_mnet025_v2.onnx",
        "filename": "retinaface_mnet025_v2.onnx",
        "sha256": None,  # Will be verified if provided
    },
    # Face recognition - ArcFace (MobileFaceNet variant)
    "arcface": {
        "url": "https://huggingface.co/onnx-community/arcface/resolve/main/arcface_mobilefacenet.onnx",
        "filename": "arcface_mobilefacenet.onnx",
        "sha256": None,
    },
    # Object detection - YOLOv8n (nano - fastest)
    "yolov8n": {
        "url": "https://huggingface.co/onnx-community/yolov8n/resolve/main/yolov8n.onnx",
        "filename": "yolov8n.onnx",
        "sha256": None,
    },
    # Scene classification - Places365 MobileNetV2
    "places365": {
        "url": "https://huggingface.co/onnx-community/places365/resolve/main/places365_mobilenetv2.onnx",
        "filename": "places365_mobilenetv2.onnx",
        "sha256": None,
    },
}

# COCO class names for YOLOv8
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
    "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
]

# Cached model sessions
_model_sessions: dict[str, ort.InferenceSession] = {}


def _verify_checksum(filepath: Path, expected_sha256: str | None) -> bool:
    """Verify file checksum."""
    if not expected_sha256:
        return True

    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest() == expected_sha256


def download_model(model_name: str, force: bool = False) -> Path:
    """
    Download model if not cached.

    Args:
        model_name: Name of the model (key in MODELS dict)
        force: Force re-download even if cached

    Returns:
        Path to the downloaded model file
    """
    if model_name not in MODELS:
        raise ValueError(f"Unknown model: {model_name}")

    config = MODELS[model_name]
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_CACHE_DIR / config["filename"]

    if model_path.exists() and not force:
        if _verify_checksum(model_path, config.get("sha256")):
            logger.debug(f"Using cached model: {model_path}")
            return model_path
        else:
            logger.warning(f"Checksum mismatch, re-downloading: {model_name}")

    logger.info(f"Downloading model: {model_name} from {config['url']}")

    try:
        urlretrieve(config["url"], model_path)
        logger.info(f"Downloaded model to: {model_path}")

        if not _verify_checksum(model_path, config.get("sha256")):
            raise ValueError(f"Checksum verification failed for {model_name}")

        return model_path
    except Exception as e:
        logger.error(f"Failed to download model {model_name}: {e}")
        if model_path.exists():
            model_path.unlink()
        raise


def get_model_session(model_name: str) -> ort.InferenceSession:
    """
    Get or create ONNX Runtime session for a model.

    Args:
        model_name: Name of the model

    Returns:
        ONNX Runtime InferenceSession
    """
    if model_name in _model_sessions:
        return _model_sessions[model_name]

    model_path = download_model(model_name)
    providers = get_onnx_providers()

    logger.info(f"Loading model {model_name} with providers: {providers}")

    session = ort.InferenceSession(
        str(model_path),
        providers=providers,
    )

    _model_sessions[model_name] = session
    return session


def clear_model_cache():
    """Clear all cached model sessions."""
    global _model_sessions
    _model_sessions = {}
    logger.info("Cleared model session cache")
