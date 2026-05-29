RESOURCES = [
    {"rs": 2000, "name": "Debris",        "type": "Debris",         "tier": "C", "notes": "Not minable."},
    {"rs": 3170, "name": "Quantainium",  "type": "Volatile Gem",   "tier": "S", "notes": "Highly volatile. Sell FAST after mining."},
    {"rs": 3185, "name": "Stileron",     "type": "Gem",            "tier": "A", "notes": "Rare gem deposit."},
    {"rs": 3200, "name": "Savrilium",    "type": "Gem",            "tier": "A", "notes": "High-value gem."},
    {"rs": 3370, "name": "Ouratite",     "type": "Gem",            "tier": "A", "notes": "Sought for crafting."},
    {"rs": 3385, "name": "Riccite",      "type": "Mineral",        "tier": "B", "notes": "Mid-tier mineral."},
    {"rs": 3400, "name": "Lindinium",    "type": "Mineral",        "tier": "B", "notes": "Industrial mineral."},
    {"rs": 3540, "name": "Beryl",        "type": "Gem",            "tier": "A", "notes": "Gemstone deposit."},
    {"rs": 3555, "name": "Taranite",     "type": "Mineral",        "tier": "A", "notes": "High-value mineral."},
    {"rs": 3570, "name": "Borase",       "type": "Mineral",        "tier": "B", "notes": "Common mid-tier."},
    {"rs": 3585, "name": "Gold",         "type": "Precious Metal", "tier": "A", "notes": "Precious metal. Strong market."},
    {"rs": 3600, "name": "Bexalite",     "type": "Mineral",        "tier": "S", "notes": "Top-tier. Highly sought."},
    {"rs": 3825, "name": "Laranite",     "type": "Mineral",        "tier": "A", "notes": "Dense, valuable mineral."},
    {"rs": 3840, "name": "Aslarite",     "type": "Mineral",        "tier": "B", "notes": "Mid-range deposit."},
    {"rs": 3855, "name": "Titanium",     "type": "Metal",          "tier": "B", "notes": "Industrial metal."},
    {"rs": 3870, "name": "Tungsten",     "type": "Metal",          "tier": "B", "notes": "Heavy industrial."},
    {"rs": 3885, "name": "Agricium",     "type": "Mineral",        "tier": "A", "notes": "Crafting resource."},
    {"rs": 3900, "name": "Torite",       "type": "Mineral",        "tier": "B", "notes": "Common industrial."},
    {"rs": 4180, "name": "Hephestanite","type": "Mineral",         "tier": "B", "notes": "Moderate value."},
    {"rs": 4195, "name": "Tin",          "type": "Metal",          "tier": "C", "notes": "Common base metal."},
    {"rs": 4210, "name": "Quartz",       "type": "Mineral",        "tier": "C", "notes": "Very common."},
    {"rs": 4225, "name": "Corundum",     "type": "Mineral",        "tier": "C", "notes": "Abrasive mineral."},
    {"rs": 4240, "name": "Copper",       "type": "Metal",          "tier": "C", "notes": "Common metal."},
    {"rs": 4255, "name": "Silicon",      "type": "Mineral",        "tier": "C", "notes": "Electronics base."},
    {"rs": 4270, "name": "Iron",         "type": "Metal",          "tier": "C", "notes": "Most common metal."},
    {"rs": 4285, "name": "Aluminium",    "type": "Metal",          "tier": "C", "notes": "Lightweight metal."},
    {"rs": 4300, "name": "Ice",          "type": "Volatile",       "tier": "C", "notes": "FPS/surface deposits."},
]

# Mode multipliers: the HUD RS reading is (base_rs * multiplier) per node
MODE_MULTIPLIERS = {
    "ship":   1,
    "fps":    3000,
    "ground": 4000,
}


def analyze_rs(total_rs: int, mode: str = "ship") -> list[dict]:
    """
    For each resource calculate node count + confidence matching the web app formula.
    remPct = remainder / base_rs  (normalised per-node, not per total)
    confidence = max(0, round((1 - min(remPct/0.15, 1)) * 100))
    Sorted: remPct asc, then nodes asc (smaller clusters win ties).
    """
    mult = MODE_MULTIPLIERS.get(mode, 1)
    results = []

    for r in RESOURCES:
        base      = r["rs"] * mult
        nodes     = max(1, round(total_rs / base))
        expected  = nodes * base
        remainder = abs(total_rs - expected)
        rem_pct   = remainder / base                       # normalised by one node RS
        confidence = max(0, round((1 - min(rem_pct / 0.15, 1)) * 100))

        if   remainder == 0:     label = "EXACT"
        elif rem_pct   < 0.05:   label = "CLOSE"
        elif rem_pct   < 0.15:   label = "APPROX"
        else:                    label = "ROUGH"

        results.append({
            **r,
            "nodes":       nodes,
            "confidence":  confidence,
            "remainder":   remainder,
            "rem_pct":     rem_pct,
            "expected_rs": expected,
            "label":       label,
        })

    results.sort(key=lambda x: (x["rem_pct"], x["nodes"]))
    exact_count = sum(1 for r in results if r["label"] == "EXACT")
    return results[:max(exact_count, 5)]
