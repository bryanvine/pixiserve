"""
Face detection using RetinaFace ONNX model.

Detects faces and facial landmarks in images.
"""

import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image

from app.ml.models import get_model_session

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """A detected face with bounding box and landmarks."""
    bbox_x: float  # Normalized 0-1
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: float
    landmarks: list[tuple[float, float]] | None = None  # 5 points: eyes, nose, mouth corners


def preprocess_image(image: Image.Image, target_size: int = 640) -> tuple[np.ndarray, float]:
    """
    Preprocess image for RetinaFace model.

    Args:
        image: PIL Image
        target_size: Target size for the longer edge

    Returns:
        Tuple of (preprocessed array, scale factor)
    """
    # Convert to RGB if needed
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Calculate scale to fit target size
    width, height = image.size
    scale = target_size / max(width, height)
    new_width = int(width * scale)
    new_height = int(height * scale)

    # Resize
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Convert to numpy and normalize
    img_array = np.array(image, dtype=np.float32)

    # Normalize to [-1, 1] (RetinaFace expects this)
    img_array = (img_array - 127.5) / 128.0

    # Pad to target size
    padded = np.zeros((target_size, target_size, 3), dtype=np.float32)
    padded[:new_height, :new_width, :] = img_array

    # Add batch dimension and transpose to NCHW
    padded = np.transpose(padded, (2, 0, 1))
    padded = np.expand_dims(padded, axis=0)

    return padded, scale


def detect_faces(
    image: Image.Image,
    confidence_threshold: float = 0.5,
    nms_threshold: float = 0.4,
) -> list[DetectedFace]:
    """
    Detect faces in an image.

    Args:
        image: PIL Image
        confidence_threshold: Minimum confidence for detection
        nms_threshold: Non-maximum suppression threshold

    Returns:
        List of detected faces
    """
    try:
        session = get_model_session("retinaface")
    except Exception as e:
        logger.error(f"Failed to load RetinaFace model: {e}")
        return []

    original_width, original_height = image.size

    # Preprocess
    input_data, scale = preprocess_image(image)

    # Run inference
    try:
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_data})
    except Exception as e:
        logger.error(f"Face detection inference failed: {e}")
        return []

    # Parse outputs (format depends on model variant)
    # RetinaFace typically outputs: bboxes, scores, landmarks
    faces = []

    try:
        # Simple output parsing - adjust based on actual model output
        if len(outputs) >= 2:
            bboxes = outputs[0]  # [N, 4] or [N, 5] with score
            scores = outputs[1] if len(outputs) > 1 else bboxes[:, 4]
            landmarks = outputs[2] if len(outputs) > 2 else None

            for i in range(len(bboxes)):
                score = float(scores[i]) if isinstance(scores[i], (int, float)) else float(scores[i][0])

                if score < confidence_threshold:
                    continue

                bbox = bboxes[i]

                # Convert from pixel coordinates to normalized
                x1 = float(bbox[0]) / scale / original_width
                y1 = float(bbox[1]) / scale / original_height
                x2 = float(bbox[2]) / scale / original_width
                y2 = float(bbox[3]) / scale / original_height

                # Clamp to valid range
                x1 = max(0, min(1, x1))
                y1 = max(0, min(1, y1))
                x2 = max(0, min(1, x2))
                y2 = max(0, min(1, y2))

                face = DetectedFace(
                    bbox_x=x1,
                    bbox_y=y1,
                    bbox_width=x2 - x1,
                    bbox_height=y2 - y1,
                    confidence=score,
                )

                # Parse landmarks if available
                if landmarks is not None and i < len(landmarks):
                    lm = landmarks[i]
                    face.landmarks = [
                        (float(lm[j]) / scale / original_width,
                         float(lm[j + 1]) / scale / original_height)
                        for j in range(0, 10, 2)
                    ]

                faces.append(face)

    except Exception as e:
        logger.error(f"Failed to parse face detection output: {e}")

    # Apply NMS if multiple faces
    if len(faces) > 1:
        faces = _apply_nms(faces, nms_threshold)

    logger.debug(f"Detected {len(faces)} faces")
    return faces


def _apply_nms(faces: list[DetectedFace], threshold: float) -> list[DetectedFace]:
    """Apply non-maximum suppression to remove overlapping detections."""
    if not faces:
        return faces

    # Sort by confidence
    faces = sorted(faces, key=lambda f: f.confidence, reverse=True)

    keep = []
    for face in faces:
        # Check overlap with kept faces
        should_keep = True
        for kept in keep:
            iou = _calculate_iou(face, kept)
            if iou > threshold:
                should_keep = False
                break

        if should_keep:
            keep.append(face)

    return keep


def _calculate_iou(face1: DetectedFace, face2: DetectedFace) -> float:
    """Calculate intersection over union between two faces."""
    x1 = max(face1.bbox_x, face2.bbox_x)
    y1 = max(face1.bbox_y, face2.bbox_y)
    x2 = min(face1.bbox_x + face1.bbox_width, face2.bbox_x + face2.bbox_width)
    y2 = min(face1.bbox_y + face1.bbox_height, face2.bbox_y + face2.bbox_height)

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = face1.bbox_width * face1.bbox_height
    area2 = face2.bbox_width * face2.bbox_height
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0
