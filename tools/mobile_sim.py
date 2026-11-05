#!/usr/bin/env python3
"""Prepare and probe a Windows 10 Mobile SDK guest with system QEMU.

The SDK image is an experimental guest, not an emulated Lumia board.
Python standard library only; QEMU, curl and cabextract are external tools.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import tempfile
from phone_input import PHONE_KEYS, send_button

ROOT = Path(__file__).resolve().parents[1]
EMULATOR = ROOT / "emulator"
SDK = EMULATOR / "artifacts/sdk-14393"
RUNTIME = EMULATOR / "runtime"
MANIFEST = EMULATOR / "manifests/sdk-14393.json"
PROFILE = EMULATOR / "profiles/lumia-1520.json"


def manifest():
    return json.loads(MANIFEST.read_text())


def binary(name):
    found = shutil.which(name)
    if not found:
        raise ValueError(f"Required executable is missing: {name}")
    return found


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def doctor(_):
    candidate = EMULATOR / "artifacts/qemu/qemu-system-x86_64"
    qemu = str(candidate) if candidate.is_file() else binary("qemu-system-x86_64")
    print(json.dumps({
        "host": platform.platform(),
        "qemu": subprocess.check_output([qemu, "--version"], text=True).splitlines()[0],
        "tools": {n: shutil.which(n) for n in ("qemu-img", "curl", "cabextract", "xdotool", "xrandr")},
        "kvm_accessible": os.access("/dev/kvm", os.R_OK | os.W_OK),
        "profile": json.loads(PROFILE.read_text()),
        "note": "QEMU availability does not establish Windows Mobile guest compatibility."
    }, indent=2, ensure_ascii=False))


def download(_):
    """Download missing payloads, then verify against the bootstrapper manifest."""
    m = manifest()
    for p in m["payloads"]:
        dest = SDK / p["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if (dest.exists() and dest.stat().st_size == p["size"]
                and digest(dest, "sha1") == p["sha1_from_bootstrapper"]):
            print(f"Verified cache: {dest.name}", flush=True)
            continue
        part = dest.with_suffix(dest.suffix + ".part")
        print(f"Downloading {dest.name} ({p['size']} bytes)", flush=True)
        subprocess.run([binary("curl"), "--fail", "--location", "--silent",
                        "--show-error", "--retry", "2", "--connect-timeout", "15",
                        "--max-time", "600", p["url"], "--output", str(part)], check=True)
        if part.stat().st_size != p["size"] or digest(part, "sha1") != p["sha1_from_bootstrapper"]:
            raise ValueError(f"SDK payload verification failed: {part}")
        part.replace(dest)
    verify(None)


def verify(_):
    receipts = []
    for p in manifest()["payloads"]:
        f = SDK / p["path"]
        if not f.is_file() or f.stat().st_size != p["size"]:
            raise ValueError(f"Missing or incomplete SDK payload: {f}. Run download-sdk.")
        if digest(f, "sha1") != p["sha1_from_bootstrapper"]:
            raise ValueError(f"SDK bootstrapper hash mismatch: {f}")
        receipts.append({"path": p["path"], "size": f.stat().st_size, "sha256": digest(f)})
    save(SDK / "verified.json", {"payloads": receipts,
         "note": "SHA-1 and sizes checked against Microsoft's SDK bootstrapper; SHA-256 values are local receipts."})
    print(f"Verified all {len(receipts)} SDK payloads.", flush=True)


def prepare(_):
    verify(None)
    image = SDK / "flash.vhd"
    expected = manifest()["assembled_image"]
    if image.exists():
        if image.stat().st_size == expected["size"] and digest(image) == expected["sha256"]:
            print(f"Verified assembled SDK VHD: {image}")
            return
        raise ValueError(f"Image already exists with unexpected content: {image}")
    parts_dir = SDK / "fragments"
    parts_dir.mkdir(exist_ok=True)
    # Vhd27..Vhd50 are empty, signed placeholders. Vhd1..Vhd26 hold the data.
    for i in range(1, 27):
        print(f"Extracting Vhd{i}.cab", flush=True)
        subprocess.run([binary("cabextract"), "-q", "-d", str(parts_dir),
                        str(SDK / f"Redistributable/1.0.0.0/Vhd{i}.cab")], check=True)
    fragments = manifest()["image_fragments"]
    if [f["sequence"] for f in fragments] != list(range(1, 27)):
        raise ValueError("Unexpected fragment order in the manifest")
    part = image.with_suffix(".vhd.part")
    with part.open("xb") as out:
        for f in fragments:
            with (parts_dir / f["file"]).open("rb") as stream:
                shutil.copyfileobj(stream, out, 4 * 1024 * 1024)
    if part.stat().st_size != expected["size"] or digest(part) != expected["sha256"]:
        raise ValueError(f"Assembled VHD size or SHA-256 mismatch: {part}")
    info = json.loads(subprocess.check_output([binary("qemu-img"), "info", "-f", "vpc",
                                              "--output=json", str(part)], text=True))
    if info["virtual-size"] != expected["virtual_size"]:
        raise ValueError("Unexpected SDK virtual disk size")
    part.replace(image)
    info["filename"] = str(image)
    save(SDK / "image.json", {"sha256": digest(image), "qemu_img_info": info})
    print(f"Assembled SDK VHD: {image}", flush=True)


def import_image(args):
    src = args.image.resolve()
    if src.suffix.lower() == ".ffu":
        raise ValueError("A Lumia ARM FFU cannot be used as an x86 SDK guest.")
    base = RUNTIME / "base.qcow2"
    overlay = RUNTIME / "disk.qcow2"
    if base.exists() or overlay.exists():
        raise ValueError(f"Guest disk already exists in {RUNTIME}; refusing to overwrite it.")
    tool = binary("qemu-img")
    info = json.loads(subprocess.check_output([tool, "info", "--output=json", "-f", "vpc", str(src)], text=True))
    RUNTIME.mkdir(exist_ok=True)
    tmp = RUNTIME / "base.qcow2.part"
    if tmp.exists():
        raise ValueError(f"Incomplete earlier import exists: {tmp}")
    subprocess.run([tool, "convert", "-p", "-f", "vpc", "-O", "qcow2", str(src), str(tmp)], check=True)
    subprocess.run([tool, "check", "-f", "qcow2", str(tmp)], check=True)
    tmp.replace(base)
    subprocess.run([tool, "create", "-f", "qcow2", "-F", "qcow2", "-b", base.name, str(overlay)], check=True)
    save(RUNTIME / "import.json", {"source": str(src), "source_sha256": digest(src), "source_info": info})
    print(f"Prepared base and writable overlay: {overlay}")


def accel(value):
    if value == "auto":
        if platform.system() == "Linux" and os.access("/dev/kvm", os.R_OK | os.W_OK):
            return "kvm"
        return "tcg"
    if value == "kvm" and not os.access("/dev/kvm", os.R_OK | os.W_OK):
        raise ValueError("KVM is not accessible on this host. Use --accel tcg.")
    return value


def command(args):
    selected = accel(args.accel)
    cpu = args.cpu or ("host" if selected == "kvm" else "max")
    disk = RUNTIME / "disk.qcow2"
    if not disk.is_file():
        raise ValueError("Guest disk is missing. Run import-image first.")
    vga = "VGA,xres=1080,yres=1920" if args.portrait else "VGA"
    rom_arg = args.vga_rom
    if args.portrait and rom_arg is None:
        rom_arg = EMULATOR / "artifacts/firmware/vgabios-bochs-portrait.bin"
    if rom_arg:
        rom = rom_arg.resolve()
        if not rom.is_file():
            raise ValueError(f"VGA ROM is missing: {rom}. Run bash tools/build_portrait_firmware.sh")
        vga += ",romfile=" + str(rom).replace(",", ",,")
    local_qemu = EMULATOR / "artifacts/qemu/qemu-system-x86_64"
    qemu = args.qemu.resolve() if args.qemu else (local_qemu if local_qemu.is_file() else Path(binary("qemu-system-x86_64")))
    pointer = args.pointer
    if pointer == "auto":
        pointer = "touch" if qemu == local_qemu else "mouse"
    cmd = [str(qemu), "-name", "Windows 10 Mobile SDK (Lumia 1520 reference)",
           "-machine", args.machine, "-accel", selected, "-cpu", cpu,
           "-m", "2048", "-smp", str(args.smp), "-no-reboot",
           "-drive", "if=ide,format=qcow2,file=" + str(disk).replace(",", ",,"),
           "-vga", "none", "-device", vga,
           "-usb", "-device", ("usb-touchscreen" if pointer == "touch" else "usb-tablet"),
           "-device", "usb-kbd", "-monitor", "none",
           "-qmp", f"tcp:127.0.0.1:{args.qmp_port},server=on,wait=off",
           "-serial", "file:" + str(RUNTIME / "serial.log"), "-parallel", "none"]
    if (qemu.parent / "pc-bios").is_dir():
        cmd += ["-L", str(qemu.parent / "pc-bios")]
    if args.nic == "none":
        cmd += ["-nic", "none"]
    else:
        cmd += ["-device", f"{args.nic},netdev=n0",
                "-netdev", ("user,id=n0,hostfwd=tcp:127.0.0.1:5080-:80,"
                            "hostfwd=tcp:127.0.0.1:5443-:443")]
        if args.trace_network:
            cmd += ["-object", "filter-dump,id=nettrace,netdev=n0,file=" + str(RUNTIME / "network.pcap").replace(",", ",,")]
    selected_audio = args.audio
    if selected_audio == "auto":
        selected_audio = {"Linux": "pa", "Windows": "dsound", "Darwin": "coreaudio"}.get(platform.system(), "none")
    if selected_audio != "none":
        backend = selected_audio
        if backend == "wav":
            backend += ",path=" + str(RUNTIME / "audio.wav").replace(",", ",,")
        cmd += ["-audiodev", backend + ",id=snd0,out.frequency=48000,out.channels=2",
                "-device", "usb-hub", "-device", "usb-audio,audiodev=snd0"]
    if args.firmware:
        firmware = args.firmware.resolve()
        if not firmware.is_file():
            raise ValueError(f"Firmware is missing: {firmware}")
        cmd += ["-bios", str(firmware)]
    if args.headless:
        cmd += ["-display", "none"]
    else:
        cmd += ["-display", "gtk,zoom-to-fit=off,grab-on-hover=off,show-cursor=on"]
    if args.snapshot:
        cmd += ["-snapshot"]
    return cmd


def configure_gtk_window(process, scale):
    tool = binary("xdotool")
    deadline = time.monotonic() + 12
    window = None
    while time.monotonic() < deadline and process.poll() is None:
        result = subprocess.run([tool, "search", "--onlyvisible", "--pid", str(process.pid)],
                                capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            window = result.stdout.splitlines()[0]
            break
        time.sleep(0.1)
    if window is None:
        raise ValueError("QEMU GTK window did not appear")
    subprocess.run([tool, "windowactivate", "--sync", window], check=True, timeout=3)
    subprocess.run([tool, "key", "--clearmodifiers", "ctrl+alt+0"], check=True, timeout=3)
    steps = round((1.0 - scale) / 0.25)
    if steps:
        subprocess.run([tool, "key", "--clearmodifiers", "--delay", "150"] +
                       ["ctrl+alt+minus"] * steps, check=True, timeout=4)
    subprocess.run([tool, "windowmove", window, "100", "40"], check=True, timeout=3)
    time.sleep(0.2)
    geometry = subprocess.check_output([tool, "getwindowgeometry", "--shell", window], text=True, timeout=2)
    save(RUNTIME / "window.json", {"qemu_pid": process.pid, "window": window,
                                  "scale": scale, "geometry": geometry})
    return window


def start(args):
    cmd = command(args)
    print(json.dumps(cmd, indent=2), flush=True)
    if args.dry_run:
        return
    save(RUNTIME / "last-command.json", {"argv": cmd, "boot_verified": False})
    print("Experimental SDK boot. QMP running status alone does not verify OS boot.", flush=True)
    controls = None
    with (RUNTIME / "qemu.stderr.log").open("a") as err:
        process = subprocess.Popen(cmd, stderr=err)
        save(RUNTIME / "process.json", {"qemu_pid": process.pid})
        try:
            if not args.headless and platform.system() == "Linux":
                window = configure_gtk_window(process, args.gtk_scale)
                if args.controls:
                    controls = subprocess.Popen([sys.executable, str(ROOT / "tools/phone_controls.py"),
                                                 "--qemu-pid", str(process.pid), "--window", window,
                                                 "--qmp-port", str(args.qmp_port)], stderr=err)
            result = process.wait()
        except (OSError, ValueError, subprocess.SubprocessError):
            process.terminate()
            process.wait(timeout=5)
            raise
        finally:
            if controls is not None and controls.poll() is None:
                controls.terminate()
                controls.wait(timeout=3)
    if result:
        raise ValueError(f"QEMU exited with {result}. See {RUNTIME / 'qemu.stderr.log'}")


def qmp(args):
    if args.action == "button":
        if args.button is None:
            raise ValueError("button requires --button")
        print(json.dumps(send_button(args.button, args.qmp_port)))
        return
    with socket.create_connection(("127.0.0.1", args.qmp_port), timeout=10) as sock:
        sock.settimeout(15)
        with sock.makefile("rwb") as stream:
            greeting = json.loads(stream.readline())
            if "QMP" not in greeting:
                raise ValueError("QMP greeting is missing")

            def execute(name, arguments=None):
                request = {"execute": name, "id": name}
                if arguments is not None:
                    request["arguments"] = arguments
                stream.write(json.dumps(request).encode() + b"\n")
                stream.flush()
                while True:
                    try:
                        line = stream.readline()
                    except ConnectionResetError:
                        if name == "quit":
                            return {"quit_sent": True}
                        raise
                    if not line:
                        if name == "quit":
                            return {"quit_sent": True}
                        raise ValueError("QMP connection closed before the reply")
                    reply = json.loads(line)
                    if reply.get("id") == name:
                        if "error" in reply:
                            raise ValueError(str(reply["error"]))
                        return reply.get("return")

            execute("qmp_capabilities")
            if args.action == "screenshot":
                time.sleep(args.delay)
                dest = args.output.resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    raise ValueError(f"Screenshot exists; refusing to overwrite {dest}")
                print(execute("screendump", {"filename": str(dest)}))
                print(dest)
            elif args.action == "diagnose":
                print(json.dumps({
                    "status": execute("query-status"),
                    "cpus": execute("query-cpus-fast"),
                    "blockstats": execute("query-blockstats"),
                    "registers": execute("human-monitor-command", {"command-line": "info registers"})
                }, indent=2))
            elif args.action == "key":
                if args.key is None:
                    raise ValueError("key requires --key")
                key = {"type": "qcode", "data": args.key}
                execute("input-send-event", {"events": [
                    {"type": "key", "data": {"down": True, "key": key}}]})
                time.sleep(0.08)
                print(execute("input-send-event", {"events": [
                    {"type": "key", "data": {"down": False, "key": key}}]}))
            elif args.action == "chord":
                if not args.keys:
                    raise ValueError("chord requires --keys")
                print(execute("send-key", {"keys": [{"type": "qcode", "data": k} for k in args.keys], "hold-time": 100}))
            elif args.action == "text":
                if not args.text or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789 " for c in args.text):
                    raise ValueError("text requires --text with lowercase ASCII letters, digits and spaces")
                for char in args.text:
                    key = {"type": "qcode", "data": "spc" if char == " " else char}
                    for down in (True, False):
                        execute("input-send-event", {"events": [
                            {"type": "key", "data": {"down": down, "key": key}}]})
                        time.sleep(0.04)
                print(json.dumps({"characters_sent": len(args.text)}))
            elif args.action == "scroll":
                for _ in range(args.steps):
                    for down in (True, False):
                        execute("input-send-event", {"events": [
                            {"type": "btn", "data": {"down": down, "button": "wheel-down"}}]})
                        time.sleep(0.04)
                print(json.dumps({"scroll_steps": args.steps}))
            elif args.action == "audio-record":
                dest = args.output.resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    raise ValueError(f"Audio recording exists: {dest}")
                print(execute("human-monitor-command", {
                    "command-line": f"wavcapture {json.dumps(str(dest))} snd0 48000 16 2"}))
            elif args.action == "audio-stop":
                print(execute("human-monitor-command", {"command-line": "stopcapture 0"}))
            elif args.action in ("click", "drag"):
                if args.x is None or args.y is None:
                    raise ValueError("click requires --x and --y")
                width, height = args.width, args.height
                if width is None or height is None:
                    with tempfile.TemporaryDirectory(dir=RUNTIME) as tmp:
                        path = Path(tmp) / "geometry.ppm"
                        execute("screendump", {"filename": str(path)})
                        with path.open("rb") as ppm:
                            ppm.readline()
                            line = ppm.readline()
                            while line.startswith(b"#"):
                                line = ppm.readline()
                            width, height = map(int, line.split())
                if not (0 <= args.x < width and 0 <= args.y < height):
                    raise ValueError("Click coordinates must be within the specified display dimensions")
                if args.action == "drag" and (args.x2 is None or args.y2 is None or
                        not (0 <= args.x2 < width and 0 <= args.y2 < height)):
                    raise ValueError("drag requires --x2 and --y2 within the display")
                execute("input-send-event", {"events": [
                    {"type": "abs", "data": {"axis": "x", "value": args.x * 32767 // width}},
                    {"type": "abs", "data": {"axis": "y", "value": args.y * 32767 // height}},
                    {"type": "btn", "data": {"down": True, "button": "left"}}]})
                time.sleep(0.08)
                if args.action == "drag":
                    for step in range(1, args.steps + 1):
                        x = round(args.x + (args.x2 - args.x) * step / args.steps)
                        y = round(args.y + (args.y2 - args.y) * step / args.steps)
                        execute("input-send-event", {"events": [
                            {"type": "abs", "data": {"axis": "x", "value": x * 32767 // width}},
                            {"type": "abs", "data": {"axis": "y", "value": y * 32767 // height}}
                        ]})
                        time.sleep(args.duration / args.steps)
                print(execute("input-send-event", {"events": [
                    {"type": "btn", "data": {"down": False, "button": "left"}}]}))
                time.sleep(0.25)
            else:
                print(json.dumps(execute({"status": "query-status", "quit": "quit"}[args.action])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("doctor", doctor), ("download-sdk", download), ("verify-sdk", verify),
                     ("prepare-sdk", prepare)):
        sub.add_parser(name).set_defaults(fn=fn)
    p = sub.add_parser("import-image")
    p.add_argument("image", type=Path)
    p.set_defaults(fn=import_image)
    p = sub.add_parser("start")
    p.add_argument("--qemu", type=Path, help="QEMU executable; default prefers the locally built touchscreen version")
    p.add_argument("--pointer", choices=("auto", "touch", "mouse"), default="auto")
    p.add_argument("--accel", choices=("auto", "tcg", "kvm", "whpx"), default="auto")
    p.add_argument("--cpu", help="Default: host with KVM, max otherwise")
    p.add_argument("--machine", choices=("pc", "q35"), default="pc")
    p.add_argument("--smp", type=int, choices=range(1, 5), default=4)
    p.add_argument("--firmware", type=Path, help="Optional firmware file; default is QEMU SeaBIOS")
    p.add_argument("--qmp-port", type=int, default=44520)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--portrait", action=argparse.BooleanOptionalAction, default=True,
                   help="1080x1920 native framebuffer (default); --no-portrait restores standard VGA")
    p.add_argument("--vga-rom", type=Path, help="Optional VGA option ROM")
    p.add_argument("--gtk-scale", type=float, choices=(0.25, 0.5, 0.75, 1.0), default=0.5,
                   help="GTK display scale on Linux/X11; does not change guest pixels")
    p.add_argument("--controls", action=argparse.BooleanOptionalAction, default=True,
                   help="Dock phone buttons and enable Ctrl+Alt+Shift host shortcuts on X11")
    p.add_argument("--nic", choices=("none", "tulip", "e1000", "rtl8139"), default="e1000",
                   help="E1000 DHCP and Device Portal verified; other NICs are experimental")
    p.add_argument("--trace-network", action="store_true")
    p.add_argument("--audio", choices=("auto", "none", "pa", "alsa", "sdl", "dsound", "coreaudio", "wav"), default="auto",
                   help="USB stereo output; auto selects pa on Linux, dsound on Windows, coreaudio on macOS")
    p.add_argument("--snapshot", action="store_true", help="Discard writes on exit")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=start)
    p = sub.add_parser("qmp")
    p.add_argument("action", choices=("status", "screenshot", "diagnose", "key", "chord", "click", "drag", "text", "scroll", "button", "audio-record", "audio-stop", "quit"))
    p.add_argument("--button", choices=tuple(PHONE_KEYS))
    p.add_argument("--qmp-port", type=int, default=44520)
    p.add_argument("--output", type=Path, default=RUNTIME / "screen.ppm")
    p.add_argument("--delay", type=float, default=1.0, help="Delay before screenshot, seconds")
    p.add_argument("--key", choices=("tab", "ret", "esc", "spc", "backspace", "up", "down", "left", "right", "home", "end", "pgup", "pgdn", "meta_l", "f4", "f12"))
    p.add_argument("--text")
    p.add_argument("--keys", nargs="+")
    p.add_argument("--steps", type=int, choices=range(1, 31), default=6)
    p.add_argument("--x", type=int)
    p.add_argument("--y", type=int)
    p.add_argument("--x2", type=int)
    p.add_argument("--y2", type=int)
    p.add_argument("--duration", type=float, default=0.8)
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.set_defaults(fn=qmp)
    args = parser.parse_args()
    try:
        args.fn(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    except KeyboardInterrupt:
        parser.exit(130, "Stopped.\n")


if __name__ == "__main__":
    main()
