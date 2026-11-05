"""Phone hardware-key gestures sent through QMP, independent of GTK focus."""
import json
import socket

# Microsoft SDK 14393+ keyboard gestures. Start also accepts the Windows key.
PHONE_KEYS = {
    "back": ("meta_l", "esc"),
    "start": ("meta_l",),
    "search": ("meta_l", "f3"),
    "volume-up": ("meta_l", "f9"),
    "volume-down": ("meta_l", "f10"),
    "power": ("meta_l", "f12"),
    "camera": ("meta_l", "f7"),
}


def send_button(name, port=44520):
    keys = PHONE_KEYS[name]
    with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
        sock.settimeout(3)
        with sock.makefile("rwb") as stream:
            if "QMP" not in json.loads(stream.readline()):
                raise ValueError("QMP greeting is missing")

            def execute(command, arguments=None):
                request = {"execute": command, "id": command}
                if arguments is not None:
                    request["arguments"] = arguments
                stream.write(json.dumps(request).encode() + b"\n")
                stream.flush()
                while True:
                    data = stream.readline()
                    if not data:
                        raise OSError("QMP disconnected")
                    response = json.loads(data)
                    if response.get("id") == command:
                        if "error" in response:
                            raise ValueError(str(response["error"]))
                        return response.get("return")

            execute("qmp_capabilities")
            # A grabbed host shortcut may have already delivered its modifiers
            # to GTK. Release them before sending the phone's own gesture.
            execute("input-send-event", {"events": [
                {"type": "key", "data": {"down": False, "key": {"type": "qcode", "data": key}}}
                for key in ("ctrl", "alt", "shift", "meta_l")
            ]})
            return execute("send-key", {"keys": [{"type": "qcode", "data": k} for k in keys],
                                        "hold-time": 100})
