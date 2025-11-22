import numpy as np
import struct

def decode_command_payload(payload_bytes: bytes):
    """
    Decodes a payload consisting of two unsigned bytes:
    - drone_id: int
    - command_value: int

    Args:
        payload_bytes (bytes): The binary payload to decode.

    Returns:
        drone_id, command_value
    """
    if len(payload_bytes) != 2:
        raise ValueError("Payload must be exactly 2 bytes long.")

    drone_id, command_value = struct.unpack('BB', payload_bytes)
    return drone_id, command_value

def decode_point_payload(payload_bytes: bytes):
    """
    Decodes a 9-byte drone PointPayload:
    - drone_id: 1 byte
    - command: 1 byte
    - x, y, z: each 2 bytes (float16)

    Args:
        payload_bytes (bytes): The binary payload to decode.

    Args:
        payload_bytes (bytes): The binary payload to decode.

    Returns:
        dict: Decoded values with keys: drone_id, command, x, y, z, R, G, B
    """
    if len(payload_bytes) != 8:
        raise ValueError(f"Payload must be exactly 8 long. Got: {len(payload_bytes)}")

    # Unpack the payload
    drone_id, command, x_bytes, y_bytes, z_bytes = struct.unpack('BB2s2s2s', payload_bytes)

    # Convert bytes to float16
    x = np.frombuffer(x_bytes, dtype=np.float16)[0]
    y = np.frombuffer(y_bytes, dtype=np.float16)[0]
    z = np.frombuffer(z_bytes, dtype=np.float16)[0]

    return {
        'drone_id': drone_id,
        'command': command,
        'x': round(float(x), 1),
        'y': round(float(y), 1),
        'z': round(float(z), 1),
    }

def decode_cpoint_payload(payload_bytes: bytes):
    """
    Decodes a 12-byte drone CPointPayload:
    - drone_id: 1 byte
    - command: 1 byte
    - x, y, z: each 2 bytes (float16)
    - R, G, B: each 1 byte

    Args:
        payload_bytes (bytes): The binary payload to decode.

    Args:
        payload_bytes (bytes): The binary payload to decode.

    Returns:
        dict: Decoded values with keys: drone_id, command, x, y, z, R, G, B
    """
    if len(payload_bytes) != 11:
        raise ValueError(f"Payload must be exactly 8 long. Got: {len(payload_bytes)}")

    # Unpack the payload
    drone_id, command, x_bytes, y_bytes, z_bytes, R, G, B = struct.unpack('BB2s2s2sBBB', payload_bytes)

    # Convert bytes to float16
    x = np.frombuffer(x_bytes, dtype=np.float16)[0]
    y = np.frombuffer(y_bytes, dtype=np.float16)[0]
    z = np.frombuffer(z_bytes, dtype=np.float16)[0]

    return {
        'drone_id': drone_id,
        'command': command,
        'x': round(float(x), 1),
        'y': round(float(y), 1),
        'z': round(float(z), 1),
        'r': R,
        'g': G,
        'b': B
    }


