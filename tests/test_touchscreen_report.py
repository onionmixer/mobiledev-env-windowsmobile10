"""Compile the patched report encoder and check the HID contact lifecycle.

The tablet sample and clock are stubs; the encoder is extracted verbatim from
the committed QEMU patch so this test also works without a QEMU checkout.
USB transport and Windows gesture handling still require guest validation.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class TouchscreenReportTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "C compiler required for HID encoder regression")
    def test_tap_release_remains_confident_and_preserves_contact(self):
        patch = Path(__file__).parents[1] / "emulator/qemu-build/usb-touchscreen.patch"
        lines = patch.read_text().splitlines()
        start = lines.index("+static int usb_hid_pointer_poll(USBHIDState *us, uint8_t *data, int length)")
        end = lines.index("+}", start)
        encoder = "\n".join(line[1:] for line in lines[start:end + 1])
        harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define QEMU_CLOCK_VIRTUAL 0
typedef struct { uint8_t sample[8]; } HIDState;
typedef struct { bool touchscreen; HIDState hid; } USBHIDState;
static uint64_t now_ms = 6554;
static uint64_t qemu_clock_get_ms(int clock) { (void)clock; return now_ms; }
static int hid_pointer_poll(HIDState *hs, uint8_t *data, int length)
{
    int copied = length < 6 ? length : 6;
    memcpy(data, hs->sample, copied);
    return copied;
}
'''
        checks = r'''
int main(void)
{
    USBHIDState us = { .touchscreen = true,
        .hid.sample = { 1, 0x34, 0x12, 0x78, 0x56, 0 } };
    uint8_t down[10], up[10], limited[12], mouse[8] = {0};
    assert(usb_hid_pointer_poll(&us, down, sizeof(down)) == 10);
    assert(down[0] == 1 && (down[1] & 1) && (down[1] & 4));
    assert(down[9] == 1);
    us.hid.sample[0] = 0;
    now_ms += 80;
    assert(usb_hid_pointer_poll(&us, up, sizeof(up)) == 10);
    assert(!(up[1] & 1));
    if (!(up[1] & 4)) {
        fputs("Touch lift must retain Confidence; clearing it cancels taps.\n", stderr);
        return 1;
    }
    assert(up[0] == down[0] && up[2] == down[2]);
    assert(memcmp(up + 3, down + 3, 4) == 0);
    assert(up[9] == 1); /* A final tip-up contact is still reported. */
    assert((uint16_t)(up[7] | (up[8] << 8)) == (uint16_t)(now_ms * 10));
    memset(limited, 0xa5, sizeof(limited));
    assert(usb_hid_pointer_poll(&us, limited, 5) == 5);
    assert(limited[5] == 0xa5 && limited[11] == 0xa5);
    us.touchscreen = false;
    assert(usb_hid_pointer_poll(&us, mouse, sizeof(mouse)) == 6);
    assert(memcmp(mouse, us.hid.sample, 6) == 0);
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="wm10-touch-report-") as tmp:
            source = Path(tmp) / "report.c"
            executable = Path(tmp) / "report-test"
            source.write_text(harness + encoder + checks)
            compiled = subprocess.run([shutil.which("cc"), "-std=c11", str(source), "-o", str(executable)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
