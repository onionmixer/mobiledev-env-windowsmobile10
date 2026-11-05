#!/usr/bin/env python3
"""Docked phone buttons and explicit X11 host shortcuts for the QEMU guest."""
import argparse
import ctypes as C
import ctypes.util
import os
import re
import subprocess
import threading
import tkinter as tk
from phone_input import send_button

BUTTONS = [
    ("Back", "back", "b"), ("Start", "start", "h"),
    ("Search", "search", "s"), ("Volume −", "volume-down", "d"),
    ("Volume +", "volume-up", "u"), ("Power", "power", "p"),
    ("Camera", "camera", "c"),
]


def panel_geometry(x, y, width, height, monitors):
    panel_width, panel_height = 104, 400
    panel_x, panel_y = x + width + 8, y
    for mx, my, mw, mh in monitors:
        if mx <= x + width // 2 < mx + mw and my <= y + height // 2 < my + mh:
            if panel_x + panel_width > mx + mw:
                panel_x = x - panel_width - 8
            panel_x = max(mx, min(panel_x, mx + mw - panel_width))
            panel_y = max(my, min(panel_y, my + mh - panel_height))
            break
    return panel_x, panel_y, panel_width, panel_height


class XKeyEvent(C.Structure):
    _fields_ = [("type", C.c_int), ("serial", C.c_ulong), ("send_event", C.c_int),
                ("display", C.c_void_p), ("window", C.c_ulong), ("root", C.c_ulong),
                ("subwindow", C.c_ulong), ("time", C.c_ulong),
                ("x", C.c_int), ("y", C.c_int), ("x_root", C.c_int), ("y_root", C.c_int),
                ("state", C.c_uint), ("keycode", C.c_uint), ("same_screen", C.c_int)]


class XEvent(C.Union):
    _fields_ = [("type", C.c_int), ("key", XKeyEvent), ("pad", C.c_long * 24)]


class HostShortcuts:
    """Grab only Ctrl+Alt+Shift plus the seven documented button keys."""
    def __init__(self):
        self.lib = C.CDLL(ctypes.util.find_library("X11"))
        lib = self.lib
        lib.XOpenDisplay.argtypes = [C.c_char_p]
        lib.XOpenDisplay.restype = C.c_void_p
        lib.XDefaultRootWindow.argtypes = [C.c_void_p]
        lib.XDefaultRootWindow.restype = C.c_ulong
        lib.XStringToKeysym.argtypes = [C.c_char_p]
        lib.XStringToKeysym.restype = C.c_ulong
        lib.XKeysymToKeycode.argtypes = [C.c_void_p, C.c_ulong]
        lib.XKeysymToKeycode.restype = C.c_uint
        lib.XGrabKey.argtypes = [C.c_void_p, C.c_int, C.c_uint, C.c_ulong, C.c_int, C.c_int, C.c_int]
        lib.XPending.argtypes = [C.c_void_p]
        lib.XPending.restype = C.c_int
        lib.XNextEvent.argtypes = [C.c_void_p, C.POINTER(XEvent)]
        lib.XSync.argtypes = [C.c_void_p, C.c_int]
        lib.XCloseDisplay.argtypes = [C.c_void_p]
        lib.XSetErrorHandler.argtypes = [C.c_void_p]
        lib.XSetErrorHandler.restype = C.c_void_p
        self.display = lib.XOpenDisplay(None)
        if not self.display:
            raise OSError("X11 display is not available")
        self.errors = []
        callback_type = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p)
        self.error_handler = callback_type(lambda _d, _e: self.errors.append(True) or 0)
        previous = lib.XSetErrorHandler(C.cast(self.error_handler, C.c_void_p))
        root = lib.XDefaultRootWindow(self.display)
        self.mapping = {}
        try:
            for _, action, key in BUTTONS:
                code = lib.XKeysymToKeycode(self.display, lib.XStringToKeysym(key.encode()))
                self.mapping[code] = action
                for lock_mask in (0, 2, 16, 18):  # Caps Lock and Num Lock variants.
                    lib.XGrabKey(self.display, code, 1 | 4 | 8 | lock_mask, root, 0, 1, 1)
            lib.XSync(self.display, 0)
        finally:
            lib.XSetErrorHandler(previous)

    def pending(self):
        actions = []
        while self.lib.XPending(self.display):
            event = XEvent()
            self.lib.XNextEvent(self.display, C.byref(event))
            if event.type == 2 and event.key.keycode in self.mapping:
                actions.append(self.mapping[event.key.keycode])
        return actions

    def close(self):
        if self.display:
            self.lib.XCloseDisplay(self.display)
            self.display = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qemu-pid", type=int, required=True)
    parser.add_argument("--window", required=True)
    parser.add_argument("--qmp-port", type=int, default=44520)
    args = parser.parse_args()
    root = tk.Tk()
    root.title("Lumia phone buttons")
    root.configure(bg="#202124")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    status = tk.StringVar(value="Ctrl+Alt+Shift + B / H / S / D / U / P / C")
    result_queue = []
    busy = False

    def press(action):
        nonlocal busy
        if busy:
            return
        busy = True

        def worker():
            try:
                send_button(action, args.qmp_port)
                result_queue.append(f"{action} ✓")
            except (OSError, ValueError) as exc:
                result_queue.append(f"Connection error: {exc}")
        threading.Thread(target=worker, daemon=True).start()

    row = tk.Frame(root, bg="#202124")
    row.pack(fill="x", padx=4, pady=(6, 2))
    row.columnconfigure(0, weight=1)
    for index, (label, action, key) in enumerate(BUTTONS):
        tk.Button(row, text=label, command=lambda a=action: press(a),
                  bg="#303236", fg="white", activebackground="#4a4d53", activeforeground="white",
                  relief="flat", takefocus=False, padx=2, pady=8).grid(row=index, column=0, sticky="ew", padx=2, pady=2)
        root.bind(f"<Control-Alt-Shift-{key.upper()}>", lambda _event, a=action: press(a))
    tk.Label(root, textvariable=status, bg="#202124", fg="#cbd0d8", font=("sans", 8), wraplength=88).pack(pady=(0, 5))
    shortcuts = None
    try:
        shortcuts = HostShortcuts()
        if shortcuts.errors:
            status.set("Some host shortcuts are in use. Buttons remain available.")
    except (OSError, AttributeError, TypeError):
        status.set("Host shortcuts require X11. Buttons remain available.")

    monitors = []
    try:
        text = subprocess.check_output(["xrandr", "--listmonitors"], text=True, timeout=2)
        for w, h, x, y in re.findall(r"(\d+)/\d+x(\d+)/\d+([+-]\d+)([+-]\d+)", text):
            monitors.append(tuple(map(int, (x, y, w, h))))
    except (OSError, subprocess.SubprocessError):
        pass

    def poll():
        nonlocal busy
        try:
            os.kill(args.qemu_pid, 0)
        except ProcessLookupError:
            root.destroy()
            return
        if result_queue:
            status.set(result_queue.pop(0))
            busy = False
        if shortcuts:
            for action in shortcuts.pending():
                press(action)
        root.after(60, poll)

    def dock():
        try:
            result = subprocess.run(["xdotool", "getwindowgeometry", "--shell", args.window],
                                    check=True, capture_output=True, text=True, timeout=1)
            geo = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
            x, y, width, height = (int(geo[k]) for k in ("X", "Y", "WIDTH", "HEIGHT"))
            panel_x, panel_y, panel_width, panel_height = panel_geometry(x, y, width, height, monitors)
            root.geometry(f"{panel_width}x{panel_height}{panel_x:+d}{panel_y:+d}")
            active = subprocess.run(["xdotool", "getactivewindow"], capture_output=True,
                                    text=True, timeout=1).stdout.strip()
            own = str(root.winfo_id())
            if active not in (args.window, own):
                root.attributes("-topmost", False)
            else:
                root.attributes("-topmost", True)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        root.after(600, dock)

    root.after(0, dock)
    root.after(60, poll)
    try:
        root.mainloop()
    finally:
        if shortcuts:
            shortcuts.close()


if __name__ == "__main__":
    main()
