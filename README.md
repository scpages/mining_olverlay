# SC Mining Overlay

A real-time Star Citizen mining assistant that reads the RS (resistance) value from your screen and identifies which resource it is, how many nodes are in the cluster, and how confident the match is.

Inspired by [rainbowramen.github.io/sc-mining-hud](https://rainbowramen.github.io/sc-mining-hud/) — this is a live overlay version that reads the HUD automatically instead of requiring manual input.

---

## How it works

1. Captures a small region of your screen where the RS value is displayed
2. Runs OCR (Tesseract) to read the number
3. For each resource, calculates: `nodes = round(total_RS / base_RS)`
4. Ranks results by how cleanly the RS divides (confidence %)
5. Displays top match + alternatives on a second monitor overlay

### Confidence levels

| Label  | Condition         | Meaning                          |
|--------|-------------------|----------------------------------|
| EXACT  | Perfect division  | High certainty                   |
| CLOSE  | < 5% off one node | Very likely correct              |
| APPROX | < 15% off        | Possible — check alternatives    |
| ROUGH  | ≥ 15% off        | Mixed ore or ambiguous reading   |

---

## Requirements

- Windows 10/11
- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed to `C:\Program Files\Tesseract-OCR\`

---

## Setup

```
setup.bat
```

Or manually:

```
pip install -r requirements.txt
```

Then install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki

---

## Usage

```
run.bat
```

Or:

```
python main.py
```

The overlay appears on your **second monitor**. Drag it anywhere by clicking and dragging. Click the mode button to switch between **SHIP / FPS / GROUND** mining contexts.

---

## Configuration

At the top of `main.py`:

```python
GAME_MONITOR    = 1     # which monitor the game runs on (1 = primary)
OVERLAY_MONITOR = 2     # which monitor for the overlay

# Region where the RS number appears — as fraction of screen size
# Calibrated for 2560×1440. Run debug_capture.py to re-tune for your resolution.
REGION_X = 0.459
REGION_Y = 0.367
REGION_W = 0.086
REGION_H = 0.042

POLL_INTERVAL = 0.5   # seconds between screen captures
```

If the region is wrong for your resolution, run:

```
python debug_capture.py
```

It will countdown 5 seconds so you can switch to the game, then capture the region and save step-by-step debug images so you can see what OCR is reading.

---

## Mining modes

| Mode   | Base RS multiplier | Use for                        |
|--------|--------------------|--------------------------------|
| SHIP   | ×1                 | Ship mining (Prospector, MOLE) |
| FPS    | ×3000              | FPS hand mining                |
| GROUND | ×4000              | Ground vehicle mining          |

---

## Resource table

| RS   | Resource      | Type          | Tier |
|------|--------------|---------------|------|
| 3170 | Quantainium  | Volatile Gem  | S    |
| 3185 | Stileron     | Gem           | A    |
| 3200 | Savrilium    | Gem           | A    |
| 3370 | Ouratite     | Gem           | A    |
| 3385 | Riccite      | Mineral       | B    |
| 3400 | Lindinium    | Mineral       | B    |
| 3540 | Beryl        | Gem           | A    |
| 3555 | Taranite     | Mineral       | A    |
| 3570 | Borase       | Mineral       | B    |
| 3585 | Gold         | Precious Metal| A    |
| 3600 | Bexalite     | Mineral       | S    |
| 3825 | Laranite     | Mineral       | A    |
| 3840 | Aslarite     | Mineral       | B    |
| 3855 | Titanium     | Metal         | B    |
| 3870 | Tungsten     | Metal         | B    |
| 3885 | Agricium     | Mineral       | A    |
| 3900 | Torite       | Mineral       | B    |
| 4180 | Hephestanite | Mineral       | B    |
| 4195 | Tin          | Metal         | C    |
| 4210 | Quartz       | Mineral       | C    |
| 4225 | Corundum     | Mineral       | C    |
| 4240 | Copper       | Metal         | C    |
| 4255 | Silicon      | Mineral       | C    |
| 4270 | Iron         | Metal         | C    |
| 4285 | Aluminium    | Metal         | C    |
| 4300 | Ice          | Volatile      | C    |

RS values from SC 4.7 PTU community data.
