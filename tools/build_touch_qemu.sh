#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_EMULATOR="$TASK_ROOT/emulator"
TASK_SOURCE="$TASK_EMULATOR/third_party/qemu"
TASK_BUILD="$TASK_EMULATOR/build/qemu"
TASK_COMMIT=44f28df24767cf9dca1ddc9b23157737c4cbb645
if [[ ! -d "$TASK_SOURCE/.git" ]]; then
    git clone --depth 1 --branch v6.2.0 https://github.com/qemu/qemu.git "$TASK_SOURCE"
fi
if [[ "$(git -C "$TASK_SOURCE" rev-parse HEAD)" != "$TASK_COMMIT" ]]; then
    printf '%s\n' 'Unexpected QEMU revision; refusing to build.' >&2
    exit 1
fi
if git -C "$TASK_SOURCE" apply --reverse --check "$TASK_EMULATOR/qemu-build/usb-touchscreen.patch" 2>/dev/null; then
    :
else
    git -C "$TASK_SOURCE" apply --check "$TASK_EMULATOR/qemu-build/usb-touchscreen.patch"
    git -C "$TASK_SOURCE" apply "$TASK_EMULATOR/qemu-build/usb-touchscreen.patch"
fi
mkdir -p "$TASK_BUILD" "$TASK_EMULATOR/artifacts/qemu"
(
    cd "$TASK_BUILD"
    "$TASK_SOURCE/configure" --target-list=x86_64-softmmu --enable-kvm --enable-gtk --enable-pa \
        --enable-slirp=git --disable-werror --disable-docs --disable-xen \
        --disable-capstone --disable-tools --meson="$(command -v meson)"
    ninja -j16 qemu-system-x86_64
)
cp "$TASK_BUILD/qemu-system-x86_64" "$TASK_EMULATOR/artifacts/qemu/qemu-system-x86_64"
cp "$TASK_SOURCE/COPYING" "$TASK_EMULATOR/artifacts/qemu/COPYING"
mkdir -p "$TASK_EMULATOR/artifacts/qemu/pc-bios"
for TASK_FILE in "$TASK_SOURCE"/pc-bios/*.bin "$TASK_SOURCE"/pc-bios/*.rom "$TASK_SOURCE"/pc-bios/*.efi; do
    [[ -f "$TASK_FILE" ]] || continue
    cp "$TASK_FILE" "$TASK_EMULATOR/artifacts/qemu/pc-bios/"
done
"$TASK_EMULATOR/artifacts/qemu/qemu-system-x86_64" -device usb-touchscreen,help
sha256sum "$TASK_EMULATOR/artifacts/qemu/qemu-system-x86_64"
