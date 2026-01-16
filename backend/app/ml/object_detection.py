"""
Object detection using YOLOv8 ONNX model.

Detects common objects (COCO classes) in images.
"""

import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image

from app.ml.models import get_model_session, COCO_CLASSES

logger = logging.getLogger(__name__)

# YOLOv8 input size
YOLO_INPUT_SIZE = 640


@dataclass
class DetectedObject:
    """A detected object with bounding box."""
    class_name: str
    class_id: int
    bbox_x: float  # Normalized 0-1
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: float


def preprocess_image(image: Image.Image, target_size: int = YOLO_INPUT_SIZE) -> tuple[np.ndarray, tuple[float, float], tuple[int, int]]:
    """
    Preprocess image for YOLOv8 model.

    Args:
        image: PIL Image
        target_size: Target size (square)

    Returns:
        Tuple of (preprocessed array, scale factors, padding)
    """
    # Convert to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    original_width, original_height = image.size

    # Calculate scale to fit in target_size while maintaining aspect ratio
    scale = min(target_size / original_width, target_size / original_height)
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)

    # Resize
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Create padded image (letterbox)
    padded = Image.new("RGB", (target_size, target_size), (114, 114, 114))
    pad_x = (target_size - new_width) // 2
    pad_y = (target_size - new_height) // 2
    padded.paste(resized, (pad_x, pad_y))

    # Convert to numpy and normalize
    img_array = np.array(padded, dtype=np.float32) / 255.0

    # Transpose to CHW and add batch dimension
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)

    return img_array, (scale, scale), (pad_x, pad_y)


def postprocess_detections(
    outputs: np.ndarray,
    original_size: tuple[int, int],
    scale: tuple[float, float],
    padding: tuple[int, int],
    confidence_threshold: float = 0.25,
    nms_threshold: float = 0.45,
) -> list[DetectedObject]:
    """
    Postprocess YOLOv8 outputs.

    Args:
        outputs: Model output
        original_size: Original image (width, height)
        scale: Scale factors used during preprocessing
        padding: Padding used during preprocessing
        confidence_threshold: Minimum confidence
        nms_threshold: NMS threshold

    Returns:
        List of detected objects
    """
    original_width, original_height = original_size
    pad_x, pad_y = padding

    # YOLOv8 output shape: [1, 84, 8400] (84 = 4 bbox + 80 classes)
    # Transpose to [8400, 84]
    predictions = outputs[0].T

    objects = []

    for pred in predictions:
        # Extract bbox and class scores
        bbox = pred[:4]  # cx, cy, w, h
        class_scores = pred[4:]

        # Get best class
        class_id = int(np.argmax(class_scores))
        confidence = float(class_scores[class_id])

        if confidence < confidence_threshold:
            continue

        # Convert from center format to corner format
        cx, cy, w, h = bbox
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

        # Remove padding and scale back to original image
        x1 = (x1 - pad_x) / scale[0]
        y1 = (y1 - pad_y) / scale[1]
        x2 = (x2 - pad_x) / scale[0]
        y2 = (y2 - pad_y) / scale[1]

        # Normalize to 0-1
        x1 = max(0, min(1, x1 / original_width))
        y1 = max(0, min(1, y1 / original_height))
        x2 = max(0, min(1, x2 / original_width))
        y2 = max(0, min(1, y2 / original_height))

        # Get class name
        class_name = COCO_CLASSES[class_id] if class_id < len(COCO_CLASSES) else f"class_{class_id}"

        objects.append(DetectedObject(
            class_name=class_name,
            class_id=class_id,
            bbox_x=x1,
            bbox_y=y1,
            bbox_width=x2 - x1,
            bbox_height=y2 - y1,
            confidence=confidence,
        ))

    # Apply NMS
    objects = _apply_nms(objects, nms_threshold)

    return objects


def _apply_nms(objects: list[DetectedObject], threshold: float) -> list[DetectedObject]:
    """Apply class-aware non-maximum suppression."""
    if not objects:
        return objects

    # Group by class
    by_class: dict[int, list[DetectedObject]] = {}
    for obj in objects:
        if obj.class_id not in by_class:
            by_class[obj.class_id] = []
        by_class[obj.class_id].append(obj)

    # Apply NMS per class
    result = []
    for class_objects in by_class.values():
        # Sort by confidence
        class_objects.sort(key=lambda x: x.confidence, reverse=True)

        keep = []
        for obj in class_objects:
            should_keep = True
            for kept in keep:
                iou = _calculate_iou(obj, kept)
                if iou > threshold:
                    should_keep = False
                    break
            if should_keep:
                keep.append(obj)

        result.extend(keep)

    return result


def _calculate_iou(obj1: DetectedObject, obj2: DetectedObject) -> float:
    """Calculate intersection over union."""
    x1 = max(obj1.bbox_x, obj2.bbox_x)
    y1 = max(obj1.bbox_y, obj2.bbox_y)
    x2 = min(obj1.bbox_x + obj1.bbox_width, obj2.bbox_x + obj2.bbox_width)
    y2 = min(obj1.bbox_y + obj1.bbox_height, obj2.bbox_y + obj2.bbox_height)

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = obj1.bbox_width * obj1.bbox_height
    area2 = obj2.bbox_width * obj2.bbox_height
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def detect_objects(
    image: Image.Image,
    confidence_threshold: float = 0.25,
    nms_threshold: float = 0.45,
) -> list[DetectedObject]:
    """
    Detect objects in an image.

    Args:
        image: PIL Image
        confidence_threshold: Minimum confidence
        nms_threshold: NMS threshold

    Returns:
        List of detected objects
    """
    try:
        session = get_model_session("yolov8n")
    except Exception as e:
        logger.error(f"Failed to load YOLOv8 model: {e}")
        return []

    original_size = image.size

    # Preprocess
    input_data, scale, padding = preprocess_image(image)

    # Run inference
    try:
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_data})
    except Exception as e:
        logger.error(f"Object detection inference failed: {e}")
        return []

    # Postprocess
    objects = postprocess_detections(
        outputs[0],
        original_size,
        scale,
        padding,
        confidence_threshold,
        nms_threshold,
    )

    logger.debug(f"Detected {len(objects)} objects")
    return objects
