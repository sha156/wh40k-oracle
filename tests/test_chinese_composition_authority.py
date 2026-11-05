"""Frozen community prices cannot contradict or omit authoritative price tiers."""
from __future__ import annotations

import json
import sqlite3

import pytest

from web_api.codex import _load_zh_composition


def composition(tmp_path, lines, costs, *, descriptions=None, revised=False):
    with sqlite3.connect(tmp_path / "composition.sqlite") as c:
        c.execute("CREATE TABLE unit_zh_detail(canonical_id TEXT,intro_json TEXT)")
        blocks = [{"type": "h3", "content": "单位构成"}] + [
            {"type": "text", "content": [{"text": line}]} for line in lines]
        c.execute("INSERT INTO unit_zh_detail VALUES ('one',?)", (json.dumps(blocks),))
        if revised:
            c.execute("CREATE TABLE official_rule_revisions(unit_id TEXT,source_date TEXT)")
            c.execute("INSERT INTO official_rule_revisions VALUES ('one','2026-09-30')")
        descriptions = descriptions or ["1 model"] * len(costs)
        return _load_zh_composition(c, "one", [
            {"cost": cost, "desc": desc} for cost, desc in zip(costs, descriptions)])


def test_guilliman_frozen_340_cannot_override_official_355(tmp_path):
    assert composition(tmp_path, ["唯一的独特模型，340 分，并且必须作为军队主将"], [355]) == []


def test_matching_chinese_quantifier_is_retained(tmp_path):
    lines = ["1 艘毁灭炮艇，95分"]
    assert composition(tmp_path, lines, [95]) == lines


@pytest.mark.parametrize("lines,costs", [
    (["5 个模型，100分"], [100, 200]),
    (["5 个模型，100分", "10 个模型，100分"], [100, 200]),
    (["1 个模型，55分"], [55, 55]),
    (["1 个模型"], [55]),
    (["1 个模型，55分"], []),
    (["1 个模型，55分"], [True]),
])
def test_missing_or_duplicate_tiers_cannot_pass_cost_set_membership(tmp_path, lines, costs):
    assert composition(tmp_path, lines, costs) == []


def test_matching_thousands_price_is_retained(tmp_path):
    lines = ["1 个模型，1,100 pts"]
    assert composition(tmp_path, lines, [1100]) == lines


def test_multi_tier_composition_uses_canonical_options(tmp_path):
    lines = ["1 个模型，1,100 pts", "2 个模型，2200 points"]
    assert composition(tmp_path, lines, [1100, 2200],
                       descriptions=["1 model", "2 models"]) == []


def test_crossed_model_count_prices_cannot_pass(tmp_path):
    assert composition(tmp_path, ["5 个模型，200分", "10 个模型，100分"], [100, 200],
                       descriptions=["5 models", "10 models"]) == []


@pytest.mark.parametrize("line,description", [
    ("5 个模型，100分", "10 models"),
    ("1 个模型，100分", "1 model (Assigned Agent)"),
    ("1 个模型，100分", ""),
    ("独特模型，100分", "1 model"),
    ("1 foo，100分", "1 model"),
    ("1 个队长和 4 个保镖，100分", "1 model"),
    ("1 个模型，100分，可以增加1个模型", "1 model"),
])
def test_quantity_or_context_ambiguity_uses_canonical_options(tmp_path, line, description):
    assert composition(tmp_path, [line], [100], descriptions=[description]) == []


def test_localized_authoritative_count_is_accepted(tmp_path):
    lines = ["3 个模型，120分"]
    assert composition(tmp_path, lines, [120], descriptions=["3 个模型"]) == lines


def test_unit_rule_revision_still_invalidates_community_composition(tmp_path):
    assert composition(tmp_path, ["1 个模型，55分；旧编制限制"], [55], revised=True) == []
