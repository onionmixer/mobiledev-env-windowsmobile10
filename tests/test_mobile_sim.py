"""Storage integrity checks using small synthetic disks, never the SDK guest."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest
from unittest.mock import patch
from argparse import Namespace

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
spec = importlib.util.spec_from_file_location("mobile_sim", Path(__file__).parents[1] / "tools/mobile_sim.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)
from phone_controls import panel_geometry


class StorageTests(unittest.TestCase):
    def test_corrupt_sdk_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "test.cab"
            payload.write_bytes(b"good")
            record = {"payloads": [{"path": "test.cab", "size": 4,
                                   "sha1_from_bootstrapper": hashlib.sha1(b"good").hexdigest()}]}
            with patch.object(sim, "SDK", root), patch.object(sim, "manifest", return_value=record):
                sim.verify(None)
                self.assertTrue((root / "verified.json").exists())
                payload.write_bytes(b"evil")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    sim.verify(None)

    def test_existing_disk_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "base.qcow2"
            target.write_bytes(b"existing guest data")
            with patch.object(sim, "RUNTIME", root):
                with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                    sim.import_image(Namespace(image=root / "unused.vhd"))
            self.assertEqual(target.read_bytes(), b"existing guest data")

    def test_real_vhd_import_preserves_source_and_creates_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "synthetic.vhd"
            subprocess.run([sim.binary("qemu-img"), "create", "-f", "vpc", str(source), "2M"],
                           check=True, stdout=subprocess.DEVNULL)
            before = sim.digest(source)
            runtime = root / "runtime"
            with patch.object(sim, "RUNTIME", runtime):
                sim.import_image(Namespace(image=source))
            self.assertEqual(sim.digest(source), before)
            info = json.loads(subprocess.check_output([sim.binary("qemu-img"), "info", "--output=json",
                                                       str(runtime / "disk.qcow2")], text=True))
            self.assertEqual(info["backing-filename"], "base.qcow2")
            self.assertEqual(Path(info["full-backing-filename"]).resolve(), runtime / "base.qcow2")
            self.assertEqual(info["backing-filename-format"], "qcow2")
            moved = root / "moved-runtime"
            runtime.rename(moved)
            subprocess.run([sim.binary("qemu-img"), "compare", "-q", "-f", "vpc", "-F", "qcow2",
                            str(source), str(moved / "disk.qcow2")], check=True)

    def test_ffu_is_rejected_before_import(self):
        with self.assertRaisesRegex(ValueError, "ARM FFU"):
            sim.import_image(Namespace(image=Path("phone.ffu")))


class ControlPlacementTests(unittest.TestCase):
    def test_controls_remain_on_landscape_monitor_when_qemu_bottom_is_offscreen(self):
        monitor = (1080, 840, 1920, 1080)
        x, y, w, h = panel_geometry(1494, 950, 540, 987, [monitor])
        self.assertGreaterEqual(x, 1494 + 540)
        self.assertGreaterEqual(y, monitor[1])
        self.assertLessEqual(x + w, monitor[0] + monitor[2])
        self.assertLessEqual(y + h, monitor[1] + monitor[3])

    def test_controls_move_left_at_right_monitor_edge(self):
        x, y, w, h = panel_geometry(5400, 100, 540, 987, [(4920, 0, 1080, 1920)])
        self.assertLessEqual(x + w, 5400)
        self.assertGreaterEqual(x, 4920)

    def test_controls_support_negative_monitor_coordinates(self):
        x, y, w, h = panel_geometry(-1000, 300, 540, 987, [(-1080, 0, 1080, 1920)])
        self.assertGreaterEqual(x, -1080)
        self.assertLessEqual(x + w, 0)
        self.assertLessEqual(y + h, 1920)


if __name__ == "__main__":
    unittest.main()
