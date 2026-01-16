"""
Scene classification using Places365 model.

Classifies images into 365 scene categories.
"""

import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image

from app.ml.models import get_model_session

logger = logging.getLogger(__name__)

# Places365 input size
PLACES_INPUT_SIZE = 224

# Top scene categories (subset of 365)
# Full list: https://github.com/CSAILVision/places365/blob/master/categories_places365.txt
SCENE_CATEGORIES = [
    "airfield", "airplane_cabin", "airport_terminal", "alcove", "alley",
    "amphitheater", "amusement_arcade", "amusement_park", "apartment_building/outdoor",
    "aquarium", "aqueduct", "arcade", "arch", "archaelogical_excavation",
    "archive", "arena/hockey", "arena/performance", "arena/rodeo", "army_base",
    "art_gallery", "art_school", "art_studio", "artists_loft", "assembly_line",
    "athletic_field/outdoor", "atrium/public", "attic", "auditorium", "auto_factory",
    "auto_showroom", "badlands", "bakery/shop", "balcony/exterior", "balcony/interior",
    "ball_pit", "ballroom", "bamboo_forest", "bank_vault", "banquet_hall",
    "bar", "barn", "barndoor", "baseball_field", "basement",
    "basketball_court/indoor", "bathroom", "bazaar/indoor", "bazaar/outdoor", "beach",
    "beach_house", "beauty_salon", "bedroom", "berth", "biology_laboratory",
    "boardwalk", "boat_deck", "boathouse", "bookstore", "booth/indoor",
    "botanical_garden", "bow_window/indoor", "bowling_alley", "boxing_ring", "bridge",
    "building_facade", "bullring", "burial_chamber", "bus_interior", "bus_station/indoor",
    "butchers_shop", "butte", "cabin/outdoor", "cafeteria", "campsite",
    "campus", "canal/natural", "canal/urban", "candy_store", "canyon",
    "car_interior", "carrousel", "casino/indoor", "castle", "catacomb",
    "cemetery", "chalet", "chemistry_lab", "childs_room", "church/indoor",
    "church/outdoor", "classroom", "clean_room", "cliff", "closet",
    "clothing_store", "coast", "cockpit", "coffee_shop", "computer_room",
    "conference_center", "conference_room", "construction_site", "corn_field", "corral",
    "corridor", "cottage", "courthouse", "courtyard", "creek",
    "crevasse", "crosswalk", "dam", "delicatessen", "department_store",
    "desert/sand", "desert/vegetation", "desert_road", "diner/outdoor", "dining_hall",
    "dining_room", "discotheque", "doorway/outdoor", "dorm_room", "downtown",
    "dressing_room", "driveway", "drugstore", "elevator/door", "elevator_lobby",
    "elevator_shaft", "embassy", "engine_room", "entrance_hall", "escalator/indoor",
    "excavation", "fabric_store", "farm", "fastfood_restaurant", "field/cultivated",
    "field/wild", "field_road", "fire_escape", "fire_station", "fishpond",
    "flea_market/indoor", "florist_shop/indoor", "food_court", "football_field",
    "forest/broadleaf", "forest_path", "forest_road", "formal_garden", "fountain",
    "galley", "garage/indoor", "garage/outdoor", "gas_station", "gazebo/exterior",
    "general_store/indoor", "general_store/outdoor", "gift_shop", "glacier", "golf_course",
    "greenhouse/indoor", "greenhouse/outdoor", "grotto", "gymnasium/indoor", "hangar/indoor",
    "harbor", "hardware_store", "hayfield", "heliport", "highway",
    "hill", "home_office", "home_theater", "hospital", "hospital_room",
    "hot_spring", "hotel/outdoor", "hotel_room", "house", "hunting_lodge/outdoor",
    "ice_cream_parlor", "ice_floe", "ice_shelf", "ice_skating_rink/indoor",
    "ice_skating_rink/outdoor", "iceberg", "igloo", "industrial_area", "inn/outdoor",
    "islet", "jacuzzi/indoor", "jail_cell", "japanese_garden", "jewelry_shop",
    "junkyard", "kasbah", "kennel/outdoor", "kindergarden_classroom", "kitchen",
    "lagoon", "lake/natural", "landfill", "landing_deck", "laundromat",
    "lawn", "lecture_room", "legislative_chamber", "library/indoor", "library/outdoor",
    "lighthouse", "living_room", "loading_dock", "lobby", "lock_chamber",
    "locker_room", "mansion", "manufactured_home", "market/indoor", "market/outdoor",
    "marsh", "martial_arts_gym", "mausoleum", "medina", "moat/water",
    "mosque/outdoor", "motel", "mountain", "mountain_path", "mountain_snowy",
    "movie_theater/indoor", "museum/indoor", "museum/outdoor", "music_studio", "natural_history_museum",
    "nursery", "nursing_home", "oast_house", "ocean", "office",
    "office_building", "office_cubicles", "oilrig", "operating_room", "orchard",
    "orchestra_pit", "pagoda", "palace", "pantry", "park",
    "parking_garage/indoor", "parking_garage/outdoor", "parking_lot", "pasture", "patio",
    "pavilion", "pet_shop", "pharmacy", "phone_booth", "physics_laboratory",
    "picnic_area", "pier", "pizzeria", "playground", "playroom",
    "plaza", "pond", "porch", "promenade", "pub/indoor",
    "racecourse", "raceway", "raft", "railroad_track", "rainforest",
    "reception", "recreation_room", "repair_shop", "residential_neighborhood", "restaurant",
    "restaurant_kitchen", "restaurant_patio", "rice_paddy", "river", "rock_arch",
    "roof_garden", "rope_bridge", "ruin", "runway", "sandbox",
    "sauna", "schoolhouse", "science_museum", "server_room", "shed",
    "shoe_shop", "shopfront", "shopping_mall/indoor", "shower", "ski_resort",
    "ski_slope", "sky", "skyscraper", "slum", "snowfield",
    "soccer_field", "stable", "stadium/baseball", "stadium/football", "stadium/soccer",
    "stage/indoor", "stage/outdoor", "staircase", "storage_room", "street",
    "subway_station/platform", "supermarket", "sushi_bar", "swamp", "swimming_hole",
    "swimming_pool/indoor", "swimming_pool/outdoor", "synagogue/outdoor", "television_room",
    "television_studio", "temple/asia", "throne_room", "ticket_booth", "topiary_garden",
    "tower", "toyshop", "track/outdoor", "train_interior", "train_station/platform",
    "tree_farm", "tree_house", "trench", "tundra", "underwater/ocean_deep",
    "utility_room", "valley", "vegetable_garden", "veterinarians_office", "viaduct",
    "village", "vineyard", "volcano", "volleyball_court/outdoor", "waiting_room",
    "water_park", "water_tower", "waterfall", "watering_hole", "wave",
    "wet_bar", "wheat_field", "wind_farm", "windmill", "yard", "youth_hostel", "zen_garden",
]


@dataclass
class SceneClassification:
    """A scene classification result."""
    scene_name: str
    confidence: float


def preprocess_image(image: Image.Image) -> np.ndarray:
    """
    Preprocess image for Places365 model.

    Args:
        image: PIL Image

    Returns:
        Preprocessed numpy array
    """
    # Convert to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Resize to 256 then center crop to 224
    image = image.resize((256, 256), Image.Resampling.LANCZOS)

    # Center crop
    left = (256 - PLACES_INPUT_SIZE) // 2
    top = (256 - PLACES_INPUT_SIZE) // 2
    image = image.crop((left, top, left + PLACES_INPUT_SIZE, top + PLACES_INPUT_SIZE))

    # Convert to numpy
    img_array = np.array(image, dtype=np.float32)

    # Normalize with ImageNet mean/std
    mean = np.array([0.485, 0.456, 0.406]) * 255
    std = np.array([0.229, 0.224, 0.225]) * 255
    img_array = (img_array - mean) / std

    # Transpose to CHW and add batch dimension
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0).astype(np.float32)

    return img_array


def classify_scene(
    image: Image.Image,
    top_k: int = 5,
) -> list[SceneClassification]:
    """
    Classify the scene in an image.

    Args:
        image: PIL Image
        top_k: Number of top predictions to return

    Returns:
        List of scene classifications with confidence scores
    """
    try:
        session = get_model_session("places365")
    except Exception as e:
        logger.error(f"Failed to load Places365 model: {e}")
        return []

    # Preprocess
    input_data = preprocess_image(image)

    # Run inference
    try:
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_data})
    except Exception as e:
        logger.error(f"Scene classification inference failed: {e}")
        return []

    # Get predictions
    logits = outputs[0][0]

    # Apply softmax
    exp_logits = np.exp(logits - np.max(logits))
    probabilities = exp_logits / np.sum(exp_logits)

    # Get top-k
    top_indices = np.argsort(probabilities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        scene_name = SCENE_CATEGORIES[idx] if idx < len(SCENE_CATEGORIES) else f"scene_{idx}"
        confidence = float(probabilities[idx])

        results.append(SceneClassification(
            scene_name=scene_name,
            confidence=confidence,
        ))

    logger.debug(f"Top scene: {results[0].scene_name} ({results[0].confidence:.2f})")
    return results
