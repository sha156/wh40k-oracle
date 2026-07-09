"""P4-a 解析层单测：骰子 / 属性归一 / 词条分词的边界。

覆盖实测脏值：4D6 / D6+8 / 2D3+3、6" / 20+" / 4* / 5* / - / N/A、-0 AP、
词条骰子参数（sustained hits d3）、anti-X 多词目标（anti-epic hero 2+）、未识别专属词条。
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.simulator.contracts import DiceExpr
from engines.simulator.parse import (
    ParseError,
    expected_dice,
    norm_stat_int,
    parse_ap,
    parse_dice,
    parse_keyword_token,
    sample_dice,
    tokenize_keywords,
)


# ---- 1. 骰子解析器 ----
@pytest.mark.parametrize("text,expected", [
    ("5", DiceExpr(0, 0, 5)),
    ("0", DiceExpr(0, 0, 0)),
    ("-1", DiceExpr(0, 0, -1)),
    ("D6", DiceExpr(1, 6, 0)),
    ("D3", DiceExpr(1, 3, 0)),
    ("D6+3", DiceExpr(1, 6, 3)),
    ("2D6", DiceExpr(2, 6, 0)),
    ("4D6", DiceExpr(4, 6, 0)),      # spec 声称 N≤3，实测有 4D6
    ("2D3+3", DiceExpr(2, 3, 3)),
    ("D6+8", DiceExpr(1, 6, 8)),     # K 上限压线
    ("d6", DiceExpr(1, 6, 0)),       # 小写
])
def test_parse_dice(text, expected):
    assert parse_dice(text) == expected


@pytest.mark.parametrize("bad", ["abc", "", "D", "6+", "D6+D3", None])
def test_parse_dice_raises(bad):
    with pytest.raises(ParseError):
        parse_dice(bad)


@pytest.mark.parametrize("text,exp", [
    ("3", 3.0), ("D6", 3.5), ("D3", 2.0), ("D6+3", 6.5),
    ("2D6", 7.0), ("2D3+3", 7.0),
])
def test_expected_dice(text, exp):
    assert expected_dice(parse_dice(text)) == pytest.approx(exp)


def test_sample_dice_bounds_and_mean():
    rng = np.random.default_rng(42)
    arr = sample_dice(parse_dice("D6+3"), rng, 20000)
    assert arr.shape == (20000,)
    assert arr.min() >= 4 and arr.max() <= 9        # D6+3 ∈ [4,9]
    assert arr.mean() == pytest.approx(6.5, abs=0.1)


def test_sample_dice_constant():
    rng = np.random.default_rng(0)
    arr = sample_dice(DiceExpr(0, 0, 3), rng, (5, 4))
    assert arr.shape == (5, 4) and (arr == 3).all()


# ---- 2. 属性归一器 ----
@pytest.mark.parametrize("value,exp", [
    ('6"', 6), ('4+', 4), ('20+"', 20), ('4*', 4), ('5*', 5),
    ('4', 4), ('5', 5), ('6', 6), ('-', None), ('N/A', None),
    ('?', None), ('', None), (None, None),
])
def test_norm_stat_int(value, exp):
    assert norm_stat_int(value) == exp


@pytest.mark.parametrize("value,exp", [
    ('0', 0), ('-1', -1), ('-2', -2), ('-3', -3),
    ('-', 0), ('-0', 0), ('', 0), (None, 0),
])
def test_parse_ap(value, exp):
    assert parse_ap(value) == exp


# ---- 3. 词条分词器 ----
def test_tokenize_warboss_kombi():
    parsed, unknown = tokenize_keywords(
        '["anti-infantry 4+, devastating wounds, rapid fire 1"]')
    assert unknown == []
    names = [p.name for p in parsed]
    assert names == ["anti", "devastating_wounds", "rapid_fire"]
    assert parsed[0].params == ("infantry", 4)
    assert parsed[2].params == (1,)
    assert all(p.recognized for p in parsed)


def test_tokenize_dice_param():
    parsed, _ = tokenize_keywords('["sustained hits d3"]')
    assert parsed[0].name == "sustained_hits"
    assert parsed[0].params == (DiceExpr(1, 3, 0),)


def test_tokenize_rapid_fire_dice():
    parsed, _ = tokenize_keywords('["rapid fire d6+3"]')
    assert parsed[0].name == "rapid_fire"
    assert parsed[0].params == (DiceExpr(1, 6, 3),)


def test_tokenize_anti_multiword_target():
    parsed, _ = tokenize_keywords('["anti-epic hero 2+"]')
    assert parsed[0].name == "anti"
    assert parsed[0].params == ("epic hero", 2)


def test_tokenize_flag_keywords():
    parsed, unknown = tokenize_keywords('["ignores cover, pistol, torrent"]')
    assert [p.name for p in parsed] == ["ignores_cover", "pistol", "torrent"]
    assert unknown == []


def test_tokenize_unknown_kept_not_dropped():
    parsed, unknown = tokenize_keywords('["bubblechukka"]')
    assert len(parsed) == 1
    assert parsed[0].name == "bubblechukka"
    assert parsed[0].recognized is False
    assert unknown == ["bubblechukka"]


@pytest.mark.parametrize("value", [None, "", "null"])
def test_tokenize_empty(value):
    parsed, unknown = tokenize_keywords(value)
    assert parsed == [] and unknown == []


def test_parse_keyword_token_twin_linked():
    pk = parse_keyword_token("twin-linked")
    assert pk.name == "twin_linked" and pk.recognized and pk.params == ()
