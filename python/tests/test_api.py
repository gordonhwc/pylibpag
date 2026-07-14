from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase

import pylibpag

# 2x2 lossless WebP with alpha
WEBP_FRAME_WIDTH = 2
WEBP_FRAME_HEIGHT = 2
WEBP_FRAME = bytes.fromhex(
    """
52 49 46 46 30 00 00 00 57 45 42 50 56 50 38 4c
23 00 00 00 2f 01 40 00 10 1f 30 ff fb 2f 20 28
f2 7f 34 81 00 21 8d ff 28 21 f8 45 42 49 80 00
28 ca 48 44 ff 63 00 00
    """
)


class EncodeWebPFramesTest(TestCase):
    def test_encodes_pag_bytes(self) -> None:
        result = pylibpag.encode_webp_frames(
            [WEBP_FRAME],
            width=WEBP_FRAME_WIDTH,
            height=WEBP_FRAME_HEIGHT,
        )

        self.assertTrue(result.startswith(b"PAG"))

    def test_embeds_audio_bytes(self) -> None:
        audio = b"pylibpag-audio-payload"

        result = pylibpag.encode_webp_frames(
            [WEBP_FRAME, WEBP_FRAME],
            width=WEBP_FRAME_WIDTH,
            height=WEBP_FRAME_HEIGHT,
            audio=audio,
            audio_start_frame=1,
        )

        self.assertIn(audio, result)

    def test_parallel_calls_are_deterministic(self) -> None:
        def encode(_: int) -> bytes:
            return pylibpag.encode_webp_frames(
                [WEBP_FRAME] * 4,
                width=WEBP_FRAME_WIDTH,
                height=WEBP_FRAME_HEIGHT,
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(encode, range(64)))

        self.assertTrue(all(result == results[0] for result in results))

    def test_rejects_empty_frames(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            pylibpag.encode_webp_frames(
                [],
                width=WEBP_FRAME_WIDTH,
                height=WEBP_FRAME_HEIGHT,
            )

    def test_rejects_one_buffer_as_frame_collection(self) -> None:
        with self.assertRaisesRegex(TypeError, "iterable of buffers"):
            pylibpag.encode_webp_frames(
                WEBP_FRAME,  # type: ignore[arg-type]
                width=WEBP_FRAME_WIDTH,
                height=WEBP_FRAME_HEIGHT,
            )
