#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_EMULATOR="$TASK_ROOT/emulator"
TASK_SOURCE="$TASK_EMULATOR/third_party/seabios"
TASK_BUILD="$TASK_EMULATOR/build/seabios"
TASK_COMMIT=a6ed6b701f0a57db0569ab98b0661c12a6ec3ff8
if [[ ! -d "$TASK_SOURCE/.git" ]]; then
    git clone --depth 1 --branch rel-1.16.3 https://github.com/coreboot/seabios.git "$TASK_SOURCE"
fi
if [[ "$(git -C "$TASK_SOURCE" rev-parse HEAD)" != "$TASK_COMMIT" ]]; then
    printf '%s\n' 'Unexpected SeaBIOS revision; refusing to build.' >&2
    exit 1
fi
if git -C "$TASK_SOURCE" apply --reverse --check "$TASK_EMULATOR/firmware/bochs-portrait.patch" 2>/dev/null; then
    : # The exact portrait patch is already applied.
else
    git -C "$TASK_SOURCE" apply --check "$TASK_EMULATOR/firmware/bochs-portrait.patch"
    git -C "$TASK_SOURCE" apply "$TASK_EMULATOR/firmware/bochs-portrait.patch"
fi
mkdir -p "$TASK_BUILD" "$TASK_EMULATOR/artifacts/firmware"
cp "$TASK_EMULATOR/firmware/bochs-portrait.config" "$TASK_SOURCE/.config"
make -C "$TASK_SOURCE" OUT="$TASK_BUILD/" PYTHON=python3 olddefconfig
make -C "$TASK_SOURCE" OUT="$TASK_BUILD/" PYTHON=python3 -j4 "$TASK_BUILD/vgabios.bin"
cp "$TASK_BUILD/vgabios.bin" "$TASK_EMULATOR/artifacts/firmware/vgabios-bochs-portrait.bin"
sha256sum "$TASK_EMULATOR/artifacts/firmware/vgabios-bochs-portrait.bin"
