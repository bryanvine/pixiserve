"""
ML module - Hardware accelerator detection and model loading.
"""

from app.ml.accelerator import (
    AcceleratorType,
    detect_accelerator,
    get_accelerator_info,
    get_onnx_providers,
)

__all__ = [
    "AcceleratorType",
    "detect_accelerator",
    "get_accelerator_info",
    "get_onnx_providers",
]
