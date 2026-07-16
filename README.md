<p align="center"><a href="https://github.com/Tencent/libpag"><img src="https://media.githubusercontent.com/media/Tencent/libpag/main/resources/readme/logo.png" alt="PAG logo" width="420"></a></p>

# pylibpag

[![CPython](https://img.shields.io/badge/CPython-3.14%20%7C%203.14t-3776AB?logo=python&logoColor=white)](pyproject.toml) [![Linux](https://img.shields.io/badge/Linux-amd64-FCC624?logo=linux&logoColor=black)](#building-the-wheel) [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE.txt)

Lightweight unofficial Python bindings for [Tencent libpag](https://github.com/Tencent/libpag), focused on encoding WebP
frame sequences and embedding audio into PAG files.

This repository is a source fork of the official libpag project. The Python layer is kept in the separate `python/`
directory so upstream libpag updates can be rebased without modifying its existing source files.

> This is an unofficial project and is not affiliated with or endorsed by Tencent.

## Features

- Encode one or more already-encoded WebP frames into a bitmap PAG animation
- Preserve WebP alpha data for transparent animations
- Optionally embed AAC audio stored in an MPEG-4 container, normally M4A bytes
- Run independent encode calls concurrently from Python threads without a global conversion lock
- Use one native wheel on both regular CPython 3.14 and free-threaded CPython 3.14t
- Avoid a CPython extension ABI by exposing a small C interface through `ctypes.CDLL`

The initial wheel target is Linux amd64 using the `manylinux_2_28_x86_64` platform tag.

## Installation

After a release is published:

```bash
python -m pip install pylibpag
```

To install a locally built wheel:

```bash
python -m pip install dist/pylibpag-*.whl
```

Python 3.14 or newer is required.

## Usage

```python
from pathlib import Path

import pylibpag

frames = [
    Path("frame-001.webp").read_bytes(),
    Path("frame-002.webp").read_bytes(),
]

pag_bytes = pylibpag.encode_webp_frames(
    frames,
    width=512,
    height=512,
    frame_rate=30.0,
)
Path("animation.pag").write_bytes(pag_bytes)
```

### Transparent frames

Pass WebP frames that already contain alpha. `pylibpag` stores the encoded frame bytes in a PAG bitmap sequence; it does
not decode, resize, or otherwise convert the source images.

### Audio

libpag expects composition audio to be AAC in an MPEG-4 container. An M4A file can be passed directly as bytes:

```python
pag_bytes = pylibpag.encode_webp_frames(
    frames,
    width=512,
    height=512,
    frame_rate=30.0,
    audio=Path("audio.m4a").read_bytes(),
    audio_start_frame=0,
)
```

The native layer embeds audio bytes without transcoding or validating the codec. Convert MP3, WAV, PCM, raw AAC, or
other inputs to AAC-in-MP4 in your Python media pipeline first. Embedded audio does not automatically extend the visual
frame duration.

### Threading

Independent calls can run concurrently:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=8) as executor:
    pag_files = list(
        executor.map(
            lambda frame_group: pylibpag.encode_webp_frames(
                frame_group,
                width=512,
                height=512,
            ),
            frame_groups,
        )
    )
```

Each call creates its own libpag composition, frame objects, input copies, error state, and output buffer. Do not share
or mutate an input buffer while a call is using it.

## API

```python
pylibpag.encode_webp_frames(
    frames,
    *,
    width,
    height,
    frame_rate=30.0,
    audio=None,
    audio_start_frame=0,
) -> bytes
```

- `frames`: ordered iterable of encoded WebP buffers
- `width` and `height`: positive composition dimensions
- `frame_rate`: finite positive frames per second
- `audio`: optional AAC-in-MP4/M4A buffer
- `audio_start_frame`: signed frame offset for the first audio frame

Native encode failures raise `pylibpag.PAGEncodeError`.

## Building the wheel

Docker is the only local build requirement:

```bash
python3 scripts/build_wheel.py
```

The script:

1. Starts the official PyPA manylinux amd64 image with `docker run --rm`
2. Mounts this repository read-only and copies it into the temporary container
3. Synchronizes the exact libpag dependencies declared by `DEPS`
4. Builds a modern PEP 517 wheel with scikit-build-core
5. Repairs the platform tag and bundled libraries with auditwheel
6. Installs and tests the same wheel using regular CPython 3.14 and free-threaded CPython 3.14t
7. Writes the final wheel to `dist/`

All dependency and compiler files remain inside the disposable container. Only the wheel in `dist/` is retained.

## Scope

`pylibpag` deliberately does not provide media conversion or PAG playback. Convert PNG, video, APNG, or other source
formats to WebP frames in Python, then pass those bytes to this package. This keeps the compiled binding small and the
upstream integration easy to maintain.

## Development

For upstream libpag SDK development and platform build instructions, see the
official [libpag development guide](https://github.com/Tencent/libpag#development). Python wheel development is
described in [Building the wheel](#building-the-wheel).

## License

Licensed under the [Apache License 2.0](LICENSE.txt). libpag is developed by Tencent. This unofficial Python package
preserves the upstream license and attribution.
