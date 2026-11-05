"""Model-free checks of official named-model sizes shared with roster pricing."""
import json

import pytest

from engines.simulator.assembly import default_model_count, parse_model_tiers


@pytest.mark.parametrize("descriptions, counts", [
    (["10 gretchin", "20 gretchin"], [10, 20]),
    (["1 sword brother, 4 neophytes, 5 initiates", "1 sword brother, 8 neophytes, 11 initiates"], [10, 20]),
    (["3 Wolf Guard Headtakers", "3 wolf guard headtakers, 3 hunting wolves"], [3, 6]),
])
def test_named_compositions_keep_default_and_available_sizes(descriptions, counts):
    points = json.dumps({"items": [{"desc": d, "cost": 100 + i} for i, d in enumerate(descriptions)]})
    assert [tier["models"] for tier in parse_model_tiers(points)] == counts
    assert default_model_count(points) == counts[0]


def test_equipment_surcharges_do_not_become_one_model_unit_tiers():
    points = json.dumps({"items": [
        {"desc": "+ 1 model with special weapon", "cost": 10},
        {"desc": "5 models", "cost": 80},
        {"desc": "per model", "cost": 5},
    ]})
    assert parse_model_tiers(points) == [{"models": 5, "cost": 80}]
    assert default_model_count(points) == 5
