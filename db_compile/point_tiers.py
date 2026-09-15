"""Official model sizes and repeat-unit tiers, excluding equipment surcharges."""
import re


def model_count(description):
    plain = re.fullmatch(r"(\d+) models?", description.strip(), re.I)
    if plain:
        return int(plain[1])
    # Official mixed-model sizes enumerate every component. Never treat a
    # leading '+ 1' optional model or a 'per Weapon' surcharge as a unit size.
    parts = re.split(r",\s*", description.strip())
    if all(re.fullmatch(r"\d+ [A-Za-z][A-Za-z '’\-]+", p) for p in parts):
        return sum(int(p.split()[0]) for p in parts)
    return None


def minimum_unit_cost(items):
    costs = [i["cost"] for i in items if isinstance(i, dict)
             and isinstance(i.get("cost"), int) and model_count(str(i.get("desc", ""))) is not None]
    return min(costs) if costs else None


def tier_applies(tier, occurrence):
    if tier == "YOUR UNIT COSTS":
        return True
    match = re.fullmatch(r"YOUR (\d+)(?:ST|ND|RD|TH)(?: TO (\d+)(?:ST|ND|RD|TH))?( \+)? UNITS? COSTS?", tier)
    if not match:
        raise ValueError("Unrecognized official repeat-unit tier: " + tier)
    low = int(match[1])
    high = float("inf") if match[3] else int(match[2] or low)
    return low <= occurrence <= high
