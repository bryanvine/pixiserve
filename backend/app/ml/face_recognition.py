"""
Face recognition using ArcFace ONNX model.

Generates 512-dimensional embeddings for face matching.
"""

import logging
from io import BytesIO

import numpy as np
from PIL import Image

from app.ml.models import get_model_session
from app.ml.face_detection import DetectedFace

logger = logging.getLogger(__name__)

# ArcFace input size
ARCFACE_INPUT_SIZE = 112


def align_face(
    image: Image.Image,
    face: DetectedFace,
    output_size: int = ARCFACE_INPUT_SIZE,
) -> Image.Image:
    """
    Crop and align face from image.

    Args:
        image: Original PIL Image
        face: Detected face with bounding box
        output_size: Size of output image

    Returns:
        Cropped and aligned face image
    """
    width, height = image.size

    # Convert normalized bbox to pixels
    x1 = int(face.bbox_x * width)
    y1 = int(face.bbox_y * height)
    x2 = int((face.bbox_x + face.bbox_width) * width)
    y2 = int((face.bbox_y + face.bbox_height) * height)

    # Add margin (20% on each side)
    margin_x = int((x2 - x1) * 0.2)
    margin_y = int((y2 - y1) * 0.2)

    x1 = max(0, x1 - margin_x)
    y1 = max(0, y1 - margin_y)
    x2 = min(width, x2 + margin_x)
    y2 = min(height, y2 + margin_y)

    # Crop face
    face_img = image.crop((x1, y1, x2, y2))

    # Resize to model input size
    face_img = face_img.resize((output_size, output_size), Image.Resampling.LANCZOS)

    return face_img


def preprocess_face(face_img: Image.Image) -> np.ndarray:
    """
    Preprocess face image for ArcFace model.

    Args:
        face_img: Cropped face image (112x112)

    Returns:
        Preprocessed numpy array
    """
    # Convert to RGB
    if face_img.mode != "RGB":
        face_img = face_img.convert("RGB")

    # Convert to numpy
    img_array = np.array(face_img, dtype=np.float32)

    # Normalize to [-1, 1]
    img_array = (img_array - 127.5) / 127.5

    # Transpose to CHW and add batch dimension
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)

    return img_array


def get_face_embedding(
    image: Image.Image,
    face: DetectedFace,
) -> np.ndarray | None:
    """
    Generate embedding for a detected face.

    Args:
        image: Original PIL Image
        face: Detected face

    Returns:
        512-dimensional embedding vector, or None on error
    """
    try:
        session = get_model_session("arcface")
    except Exception as e:
        logger.error(f"Failed to load ArcFace model: {e}")
        return None

    try:
        # Align and preprocess face
        face_img = align_face(image, face)
        input_data = preprocess_face(face_img)

        # Run inference
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_data})

        # Get embedding and normalize
        embedding = outputs[0][0]
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    except Exception as e:
        logger.error(f"Face embedding generation failed: {e}")
        return None


def get_face_embeddings_batch(
    image: Image.Image,
    faces: list[DetectedFace],
    batch_size: int = 8,
) -> list[np.ndarray | None]:
    """
    Generate embeddings for multiple faces.

    Args:
        image: Original PIL Image
        faces: List of detected faces
        batch_size: Batch size for inference

    Returns:
        List of embeddings (None for failed faces)
    """
    if not faces:
        return []

    try:
        session = get_model_session("arcface")
    except Exception as e:
        logger.error(f"Failed to load ArcFace model: {e}")
        return [None] * len(faces)

    embeddings = []

    # Process in batches
    for i in range(0, len(faces), batch_size):
        batch_faces = faces[i:i + batch_size]
        batch_inputs = []

        for face in batch_faces:
            try:
                face_img = align_face(image, face)
                input_data = preprocess_face(face_img)
                batch_inputs.append(input_data[0])  # Remove batch dimension
            except Exception as e:
                logger.warning(f"Failed to preprocess face: {e}")
                batch_inputs.append(None)

        # Filter valid inputs
        valid_indices = [j for j, inp in enumerate(batch_inputs) if inp is not None]
        if not valid_indices:
            embeddings.extend([None] * len(batch_faces))
            continue

        valid_inputs = np.stack([batch_inputs[j] for j in valid_indices])

        try:
            input_name = session.get_inputs()[0].name
            outputs = session.run(None, {input_name: valid_inputs})

            batch_embeddings = outputs[0]

            # Normalize embeddings
            batch_embeddings = batch_embeddings / np.linalg.norm(
                batch_embeddings, axis=1, keepdims=True
            )

            # Reconstruct results with None for invalid faces
            result_idx = 0
            for j in range(len(batch_faces)):
                if j in valid_indices:
                    embeddings.append(batch_embeddings[result_idx])
                    result_idx += 1
                else:
                    embeddings.append(None)

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            embeddings.extend([None] * len(batch_faces))

    return embeddings


def compare_faces(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate similarity between two face embeddings.

    Args:
        embedding1: First embedding
        embedding2: Second embedding

    Returns:
        Cosine similarity score (0-1, higher = more similar)
    """
    # Cosine similarity
    similarity = np.dot(embedding1, embedding2)

    # Convert from [-1, 1] to [0, 1]
    return (similarity + 1) / 2


def find_matching_faces(
    query_embedding: np.ndarray,
    embeddings: list[np.ndarray],
    threshold: float = 0.6,
) -> list[tuple[int, float]]:
    """
    Find faces matching a query embedding.

    Args:
        query_embedding: Query face embedding
        embeddings: List of embeddings to search
        threshold: Minimum similarity threshold

    Returns:
        List of (index, similarity) tuples for matches
    """
    matches = []

    for i, embedding in enumerate(embeddings):
        if embedding is None:
            continue

        similarity = compare_faces(query_embedding, embedding)
        if similarity >= threshold:
            matches.append((i, similarity))

    # Sort by similarity (descending)
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches
