"""Thin ctypes wrapper around the pylibpag native encoder."""

import ctypes
import math
from collections.abc import Buffer, Iterable
from pathlib import Path


class PAGEncodeError(RuntimeError):
    """Raised when libpag cannot encode a PAG file."""


class _ByteSpan(ctypes.Structure):
    _fields_ = [("data", ctypes.c_void_p), ("size", ctypes.c_size_t)]


def _load_library() -> ctypes.CDLL:
    library_path = Path(__file__).with_name("_native.so")
    try:
        return ctypes.CDLL(str(library_path))
    except OSError as error:
        raise ImportError(
            f"Unable to load pylibpag native library: {library_path}"
        ) from error


_LIBRARY = _load_library()
_ENCODE = _LIBRARY.pylibpag_encode_webp_frames
_ENCODE.argtypes = [
    ctypes.POINTER(_ByteSpan),
    ctypes.c_size_t,
    ctypes.c_int32,
    ctypes.c_int32,
    ctypes.c_float,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_int64,
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(ctypes.c_size_t),
]
_ENCODE.restype = ctypes.c_int
_LAST_ERROR = _LIBRARY.pylibpag_last_error
_LAST_ERROR.argtypes = []
_LAST_ERROR.restype = ctypes.c_char_p
_FREE = _LIBRARY.pylibpag_free
_FREE.argtypes = [ctypes.c_void_p]
_FREE.restype = None


def _as_nonempty_bytes(value: Buffer, name: str) -> bytes:
    try:
        data = value if isinstance(value, bytes) else memoryview(value).tobytes()
    except TypeError as error:
        raise TypeError(f"{name} must support the buffer protocol") from error

    if not data:
        raise ValueError(f"{name} must not be empty")
    return data


def _positive_int32(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if not 0 < value <= 2_147_483_647:
        raise ValueError(f"{name} must be between 1 and 2147483647")
    return value


def _int64(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if not -(2 ** 63) <= value < 2 ** 63:
        raise ValueError(f"{name} must fit in a signed 64-bit integer")
    return value


def encode_webp_frames(
    frames: Iterable[Buffer],
    *,
    width: int,
    height: int,
    frame_rate: float = 30.0,
    audio: Buffer | None = None,
    audio_start_frame: int = 0,
) -> bytes:
    """Encode WebP frames into a PAG file with optional embedded AAC-in-MP4 audio.

    Args:
        frames: Ordered encoded WebP frame buffers.
        width: Composition width in pixels.
        height: Composition height in pixels.
        frame_rate: Frames per second.
        audio: Optional AAC audio in an MPEG-4 container, normally M4A bytes.
        audio_start_frame: Frame on which audio playback begins.

    Returns:
        Encoded PAG file bytes.

    Raises:
        PAGEncodeError: libpag rejected or failed to encode the composition.
        TypeError: An argument has the wrong type.
        ValueError: An argument is empty or outside its valid range.
    """
    if isinstance(frames, Buffer):
        raise TypeError("frames must be an iterable of buffers, not one buffer")

    frame_data = [
        _as_nonempty_bytes(frame, f"frames[{index}]")
        for index, frame in enumerate(frames)
    ]
    if not frame_data:
        raise ValueError("frames must contain at least one WebP frame")

    width = _positive_int32(width, "width")
    height = _positive_int32(height, "height")
    if isinstance(frame_rate, bool):
        raise TypeError("frame_rate must be a real number")
    try:
        frame_rate = float(frame_rate)
    except (TypeError, ValueError) as error:
        raise TypeError("frame_rate must be a real number") from error
    if not math.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError("frame_rate must be finite and positive")
    audio_start_frame = _int64(audio_start_frame, "audio_start_frame")

    frame_pointers = [ctypes.c_char_p(frame) for frame in frame_data]
    span_array_type = _ByteSpan * len(frame_data)
    frame_spans = span_array_type(
        *(
            _ByteSpan(ctypes.cast(pointer, ctypes.c_void_p), len(frame))
            for pointer, frame in zip(frame_pointers, frame_data, strict=True)
        )
    )

    audio_data = _as_nonempty_bytes(audio, "audio") if audio is not None else None
    audio_pointer = ctypes.c_char_p(audio_data) if audio_data is not None else None
    output_pointer = ctypes.c_void_p()
    output_size = ctypes.c_size_t()

    status = _ENCODE(
        frame_spans,
        len(frame_data),
        width,
        height,
        frame_rate,
        ctypes.cast(audio_pointer, ctypes.c_void_p)
        if audio_pointer is not None
        else None,
        len(audio_data) if audio_data is not None else 0,
        audio_start_frame,
        ctypes.byref(output_pointer),
        ctypes.byref(output_size),
    )
    if status != 0:
        error_bytes = _LAST_ERROR()
        message = (
            error_bytes.decode("utf-8", errors="replace")
            if error_bytes
            else f"Native status {status}"
        )
        raise PAGEncodeError(message)

    try:
        return ctypes.string_at(output_pointer, output_size.value)
    finally:
        _FREE(output_pointer)
