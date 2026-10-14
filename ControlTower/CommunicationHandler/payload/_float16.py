"""Little-endian float16 encoding helper shared by the payload classes."""
import numpy as np


def encode_float16(value: float) -> bytes:
    """Encode a number as a little-endian IEEE 754 half-precision float.

    Args:
        value: Number to encode.

    Returns:
        Two bytes, least significant byte first.

    Raises:
        ValueError: If the value is not a finite number that fits in float16 (largest magnitude 65504).
    """
    try:
        with np.errstate(over="ignore"):
            encoded = np.float16(value)
    except (OverflowError, ValueError, TypeError) as error:
        raise ValueError(f"Float value {value!r} out of range for float16") from error

    if not np.isfinite(encoded):
        raise ValueError(f"Float value {value!r} out of range for float16")

    return encoded.astype('<f2').tobytes()
