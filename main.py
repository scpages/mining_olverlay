import tkinter as tk
import threading
import time
import re
import mss
import pytesseract
from PIL import Image

from resources import analyze_rs

# ── Tesseract path ────────────────────────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── Config ────────────────────────────────────────────────────────────────────
GAME_MONITOR    = 1     # monitor the game runs on
OVERLAY_MONITOR = 2     # monitor for the overlay (set to 1 if single monitor)

REGION_X = 0.459
REGION_Y = 0.367
REGION_W = 0.086
REGION_H = 0.042

POLL_INTERVAL = 0.5   # seconds between captures
DEBUG         = False  # set True to save processed images to debug/ folder

# ── Colours ───────────────────────────────────────────────────────────────────
TIER_COLOR  = {"S": "#FFD700", "A": "#00CC55", "B": "#FFAA00", "C": "#888888"}
CONF_COLOR  = {100: "#00FF88", 90: "#88FF44", 80: "#FFDD00", 0: "#FF6644"}
BG          = "#0a0a18"
BG2         = "#12122a"

MODES = ["ship", "fps", "ground"]

# ─────────────────────────────────────────────────────────────────────────────

class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SC Mining Overlay")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)

        self._mode_idx = 0
        self._last_rs  = None
        self.running   = True

        self._place_window()
        self._build_ui()
        self._make_draggable()

        threading.Thread(target=self._loop, daemon=True).start()

    # ── window ────────────────────────────────────────────────────────────────

    def _place_window(self):
        with mss.MSS() as sct:
            monitors = sct.monitors
            idx = OVERLAY_MONITOR if OVERLAY_MONITOR < len(monitors) else 1
            m   = monitors[idx]
        self.root.geometry(f"340x260+{m['left'] + 20}+{m['top'] + 20}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── title bar ──
        bar = tk.Frame(self.root, bg=BG2, height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="SC MINING", font=("Consolas", 9, "bold"),
                 bg=BG2, fg="#4477aa").pack(side="left", padx=8)

        close = tk.Label(bar, text="✕", font=("Consolas", 10),
                         bg=BG2, fg="#555", cursor="hand2")
        close.pack(side="right", padx=8)
        close.bind("<Button-1>", lambda _: self._quit())

        self.mode_btn = tk.Label(bar, text="SHIP", font=("Consolas", 9, "bold"),
                                  bg=BG2, fg="#4477aa", cursor="hand2")
        self.mode_btn.pack(side="right", padx=4)
        self.mode_btn.bind("<Button-1>", lambda _: self._cycle_mode())

        # ── RS readout ──
        rs_frame = tk.Frame(self.root, bg=BG, pady=6)
        rs_frame.pack(fill="x", padx=10)

        tk.Label(rs_frame, text="RS", font=("Consolas", 9), bg=BG, fg="#445").pack(side="left")
        self.rs_lbl = tk.Label(rs_frame, text="—", font=("Consolas", 18, "bold"),
                                bg=BG, fg="#335577")
        self.rs_lbl.pack(side="left", padx=8)

        sep = tk.Frame(self.root, bg="#1a1a3a", height=1)
        sep.pack(fill="x", padx=6)

        # ── top match (large) ──
        self.top_frame = tk.Frame(self.root, bg=BG, pady=8)
        self.top_frame.pack(fill="x", padx=10)

        self.top_tier  = tk.Label(self.top_frame, text="", font=("Consolas", 22, "bold"),
                                   bg=BG, fg="#333", width=4, anchor="w")
        self.top_tier.pack(side="left")

        top_right = tk.Frame(self.top_frame, bg=BG)
        top_right.pack(side="left", fill="x", expand=True)

        self.top_name  = tk.Label(top_right, text="Waiting for scan…",
                                   font=("Consolas", 13, "bold"), bg=BG, fg="#445", anchor="w")
        self.top_name.pack(fill="x")

        self.top_meta  = tk.Label(top_right, text="",
                                   font=("Consolas", 9), bg=BG, fg="#445", anchor="w")
        self.top_meta.pack(fill="x")

        self.top_notes = tk.Label(top_right, text="",
                                   font=("Consolas", 8), bg=BG, fg="#445",
                                   wraplength=230, justify="left", anchor="w")
        self.top_notes.pack(fill="x")

        sep2 = tk.Frame(self.root, bg="#1a1a3a", height=1)
        sep2.pack(fill="x", padx=6, pady=(4, 0))

        # ── alternatives (small) ──
        self.alt_labels = []
        for _ in range(4):
            lbl = tk.Label(self.root, text="", font=("Consolas", 9),
                           bg=BG, fg="#445", anchor="w")
            lbl.pack(fill="x", padx=14, pady=1)
            self.alt_labels.append(lbl)

    def _make_draggable(self):
        self.root.bind("<Button-1>",  lambda e: (setattr(self, "_ox", e.x), setattr(self, "_oy", e.y)))
        self.root.bind("<B1-Motion>", lambda e: self.root.geometry(
            f"+{self.root.winfo_x()+e.x-self._ox}+{self.root.winfo_y()+e.y-self._oy}"))

    # ── mode toggle ───────────────────────────────────────────────────────────

    def _cycle_mode(self):
        self._mode_idx = (self._mode_idx + 1) % len(MODES)
        self.mode_btn.config(text=MODES[self._mode_idx].upper())
        self._last_rs = None   # force refresh

    @property
    def _mode(self):
        return MODES[self._mode_idx]

    # ── update display ────────────────────────────────────────────────────────

    def _refresh(self, total_rs):
        matches = analyze_rs(total_rs, self._mode) if total_rs else []
        self.root.after(0, self._draw, total_rs, matches)

    def _draw(self, total_rs, matches):
        # RS readout
        if total_rs:
            self.rs_lbl.config(text=f"{total_rs:,}", fg="#6699cc")
        else:
            self.rs_lbl.config(text="—", fg="#335577")

        if not matches:
            self.top_tier.config(text="", fg="#333")
            self.top_name.config(text="No match" if total_rs else "Waiting for scan…", fg="#445")
            self.top_meta.config(text="")
            self.top_notes.config(text="")
            for lbl in self.alt_labels:
                lbl.config(text="")
            return

        # Top match
        m = matches[0]
        color      = TIER_COLOR.get(m["tier"], "#fff")
        conf_color = self._conf_color(m["label"])
        nodes_str  = f"{m['nodes']} node{'s' if m['nodes']>1 else ''}"
        delta_str  = f"Δ{m['remainder']:,}" if m["remainder"] else "exact"
        self.top_tier.config(text=f"[{m['tier']}]", fg=color)
        self.top_name.config(text=m["name"], fg=color)
        self.top_meta.config(
            text=f"{nodes_str}  •  {m['label']}  •  {m['confidence']}%  ({delta_str})",
            fg=conf_color)
        self.top_notes.config(text=m["notes"], fg="#aaa")

        # Alternatives
        for i, lbl in enumerate(self.alt_labels):
            if i + 1 < len(matches):
                a = matches[i + 1]
                c = TIER_COLOR.get(a["tier"], "#888")
                lbl.config(
                    text=f"  [{a['tier']}] {a['name']:<14}  {a['nodes']}×  {a['confidence']}%",
                    fg=c)
            else:
                lbl.config(text="")

    def _conf_color(self, label):
        return {
            "EXACT":  CONF_COLOR[100],
            "CLOSE":  CONF_COLOR[90],
            "APPROX": CONF_COLOR[80],
            "ROUGH":  CONF_COLOR[0],
        }.get(label, CONF_COLOR[0])

    # ── capture loop ──────────────────────────────────────────────────────────

    def _loop(self):
        with mss.MSS() as sct:
            monitors = sct.monitors
            idx = GAME_MONITOR if GAME_MONITOR < len(monitors) else 1
            m   = monitors[idx]
            region = {
                "left":   int(m["width"]  * REGION_X) + m["left"],
                "top":    int(m["height"] * REGION_Y) + m["top"],
                "width":  int(m["width"]  * REGION_W),
                "height": int(m["height"] * REGION_H),
            }

            while self.running:
                try:
                    shot     = sct.grab(region)
                    img      = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    total_rs = _best_rs(_ocr(img))

                    if total_rs != self._last_rs:
                        self._last_rs = total_rs
                        self._refresh(total_rs)
                except Exception:
                    pass
                time.sleep(POLL_INTERVAL)

    def _quit(self):
        self.running = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ── OCR ───────────────────────────────────────────────────────────────────────

_debug_counter = 0

def _ocr(img: Image.Image) -> str:
    """Return raw digit string from capture. Caller resolves the best RS value."""
    global _debug_counter

    w, h = img.size
    # Trim top 20% (removes UI frame) and right 5% (removes edge artifact)
    img = img.crop((0, int(h * 0.20), int(w * 0.95), h))

    gray   = img.convert("L")
    gray   = gray.resize((gray.width * 4, gray.height * 4), Image.LANCZOS)
    binary = gray.point(lambda p: 255 if p > 140 else 0)
    inv    = binary.point(lambda p: 0 if p else 255)
    padded = Image.new("L", (inv.width + 40, inv.height + 40), 255)
    padded.paste(inv, (20, 20))

    if DEBUG:
        import os
        os.makedirs("debug", exist_ok=True)
        padded.save(f"debug/{_debug_counter:04d}.png")
        _debug_counter += 1

    cfg  = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.,"
    text = pytesseract.image_to_string(padded, config=cfg).strip()
    return re.sub(r"[^0-9]", "", text)


def _best_rs(digits: str) -> int | None:
    """
    The icon left of the number can add a spurious leading digit.
    Try the full string, then strip 1-2 leading digits.
    Return the candidate whose analyze_rs() gives the highest confidence.
    Require confidence >= 60 to filter out pure noise.
    """
    if len(digits) < 3:
        return None

    best_val, best_conf = None, -1

    for start in range(min(3, len(digits) - 2)):
        candidate = digits[start:]
        try:
            val = int(candidate)
        except ValueError:
            continue
        if val < 1000:
            continue
        results = analyze_rs(val)
        conf = results[0]["confidence"] if results else -1
        if conf > best_conf:
            best_conf, best_val = conf, val

    return best_val if best_conf >= 60 else None


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Overlay().run()
