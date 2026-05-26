"""
Run this while Star Citizen is open with the RS number visible.
Saves step-by-step processed images and prints what OCR reads.
Use this to verify the region and preprocessing are correct.
"""

import re
import sys
import mss
import pytesseract
from PIL import Image

sys.path.insert(0, ".")
from resources import analyze_rs

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

GAME_MONITOR = 1
REGION_X     = 0.459
REGION_Y     = 0.367
REGION_W     = 0.086
REGION_H     = 0.042

print("\nSwitch to Star Citizen now — capturing in 5 seconds...")
import time
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)
print("Capturing!\n")

with mss.MSS() as sct:
    monitors = sct.monitors
    m = monitors[GAME_MONITOR]
    region = {
        "left":   int(m["width"]  * REGION_X) + m["left"],
        "top":    int(m["height"] * REGION_Y) + m["top"],
        "width":  int(m["width"]  * REGION_W),
        "height": int(m["height"] * REGION_H),
    }
    print(f"Capturing region: {region}")
    shot = sct.grab(region)
    img  = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

img.save("step0_raw.png")
print("Saved step0_raw.png  (original capture)")

w, h = img.size
img = img.crop((0, int(h * 0.20), int(w * 0.95), h))
img.save("step1_trimmed.png")
print("Saved step1_trimmed.png  (top + right trimmed)")

gray = img.convert("L")
gray = gray.resize((gray.width * 4, gray.height * 4), Image.LANCZOS)
gray.save("step2_scaled.png")
print("Saved step2_scaled.png  (grayscale 4x)")

binary = gray.point(lambda p: 255 if p > 140 else 0)
inv    = binary.point(lambda p: 0 if p else 255)
padded = Image.new("L", (inv.width + 40, inv.height + 40), 255)
padded.paste(inv, (20, 20))
padded.save("step3_final.png")
print("Saved step3_final.png  (what OCR sees)")

print("\n--- PSM mode comparison ---")
best_digits = ""
for psm in [7, 6, 8, 11, 13]:
    cfg  = f"--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789.,"
    text = pytesseract.image_to_string(padded, config=cfg).strip()
    d    = re.sub(r"[^0-9]", "", text)
    print(f"  PSM {psm:2d}: raw='{text}'  digits='{d}'")
    if len(d) > len(best_digits):
        best_digits = d

digits = best_digits
print(f"\nBest digits: '{digits}'")

# Try best RS resolution
best_val, best_conf = None, -1
for start in range(min(3, max(0, len(digits) - 2))):
    candidate = digits[start:]
    try:
        val = int(candidate)
        if val < 1000:
            continue
        results = analyze_rs(val)
        conf = results[0]["confidence"] if results else -1
        marker = " <-- best" if conf > best_conf else ""
        print(f"  strip {start}: {val:>8,}  →  conf={conf}%{marker}")
        if conf > best_conf:
            best_conf, best_val = conf, val
    except ValueError:
        pass

if best_val and best_conf >= 60:
    print(f"\nResult: RS {best_val:,}")
    results = analyze_rs(best_val)
    for r in results[:3]:
        print(f"  [{r['tier']}] {r['name']:15} {r['nodes']}×  {r['label']:6}  {r['confidence']}%")
else:
    print("\nNo confident match found — check step3_final.png")
