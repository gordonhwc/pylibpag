"""Build and test the Linux amd64 wheel in a disposable manylinux container."""

import os
import shutil
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DIST_DIRECTORY = REPOSITORY_ROOT / "dist"
DOCKER_IMAGE = "quay.io/pypa/manylinux_2_28_x86_64:latest"

CONTAINER_SCRIPT = r"""
set -euo pipefail

cp --archive /src/. /work/
dnf module install --assumeyes nodejs:24/common
npm install --global depsync@1.4.6

cd /work
depsync

PYTHON=/opt/python/cp314-cp314t/bin/python
"${PYTHON}" -m pip install \
    --disable-pip-version-check \
    --root-user-action ignore \
    --upgrade \
    build==1.5.1 \
    auditwheel==6.7.0
"${PYTHON}" -m build --wheel --outdir /tmp/wheelhouse
"${PYTHON}" -m auditwheel repair \
    --plat manylinux_2_28_x86_64 \
    --wheel-dir /tmp/repaired \
    /tmp/wheelhouse/*.whl

WHEEL=$(find /tmp/repaired -maxdepth 1 -name '*.whl' -print -quit)
test -n "${WHEEL}"

test_wheel() {
    local python="$1"
    local environment="$2"

    "${python}" -m venv "${environment}"
    "${environment}/bin/python" -m pip install \
        --disable-pip-version-check \
        --no-deps \
        "${WHEEL}"
    "${environment}/bin/python" -m unittest discover \
        --start-directory /work/python/tests \
        --verbose
}

test_wheel /opt/python/cp314-cp314/bin/python /tmp/test-cp314
test_wheel /opt/python/cp314-cp314t/bin/python /tmp/test-cp314t
/tmp/test-cp314t/bin/python -c \
    'import sysconfig; assert sysconfig.get_config_var("Py_GIL_DISABLED") == 1'

cp "${WHEEL}" /dist/
chown "${HOST_UID}:${HOST_GID}" "/dist/$(basename "${WHEEL}")"
""".strip()


def main() -> None:
    """Build the wheel and write it to the dist directory."""
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required to build the wheel")

    DIST_DIRECTORY.mkdir(exist_ok=True)
    command = [
        "docker",
        "run",
        "--rm",
        "--pull",
        "always",
        "--platform",
        "linux/amd64",
        "--volume",
        f"{REPOSITORY_ROOT}:/src:ro",
        "--volume",
        f"{DIST_DIRECTORY}:/dist",
        "--env",
        f"HOST_UID={os.getuid()}",
        "--env",
        f"HOST_GID={os.getgid()}",
        "--workdir",
        "/work",
        DOCKER_IMAGE,
        "bash",
        "-c",
        CONTAINER_SCRIPT,
    ]

    print(f"Building pylibpag wheel with {DOCKER_IMAGE}", flush=True)
    subprocess.run(command, check=True)

    wheels = sorted(
        DIST_DIRECTORY.glob("pylibpag-*.whl"), key=lambda path: path.stat().st_mtime
    )
    if not wheels:
        raise FileNotFoundError(f"No wheel was created in {DIST_DIRECTORY}")
    print(f"Done: built and tested {wheels[-1]}")


if __name__ == "__main__":
    main()
