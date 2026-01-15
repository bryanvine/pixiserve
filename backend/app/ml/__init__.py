"""
ML module - Hardware accelerator detection and model loading.
"""

from app.ml.accelerator import AcceleratorType, detect_accelerator, get_accelerator_info

__all__ = ["AcceleratorType", "detect_accelerator", "get_accelerator_info"]
