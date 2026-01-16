"""
Object detection and scene classification Celery tasks.
"""

import logging

from celery import shared_task
from PIL import Image

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    queue="ml",
)
def detect_objects_task(self, asset_id: str, storage_path: str) -> dict:
    """
    Detect objects in an image.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the image file

    Returns:
        Dictionary with detected objects
    """
    from app.ml.object_detection import detect_objects
    from app.database import get_sync_session
    from app.models import Tag, AssetTag, TagType
    from sqlalchemy import select

    logger.info(f"Detecting objects in asset {asset_id}")

    try:
        with Image.open(storage_path) as img:
            objects = detect_objects(img, confidence_threshold=0.4)

        if not objects:
            logger.info(f"No objects detected in {asset_id}")
            return {"asset_id": asset_id, "objects": []}

        logger.info(f"Detected {len(objects)} objects in {asset_id}")

        with get_sync_session() as session:
            results = []

            for obj in objects:
                # Get or create tag
                tag = session.execute(
                    select(Tag).where(
                        Tag.name == obj.class_name,
                        Tag.tag_type == TagType.OBJECT,
                    )
                ).scalar_one_or_none()

                if not tag:
                    tag = Tag(
                        name=obj.class_name,
                        tag_type=TagType.OBJECT,
                    )
                    session.add(tag)
                    session.flush()

                # Create asset-tag association
                asset_tag = AssetTag(
                    asset_id=asset_id,
                    tag_id=tag.id,
                    confidence=obj.confidence,
                    bbox_x=obj.bbox_x,
                    bbox_y=obj.bbox_y,
                    bbox_width=obj.bbox_width,
                    bbox_height=obj.bbox_height,
                    source="yolov8",
                )
                session.add(asset_tag)

                # Update usage count
                tag.usage_count += 1

                results.append({
                    "class": obj.class_name,
                    "confidence": obj.confidence,
                })

            session.commit()

        return {
            "asset_id": asset_id,
            "objects": results,
        }

    except Exception as e:
        logger.error(f"Object detection failed for {asset_id}: {e}")
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    queue="ml",
)
def classify_scene_task(self, asset_id: str, storage_path: str) -> dict:
    """
    Classify the scene in an image.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the image file

    Returns:
        Dictionary with scene classifications
    """
    from app.ml.scene_classification import classify_scene
    from app.database import get_sync_session
    from app.models import Tag, AssetTag, TagType
    from sqlalchemy import select

    logger.info(f"Classifying scene in asset {asset_id}")

    try:
        with Image.open(storage_path) as img:
            scenes = classify_scene(img, top_k=3)

        if not scenes:
            logger.info(f"No scene classified for {asset_id}")
            return {"asset_id": asset_id, "scenes": []}

        logger.info(f"Top scene for {asset_id}: {scenes[0].scene_name}")

        with get_sync_session() as session:
            results = []

            for scene in scenes:
                # Only save high-confidence scenes
                if scene.confidence < 0.1:
                    continue

                # Get or create tag
                tag = session.execute(
                    select(Tag).where(
                        Tag.name == scene.scene_name,
                        Tag.tag_type == TagType.SCENE,
                    )
                ).scalar_one_or_none()

                if not tag:
                    tag = Tag(
                        name=scene.scene_name,
                        tag_type=TagType.SCENE,
                    )
                    session.add(tag)
                    session.flush()

                # Create asset-tag association
                asset_tag = AssetTag(
                    asset_id=asset_id,
                    tag_id=tag.id,
                    confidence=scene.confidence,
                    source="places365",
                )
                session.add(asset_tag)

                # Update usage count
                tag.usage_count += 1

                results.append({
                    "scene": scene.scene_name,
                    "confidence": scene.confidence,
                })

            session.commit()

        return {
            "asset_id": asset_id,
            "scenes": results,
        }

    except Exception as e:
        logger.error(f"Scene classification failed for {asset_id}: {e}")
        raise


@shared_task(queue="ml")
def process_ml_intelligence(asset_id: str, storage_path: str, owner_id: str) -> dict:
    """
    Run all ML intelligence tasks on an asset.

    Queues face detection, object detection, and scene classification.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the image file
        owner_id: UUID of the asset owner

    Returns:
        Task IDs for tracking
    """
    from celery import group

    from app.workers.tasks.face_processing import detect_and_encode_faces

    logger.info(f"Queueing ML intelligence for {asset_id}")

    # Run all tasks in parallel
    workflow = group(
        detect_and_encode_faces.s(asset_id, storage_path, owner_id),
        detect_objects_task.s(asset_id, storage_path),
        classify_scene_task.s(asset_id, storage_path),
    )

    result = workflow.apply_async()

    return {
        "asset_id": asset_id,
        "task_group_id": result.id,
    }
