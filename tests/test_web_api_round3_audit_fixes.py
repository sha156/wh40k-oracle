"""tests/test_web_api_round3_audit_fixes.py — 第 3 轮（web_api/ + 前端）审查 HIGH 的护栏。

对应 docs/superpowers/specs/2026-07-30-audit-round3-web.md §2.1：

- H1 `web_api/codex.py:_min_points` 把 dict 型 points_json 当 list 迭代 ⇒
  全库 1715 个单位的「N 分起」徽章恒为空（图鉴/模拟器/军表三处）。
- H2 `web_api/simulate.py` 数值入参超上限后静默丢弃 ⇒ 端出一份按默认值算的
  `ok=True` 假成功报告，与压根不填时逐位相同。
- H3 `SimResponse.errors` 在整个前端从不被读取，而后端 note 明文写「见 errors」
  ⇒ 第 1 轮 H3 那句面向用户的失败说明在 web 侧可见性为零。

H3 只能做源码级断言：前端没有单测框架（package.json 只有 @playwright/test），
而 e2e 依赖 `next dev`（本机直接 panic，见 CLAUDE.md），pytest 里跑不了浏览器。
既有先例见 tests/test_web_api_stage5_deploy.py（同样以文本方式核对 web/ 下的源文件）。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from web_api.codex import _min_points, list_units
from web_api.simulate import (MODELS_MAX, WEAPON_COUNT_MAX, run_simulation,
                              sanitize_options)

# sanitize_options_ex 是本轮新增的符号，故意**不在模块顶层导入**：顶层导入会让
# 「stash 掉实现」退化成一个 collection ERROR（整模块起不来），看不出哪几条护栏
# 真的在测行为。放进用例内部后，缺实现的那几条各自 FAILED，而两条端到端用例
# （只用 run_simulation）报的是**行为断言失败**，红得有信息量。

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "db" / "wh40k.sqlite"
DRONES = "000000403"      # Tactical Drones：射击阶段武器池只 1 把 ⇒ 自动装配，无需人工 loadout
BROADSIDE = "000000433"   # Broadside Battlesuits：射击 5 把 ⇒ 未给 loadout 必 ambiguous

needs_db = pytest.mark.skipif(not DB_PATH.exists(), reason="wh40k.sqlite 不存在")


# ── H1：点数徽章 ──────────────────────────────────────────────────

def test_min_points_reads_the_dict_shape_actually_stored_in_units():
    """库里 points_json 是 dict 不是 list——按 list 迭代会静默得到 None。

    这是 H1 的最小复现：老实现 `for o in json.loads(pj)` 迭代 dict 拿到的是
    key 字符串，`isinstance(o, dict)` 恒 False ⇒ 恒返回 None。
    """
    real_shape = json.dumps({
        "points": 170,
        "items": [{"line": "1", "desc": "4 models", "cost": 170},
                  {"line": "2", "desc": "8 models", "cost": 320}],
        "mfm": {"points": 170},
    })
    assert _min_points(real_shape) == 170          # 取基准档最小 cost，不取顶层
    # 无 items 时回退顶层 points（与 db_compile.calc_points 同一口径）
    assert _min_points(json.dumps({"points": 95})) == 95
    # 诚实的空：没有点数就是 None，不编造
    assert _min_points(None) is None
    assert _min_points("") is None
    assert _min_points("not json") is None
    assert _min_points(json.dumps({"items": []})) is None


@needs_db
def test_points_badge_is_not_universally_empty_on_the_real_db():
    """全库口径：绝大多数单位应当有点数徽章。老实现在这里是 0 个。"""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT points_json FROM units").fetchall()
    finally:
        conn.close()
    total = len(rows)
    non_null = sum(1 for (pj,) in rows if _min_points(pj) is not None)
    assert total > 1000, "库里单位数异常，用例前提失效"
    # 实测 1711/1715；留余量只断言 95%，但把「恒为 0」这条死线钉死
    assert non_null > total * 0.95, f"有点数的单位只有 {non_null}/{total}"


@needs_db
def test_list_units_renders_the_points_badge():
    """消费方视角：list_units 的 pts 必须真的填出「N 分起」。"""
    units = list_units(DB_PATH, "TAU")
    assert units, "TAU 阵营应有单位"
    with_pts = [u for u in units if u["pts"]]
    assert len(with_pts) > len(units) * 0.9, (
        f"TAU {len(units)} 个单位只有 {len(with_pts)} 个有 pts —— 徽章分支又死了")
    assert all(u["pts"].endswith(" 分起") for u in with_pts)
    assert all(u["pts"].split(" ")[0].isdigit() for u in with_pts)


# ── H2：被丢弃的入参必须交代 ──────────────────────────────────────

def test_over_limit_numeric_inputs_are_disclosed():
    from web_api.simulate import sanitize_options_ex
    raw = {"phase": "shooting", "attacker_models": MODELS_MAX + 100,
           "defender_models": 10}
    out, dropped = sanitize_options_ex(raw)
    # 行为不变：仍然丢弃，不静默钳制（钳了会悄悄改变模拟语义）
    assert "attacker_models" not in out
    assert out["defender_models"] == 10
    # 新增：必须说出来，且说清是哪个键、填的什么、合法范围
    assert len(dropped) == 1
    note = dropped[0]
    assert "attacker_models" in note
    assert str(MODELS_MAX + 100) in note
    assert str(MODELS_MAX) in note


def test_whole_loadout_drop_is_disclosed():
    from web_api.simulate import sanitize_options_ex
    _, dropped = sanitize_options_ex(
        {"loadout": [["Heavy rail rifle", WEAPON_COUNT_MAX + 100]]})
    assert len(dropped) == 1 and "loadout" in dropped[0]
    # 行数超限同样交代
    many = [[f"gun{i}", 1] for i in range(41)]
    _, dropped2 = sanitize_options_ex({"defender_loadout": many})
    assert len(dropped2) == 1 and "defender_loadout" in dropped2[0]


def test_legal_inputs_produce_no_noise():
    """负向成对：合法入参一条也不许报——否则告警会被稀释成噪音。"""
    from web_api.simulate import sanitize_options_ex
    out, dropped = sanitize_options_ex({
        "phase": "melee", "charge": True, "fnp": 5, "n": 10**9,
        "attacker_models": 20, "defender_models": 10, "damage_reduction": 1,
        "seed": 42, "loadout": [["gun", 60]],
    })
    assert dropped == [], dropped
    assert out["attacker_models"] == 20 and out["n"] == 20000
    # 未知键不在白名单登记表里，不算「填了没生效」，保持既有静默丢弃语义
    _, d2 = sanitize_options_ex({"evil_key": "rm -rf"})
    assert d2 == []


def test_sanitize_options_backwards_compatible():
    """老签名行为逐字节不变（只是不再是唯一入口）。"""
    from web_api.simulate import sanitize_options_ex
    raw = {"phase": "melee", "attacker_models": 10**9, "n": 1}
    assert sanitize_options(raw) == sanitize_options_ex(raw)[0]
    assert sanitize_options(None) == {}


@needs_db
def test_run_simulation_never_reports_silent_success_for_dropped_inputs():
    """H2 的端到端复现：填 attacker_models=200 曾端出与不填时逐位相同的 ok=True 报告。"""
    base = {"phase": "shooting", "n": 200}
    clean = run_simulation(DB_PATH, DRONES, DRONES, dict(base))
    over = run_simulation(DB_PATH, DRONES, DRONES,
                          dict(base, attacker_models=MODELS_MAX + 100))
    assert clean is not None and over is not None
    assert clean.ok and over.ok
    # 数值上确实一模一样（入参被丢弃了）——所以更必须有文字交代
    assert over.report is not None and clean.report is not None
    assert over.report.expected_damage == clean.report.expected_damage
    # 对照组：合法入参不产生任何丢弃告警
    assert not any("未生效" in e for e in clean.errors)
    assert "未生效" not in (clean.warning or "")
    # 超限组：errors 有明细、warning 有摘要（成功路径上只有 warning 会被渲染）
    assert any("attacker_models" in e and "未生效" in e for e in over.errors)
    assert "未生效" in (over.warning or "")
    # 原有的引擎 warning 不许被顶掉
    if clean.warning:
        assert clean.warning in (over.warning or "")


@needs_db
def test_dropped_loadout_is_explained_on_the_failure_path():
    """件数超限 ⇒ 整份 loadout 消失 ⇒ 用户拿回一模一样的装配面板，必须说明原因。"""
    resp = run_simulation(DB_PATH, BROADSIDE, DRONES, {
        "phase": "shooting", "n": 200,
        "loadout": [["Heavy rail rifle", WEAPON_COUNT_MAX + 100]]})
    assert resp is not None and not resp.ok
    assert resp.reason == "loadout_required"
    assert any("loadout" in e and "未生效" in e for e in resp.errors)


# ── H3：errors 必须真的渲染到页面上 ───────────────────────────────

def test_simulator_page_renders_response_errors():
    """后端 note 明文写「见 errors」，那这个字段就必须在页面上存在。

    以前 `grep -rn errors web/src` 的唯一命中是 sim.ts 的类型声明本身。
    """
    page = (REPO / "web" / "src" / "app" / "simulator" / "page.tsx").read_text(
        encoding="utf-8")
    assert "resp?.errors" in page or "resp.errors" in page, (
        "simulator 页没有读 resp.errors")
    assert "errors.map(" in page, "读了但没渲染成列表"


def test_errors_field_is_not_declaration_only_in_frontend():
    """全前端扫描：errors 不能只活在类型声明里。"""
    src = REPO / "web" / "src"
    hits = []
    for p in sorted(src.rglob("*.ts")) + sorted(src.rglob("*.tsx")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "errors" in line:
                hits.append((p.relative_to(src).as_posix(), i, line.strip()))
    decl_only = [h for h in hits if h[0] == "lib/sim.ts"]
    assert len(hits) > len(decl_only), (
        "errors 在前端只出现在契约声明里，没有任何一处渲染它：\n"
        + "\n".join(f"{f}:{i}: {t}" for f, i, t in hits))
