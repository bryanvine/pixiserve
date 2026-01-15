"""
Hardware accelerator detection for ML inference.

Supports:
- NVIDIA CUDA (via onnxruntime-gpu or direct CUDA)
- AMD ROCm (via onnxruntime-rocm)
- Google Coral TPU (via pycoral/tflite)
- CPU fallback (always available)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

logger = logging.getLogger(__name__)


class AcceleratorType(str, Enum):
    """Supported hardware accelerators."""
    CUDA = "cuda"
    ROCM = "rocm"
    CORAL = "coral"
    CPU = "cpu"


@dataclass
class AcceleratorInfo:
    """Information about detected accelerator."""
    type: AcceleratorType
    name: str
    available: bool
    device_count: int = 1
    memory_mb: int | None = None
    details: dict | None = None


def _detect_cuda() -> AcceleratorInfo | None:
    """Detect NVIDIA CUDA GPUs."""
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()

        if "CUDAExecutionProvider" in providers:
            # Try to get GPU info
            device_count = 1
            memory_mb = None
            gpu_name = "NVIDIA GPU"

            try:
                # Try using pynvml for detailed info
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(gpu_name, bytes):
                        gpu_name = gpu_name.decode()
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    memory_mb = mem_info.total // (1024 * 1024)
                pynvml.nvmlShutdown()
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"Could not get detailed CUDA info: {e}")

            return AcceleratorInfo(
                type=AcceleratorType.CUDA,
                name=gpu_name,
                available=True,
                device_count=device_count,
                memory_mb=memory_mb,
            )
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"CUDA detection error: {e}")

    return None


def _detect_rocm() -> AcceleratorInfo | None:
    """Detect AMD ROCm GPUs."""
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()

        if "ROCMExecutionProvider" in providers:
            return AcceleratorInfo(
                type=AcceleratorType.ROCM,
                name="AMD GPU (ROCm)",
                available=True,
            )
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"ROCm detection error: {e}")

    return None


def _detect_coral() -> AcceleratorInfo | None:
    """Detect Google Coral TPU."""
    try:
        # Check for Coral Edge TPU
        from pycoral.utils.edgetpu import list_edge_tpus

        tpus = list_edge_tpus()
        if tpus:
            return AcceleratorInfo(
                type=AcceleratorType.CORAL,
                name="Google Coral Edge TPU",
                available=True,
                device_count=len(tpus),
                details={"devices": tpus},
            )
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Coral detection error: {e}")

    return None


@lru_cache(maxsize=1)
def detect_accelerator() -> AcceleratorInfo:
    """
    Detect the best available hardware accelerator.

    Priority: CUDA > ROCm > Coral > CPU

    Returns:
        AcceleratorInfo for the best available accelerator.
    """
    # Check CUDA first (most common for ML)
    cuda = _detect_cuda()
    if cuda:
        logger.info(f"Detected CUDA accelerator: {cuda.name}")
        return cuda

    # Check ROCm (AMD GPUs)
    rocm = _detect_rocm()
    if rocm:
        logger.info(f"Detected ROCm accelerator: {rocm.name}")
        return rocm

    # Check Coral TPU
    coral = _detect_coral()
    if coral:
        logger.info(f"Detected Coral TPU: {coral.device_count} device(s)")
        return coral

    # Fallback to CPU
    logger.info("No GPU/TPU detected, using CPU for inference")
    return AcceleratorInfo(
        type=AcceleratorType.CPU,
        name="CPU",
        available=True,
    )


def get_accelerator_info() -> dict:
    """Get accelerator info as a dictionary for API responses."""
    info = detect_accelerator()
    return {
        "type": info.type.value,
        "name": info.name,
        "available": info.available,
        "device_count": info.device_count,
        "memory_mb": info.memory_mb,
    }


def get_onnx_providers() -> list[str]:
    """
    Get ONNX Runtime execution providers in priority order.

    Returns:
        List of provider names for onnxruntime.InferenceSession.
    """
    accelerator = detect_accelerator()

    if accelerator.type == AcceleratorType.CUDA:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif accelerator.type == AcceleratorType.ROCM:
        return ["ROCMExecutionProvider", "CPUExecutionProvider"]
    else:
        return ["CPUExecutionProvider"]
