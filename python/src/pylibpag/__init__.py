"""Encode WebP frame sequences as PAG files."""

from ._api import PAGEncodeError, encode_webp_frames

__all__ = ["PAGEncodeError", "encode_webp_frames"]
