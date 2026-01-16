"""
Face detection and recognition Celery tasks.
"""

import logging
from io import BytesIO
from pathlib import Path

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
def detect_and_encode_faces(self, asset_id: str, storage_path: str, owner_id: str) -> dict:
    """
    Detect faces in an image and generate embeddings.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the image file
        owner_id: UUID of the asset owner

    Returns:
        Dictionary with detected faces and embeddings
    """
    from app.ml.face_detection import detect_faces
    from app.ml.face_recognition import get_face_embeddings_batch, align_face
    from app.database import get_sync_session
    from app.models import Face
    from app.config import get_settings

    logger.info(f"Processing faces for asset {asset_id}")

    try:
        # Load image
        with Image.open(storage_path) as img:
            # Detect faces
            detected = detect_faces(img, confidence_threshold=0.7)

            if not detected:
                logger.info(f"No faces detected in {asset_id}")
                return {"asset_id": asset_id, "faces": []}

            logger.info(f"Detected {len(detected)} faces in {asset_id}")

            # Generate embeddings
            embeddings = get_face_embeddings_batch(img, detected)

            # Save face crops
            settings = get_settings()
            thumbnails_dir = Path(settings.storage_path).parent / "thumbnails" / "faces"
            thumbnails_dir.mkdir(parents=True, exist_ok=True)

            face_results = []

            with get_sync_session() as session:
                for i, (face, embedding) in enumerate(zip(detected, embeddings)):
                    # Save face crop
                    crop_path = None
                    try:
                        face_img = align_face(img, face, output_size=160)
                        crop_filename = f"{asset_id}_{i}.webp"
                        crop_path = thumbnails_dir / crop_filename
                        face_img.save(crop_path, "WEBP", quality=85)
                        crop_path = str(crop_path)
                    except Exception as e:
                        logger.warning(f"Failed to save face crop: {e}")

                    # Create Face record
                    face_record = Face(
                        asset_id=asset_id,
                        bbox_x=face.bbox_x,
                        bbox_y=face.bbox_y,
                        bbox_width=face.bbox_width,
                        bbox_height=face.bbox_height,
                        confidence=face.confidence,
                        embedding=embedding.tolist() if embedding is not None else None,
                        landmarks=[coord for point in (face.landmarks or []) for coord in point],
                        thumbnail_path=crop_path,
                    )
                    session.add(face_record)

                    face_results.append({
                        "face_id": str(face_record.id),
                        "confidence": face.confidence,
                        "has_embedding": embedding is not None,
                    })

                session.commit()

            logger.info(f"Saved {len(face_results)} faces for {asset_id}")

            # Queue clustering task
            cluster_faces.delay(owner_id)

            return {
                "asset_id": asset_id,
                "faces": face_results,
            }

    except Exception as e:
        logger.error(f"Face processing failed for {asset_id}: {e}")
        raise


@shared_task(queue="ml")
def cluster_faces(owner_id: str) -> dict:
    """
    Cluster faces for a user using DBSCAN.

    Args:
        owner_id: UUID of the user

    Returns:
        Clustering results
    """
    from app.database import get_sync_session
    from app.models import Face, Person
    from sqlalchemy import select
    import numpy as np

    logger.info(f"Clustering faces for user {owner_id}")

    try:
        with get_sync_session() as session:
            # Get all unassigned faces with embeddings
            faces = session.execute(
                select(Face)
                .join(Face.asset)
                .where(Face.person_id.is_(None))
                .where(Face.embedding.isnot(None))
            ).scalars().all()

            if len(faces) < 2:
                logger.info("Not enough faces for clustering")
                return {"clustered": 0}

            # Extract embeddings
            embeddings = np.array([f.embedding for f in faces])
            face_ids = [f.id for f in faces]

            # Simple clustering using cosine similarity
            # For production, use DBSCAN or HDBSCAN
            from sklearn.cluster import DBSCAN

            # Cosine distance = 1 - cosine similarity
            clustering = DBSCAN(
                eps=0.5,  # Distance threshold
                min_samples=2,
                metric="cosine",
            ).fit(embeddings)

            labels = clustering.labels_

            # Group faces by cluster
            clusters: dict[int, list] = {}
            for face_id, label in zip(face_ids, labels):
                if label == -1:  # Noise
                    continue
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(face_id)

            # Create or update Person records
            created_people = 0
            for cluster_id, cluster_face_ids in clusters.items():
                # Check if any face in cluster already has a person
                existing_person = None
                for fid in cluster_face_ids:
                    face = session.get(Face, fid)
                    if face and face.person_id:
                        existing_person = session.get(Person, face.person_id)
                        break

                if not existing_person:
                    # Create new person
                    existing_person = Person(
                        owner_id=owner_id,
                        face_count=len(cluster_face_ids),
                    )
                    session.add(existing_person)
                    session.flush()
                    created_people += 1

                # Assign faces to person
                for fid in cluster_face_ids:
                    face = session.get(Face, fid)
                    if face:
                        face.person_id = existing_person.id

                # Update face count
                existing_person.face_count = len(cluster_face_ids)

                # Set cover face if not set
                if not existing_person.cover_face_id and cluster_face_ids:
                    existing_person.cover_face_id = cluster_face_ids[0]

            session.commit()

            logger.info(f"Clustered {len(faces)} faces into {len(clusters)} groups, created {created_people} people")

            return {
                "total_faces": len(faces),
                "clusters": len(clusters),
                "created_people": created_people,
            }

    except ImportError:
        logger.warning("sklearn not available, skipping clustering")
        return {"error": "sklearn not installed"}
    except Exception as e:
        logger.error(f"Face clustering failed: {e}")
        raise


@shared_task(queue="ml")
def merge_people(person_id_keep: str, person_id_merge: str) -> dict:
    """
    Merge two people into one.

    Args:
        person_id_keep: UUID of person to keep
        person_id_merge: UUID of person to merge into keep

    Returns:
        Merge results
    """
    from app.database import get_sync_session
    from app.models import Face, Person

    logger.info(f"Merging person {person_id_merge} into {person_id_keep}")

    try:
        with get_sync_session() as session:
            person_keep = session.get(Person, person_id_keep)
            person_merge = session.get(Person, person_id_merge)

            if not person_keep or not person_merge:
                return {"error": "Person not found"}

            # Move all faces to kept person
            for face in person_merge.faces:
                face.person_id = person_keep.id

            # Update face count
            person_keep.face_count += person_merge.face_count

            # Mark merged person
            person_merge.merged_into_id = person_keep.id
            person_merge.face_count = 0

            session.commit()

            return {
                "kept": person_id_keep,
                "merged": person_id_merge,
                "new_face_count": person_keep.face_count,
            }

    except Exception as e:
        logger.error(f"Person merge failed: {e}")
        raise
