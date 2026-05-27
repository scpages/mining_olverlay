import tkinter as tk
import threading
import time
import re
import mss
import pytesseract
from PIL import Image
from collections import deque

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

POLL_INTERVAL  = 0.1    # seconds between captures
HISTORY_SIZE   = 5      # how many unique scans to remember
MAX_RS         = 100_000  # ignore OCR readings above this value
DEBUG          = False  # set True to save processed images to debug/ folder

# ── Colours ───────────────────────────────────────────────────────────────────
TIER_COLOR = {"S": "#FFD700", "A": "#00CC55", "B": "#FFAA00", "C": "#888888"}
CONF_COLOR = {"EXACT": "#00FF88", "CLOSE": "#88FF44", "APPROX": "#FFDD00", "ROUGH": "#FF6644"}
BG  = "#0a0a18"
BG2 = "#12122a"
DIM = "#2a2a4a"

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
        self._history  = deque(maxlen=HISTORY_SIZE)   # stores raw RS ints, newest first
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
        w = 360
        h = 28 + HISTORY_SIZE * 50 + 12
        x = m["left"] + (m["width"] - w) // 2
        y = m["top"] + 20
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # title bar
        bar = tk.Frame(self.root, bg=BG2, height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="SC MINING", font=("Consolas", 9, "bold"),
                 bg=BG2, fg="#4477aa").pack(side="left", padx=8)

        close_btn = tk.Label(bar, text="✕", font=("Consolas", 10),
                             bg=BG2, fg="#555", cursor="hand2")
        close_btn.pack(side="right", padx=8)
        close_btn.bind("<Button-1>", lambda _: self._quit())

        self.mode_btn = tk.Label(bar, text="SHIP", font=("Consolas", 9, "bold"),
                                  bg=BG2, fg="#4477aa", cursor="hand2")
        self.mode_btn.pack(side="right", padx=4)
        self.mode_btn.bind("<Button-1>", lambda _: self._cycle_mode())

        # history rows
        self._rows = []
        for i in range(HISTORY_SIZE):
            if i > 0:
                tk.Frame(self.root, bg=DIM, height=1).pack(fill="x", padx=8)

            outer = tk.Frame(self.root, bg=BG, pady=4)
            outer.pack(fill="x", padx=10)

            top = tk.Frame(outer, bg=BG)
            top.pack(fill="x")

            # RS value — fixed width so rows align vertically
            rs_lbl = tk.Label(top, text="", font=("Consolas", 11, "bold"),
                               bg=BG, fg="#888", width=8, anchor="e")
            rs_lbl.pack(side="left")

            # node count
            nodes_lbl = tk.Label(top, text="", font=("Consolas", 11, "bold"),
                                  bg=BG, fg="#333", width=3, anchor="e")
            nodes_lbl.pack(side="left")

            # resource name
            name_lbl = tk.Label(top, text="Waiting…" if i == 0 else "",
                                 font=("Consolas", 11, "bold"), bg=BG,
                                 fg="#444" if i == 0 else "#333", anchor="w")
            name_lbl.pack(side="left", padx=(2, 0))

            # tier badge — after name
            tier_lbl = tk.Label(top, text="", font=("Consolas", 9),
                                 bg=BG, fg="#333", anchor="w")
            tier_lbl.pack(side="left", padx=(4, 0))

            conf_lbl = tk.Label(top, text="", font=("Consolas", 9),
                                 bg=BG, fg="#444", anchor="e")
            conf_lbl.pack(side="right")

            meta_lbl = tk.Label(outer, text="", font=("Consolas", 8),
                                 bg=BG, fg="#445", anchor="w")
            meta_lbl.pack(fill="x", padx=2)

            self._rows.append({
                "rs": rs_lbl, "nodes": nodes_lbl, "name": name_lbl,
                "tier": tier_lbl, "conf": conf_lbl, "meta": meta_lbl,
            })

    def _make_draggable(self):
        self.root.bind("<Button-1>",
            lambda e: (setattr(self, "_ox", e.x), setattr(self, "_oy", e.y)))
        self.root.bind("<B1-Motion>",
            lambda e: self.root.geometry(
                f"+{self.root.winfo_x()+e.x-self._ox}+{self.root.winfo_y()+e.y-self._oy}"))

    # ── mode toggle ───────────────────────────────────────────────────────────

    def _cycle_mode(self):
        self._mode_idx = (self._mode_idx + 1) % len(MODES)
        self.mode_btn.config(text=MODES[self._mode_idx].upper())
        self._redraw()

    @property
    def _mode(self):
        return MODES[self._mode_idx]

    # ── draw ──────────────────────────────────────────────────────────────────

    def _redraw(self):
        entries = []
        for rs in self._history:
            results  = analyze_rs(rs, self._mode)
            exact    = [r for r in results if r["label"] == "EXACT"]
            entries.append((rs, exact))
        self.root.after(0, self._draw, entries)

    def _draw(self, entries):
        for i, row in enumerate(self._rows):
            if i < len(entries):
                rs_val, exact = entries[i]
                alpha = max(0.4, 1.0 - i * 0.15)
                self._fill_row(row, rs_val, exact, alpha)
            else:
                self._clear_row(row, placeholder="Waiting…" if i == 0 else "")

    def _fill_row(self, row, rs_val, exact, alpha=1.0):
        """exact is a list of EXACT-confidence matches (may be empty)."""
        rs_fg   = self._dim("#aaaaaa", alpha)
        meta_fg = self._dim("#445566", alpha)
        dim_fg  = self._dim("#444444", alpha)
        row["rs"].config(text=f"{rs_val:,}", fg=rs_fg)

        if exact:
            m          = exact[0]
            name_color = self._dim(TIER_COLOR.get(m["tier"], "#fff"), alpha)
            tier_color = self._dim(name_color, 0.65)
            row["nodes"].config(text=f"{m['nodes']}×", fg=name_color)
            row["name"].config( text=m["name"],         fg=name_color)
            row["tier"].config( text=f"[{m['tier']}]", fg=tier_color)
            row["conf"].config( text=m["type"],         fg=self._dim("#667788", alpha))

            # additional exact matches (rare) shown on meta line
            if len(exact) > 1:
                others = "  also: " + "  /  ".join(
                    f"{r['nodes']}× {r['name']} [{r['tier']}]" for r in exact[1:]
                )
                row["meta"].config(text=others, fg=meta_fg)
            else:
                row["meta"].config(text="", fg="#333")
        else:
            # logged but no exact match — show RS, no name
            row["nodes"].config(text="",  fg="#333")
            row["name"].config( text="—", fg=dim_fg)
            row["tier"].config( text="",  fg="#333")
            row["conf"].config( text="",  fg="#333")
            row["meta"].config( text="",  fg="#333")

    def _clear_row(self, row, placeholder=""):
        row["rs"].config(   text="",            fg="#333")
        row["nodes"].config(text="",            fg="#333")
        row["name"].config( text=placeholder,   fg="#444" if placeholder else "#333")
        row["tier"].config( text="",            fg="#333")
        row["conf"].config( text="",            fg="#333")
        row["meta"].config( text="",            fg="#333")

    @staticmethod
    def _dim(hex_color, alpha):
        """Blend colour toward background to fade older entries."""
        c = hex_color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        br, bg_, bb = 10, 10, 24
        return f"#{int(r*alpha+br*(1-alpha)):02x}{int(g*alpha+bg_*(1-alpha)):02x}{int(b*alpha+bb*(1-alpha)):02x}"

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

                    if total_rs is not None:
                        results = analyze_rs(total_rs, self._mode)
                        if any(r["label"] == "EXACT" for r in results):
                            if total_rs not in self._history:
                                self._history.appendleft(total_rs)
                                self._redraw()
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
    global _debug_counter
    w, h = img.size
    img  = img.crop((0, int(h * 0.20), int(w * 0.95), int(h * 0.62)))
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
    Return the most plausible RS value from OCR digits.
    Tries stripping 0-2 leading digits (icon noise) and picks the candidate
    with the highest analyze_rs() confidence. If nothing scores well,
    still returns the raw value so it appears in history as unrecognized.
    """
    if len(digits) < 3:
        return None
    best_val, best_conf = None, -1
    for start in range(min(3, len(digits) - 2)):
        try:
            val = int(digits[start:])
        except ValueError:
            continue
        if val < 1000 or val > MAX_RS:
            continue
        results = analyze_rs(val)
        conf = results[0]["confidence"] if results else -1
        if conf > best_conf:
            best_conf, best_val = conf, val
    return best_val if best_conf >= 60 else None


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Overlay().run()
