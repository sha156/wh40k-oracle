"""⚔️ 模拟器面板（P5-d）——engines/simulator 的 Streamlit 薄壳。

铁律（spec 五节）：本模块**不含任何模拟逻辑**，只调 `agent.tools.simulate_combat`
（已含实体解析 + 装配 + 三失败路径）并把结果渲染成图表/表格/诚实披露。
「面板数字 == CLI 数字」——两者共用同一个 simulate_combat，故必然一致。

图表用 Streamlit 原生 `st.bar_chart`（零额外依赖，避开 matplotlib 字体坑）。
可脱 Streamlit 单测的核心是 `kill_distribution_series` / `funnel_rows`（纯数据，不碰 st）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


# ── 纯函数（可脱 Streamlit 单测）───────────────────────────────
def kill_distribution_series(report: Dict[str, Any]) -> List[Tuple[int, float]]:
    """report → [(击杀数, 概率)] 升序。histogram 键可能是 int 或 JSON 往返后的 str。"""
    dist = report.get("distribution", {}) or {}
    hist = dist.get("histogram", {}) or {}
    out: List[Tuple[int, float]] = []
    for k, v in hist.items():
        try:
            out.append((int(k), float(v)))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda t: t[0])
    return out


def funnel_rows(report: Dict[str, Any]) -> List[Tuple[str, float]]:
    """漏斗表行（顺序固定），供 st.table / 单测。"""
    f = report.get("funnel", {}) or {}
    labels = [("attacks", "攻击数"), ("hits", "命中"), ("wounds", "致伤"),
              ("unsaved", "过保/致命"), ("damage", "有效伤害"), ("kills", "击杀")]
    return [(zh, float(f.get(en, 0.0))) for en, zh in labels]


def percentile_caption(report: Dict[str, Any]) -> str:
    """P10/P50/P90 击杀分位说明文本。"""
    d = report.get("distribution", {}) or {}
    return (f"击杀分位 P10 / P50 / P90 = "
            f"{d.get('p10', 0):g} / {d.get('p50', 0):g} / {d.get('p90', 0):g}")


# ── Streamlit 壳（需 script run context，不进单测）──────────────
def _render_report(st, report: Dict[str, Any], title: str) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("期望伤害", f"{report.get('expected_damage', 0):.2f}")
    c2.metric("期望击杀", f"{report.get('expected_kills', 0):.2f}")
    c3.metric("团灭率", f"{report.get('wipe_probability', 0) * 100:.1f}%")

    series = kill_distribution_series(report)
    if series:
        import pandas as pd
        df = pd.DataFrame({"概率": [p for _, p in series]},
                          index=[k for k, _ in series])
        df.index.name = "击杀模型数"
        st.bar_chart(df, color="#8a1c1c")
    st.caption(percentile_caption(report))

    st.caption("阶段漏斗")
    rows = funnel_rows(report)
    st.table({"阶段": [r[0] for r in rows], "期望": [round(r[1], 2) for r in rows]})

    eff = report.get("efficiency") or {}
    if eff:
        st.caption(f"性价比（{eff.get('points')} 点）：每 100 点 "
                   f"伤害 {eff.get('damage_per_100')} / 击杀 {eff.get('kills_per_100')}")

    if report.get("modeled_effects"):
        st.success("计入词条：" + "、".join(report["modeled_effects"]))
    if report.get("not_modeled"):
        with st.expander("未建模（诚实披露）", expanded=False):
            for nm in report["not_modeled"]:
                st.markdown(f"- {nm}")
    if report.get("bias_notes"):
        with st.expander("系统性偏差声明", expanded=False):
            for b in report["bias_notes"]:
                st.markdown(f"- {b}")


def _options_from_inputs(st) -> Dict[str, Any]:
    """从控件 session_state 读出 simulate_combat 的 options。

    loadout 畸形时抛 LoadoutParseError（评审 H11）——调用方（render_simulator_panel）
    捕获后走 st.error 友好提示，不让裸 traceback 冲垮面板。
    """
    from engines.simulator.cli import _clean_options, _parse_loadout

    opts: Dict[str, Any] = {
        "phase": st.session_state.get("sim_phase", "shooting"),
        "charge": st.session_state.get("sim_charge", False),
        "half_range": st.session_state.get("sim_half", False),
        "cover": st.session_state.get("sim_cover", False),
        "stationary": st.session_state.get("sim_stationary", False),
        "long_range": st.session_state.get("sim_long", False),
        "indirect": st.session_state.get("sim_indirect", False),
        "stealth": st.session_state.get("sim_stealth", False),
        "go_to_ground": st.session_state.get("sim_gtg", False),
        "smokescreen": st.session_state.get("sim_smoke", False),
        "n": int(st.session_state.get("sim_n", 8000)),
        "seed": int(st.session_state.get("sim_seed", 1234)),
    }
    fnp = int(st.session_state.get("sim_fnp", 0) or 0)
    if fnp:
        opts["fnp"] = fnp
    dr = int(st.session_state.get("sim_dr", 0) or 0)
    if dr:
        opts["damage_reduction"] = dr
    lo = _parse_loadout(st.session_state.get("sim_loadout", "") or "")
    if lo:
        opts["loadout"] = lo
    dlo = _parse_loadout(st.session_state.get("sim_def_loadout", "") or "")
    if dlo:
        opts["defender_loadout"] = dlo
    # 评审 H10：只滤 None/False 本身，绝不滤 0（0 == False 会把 seed=0 静默丢回默认 1234）
    return _clean_options(opts)


def render_simulator_panel(st) -> None:
    """在传入的 Streamlit 命名空间下渲染模拟器面板。app.py 侧边栏切到「模拟器」时调用。"""
    st.markdown("### ⚔️ 蒙特卡洛对战模拟器")
    st.caption("十版逐骰模拟｜攻方打守方 N 次 → 期望伤害/击杀/团灭率 + 阶段漏斗 + 性价比 + 诚实披露。"
               "数字与 CLI 完全一致（共用同一引擎）。")

    with st.form("sim_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("攻方单位（中/英/俗名）", key="sim_attacker",
                          placeholder="如：兽人 Warboss / Boyz")
            st.text_input("攻方装配 loadout（多模型必填）", key="sim_loadout",
                          placeholder='武器名:数量,... 如 Shoota:9,Slugga:1')
        with col_b:
            st.text_input("守方单位", key="sim_defender",
                          placeholder="如：Intercessor Squad")
            st.text_input("守方装配（填了则做幸存反打）", key="sim_def_loadout",
                          placeholder="留空=单向模拟")

        st.selectbox("阶段", ["shooting", "melee"], key="sim_phase")
        cols = st.columns(4)
        cols[0].checkbox("冲锋", key="sim_charge")
        cols[1].checkbox("半射程", key="sim_half")
        cols[2].checkbox("目标在掩体", key="sim_cover")
        cols[3].checkbox("本方静止", key="sim_stationary")
        cols2 = st.columns(4)
        cols2[0].checkbox("远距离(12/24\"外)", key="sim_long")
        cols2[1].checkbox("间接火力", key="sim_indirect")
        cols2[2].checkbox("守方 Stealth", key="sim_stealth")
        cols2[3].checkbox("守方卧倒(掩体+6++)", key="sim_gtg")

        cols3 = st.columns(4)
        cols3[0].checkbox("守方烟幕(掩体+潜行)", key="sim_smoke")
        cols3[1].number_input("守方 FNP X+（0=关）", 0, 6, 0, key="sim_fnp")
        cols3[2].number_input("守方减伤（0=关）", 0, 3, 0, key="sim_dr")
        cols3[3].number_input("迭代 n", 1000, 50000, 8000, step=1000, key="sim_n")
        st.number_input("随机种子", 0, 999999, 1234, key="sim_seed")

        submitted = st.form_submit_button("开始模拟", type="primary")

    if not submitted:
        return

    attacker = (st.session_state.get("sim_attacker") or "").strip()
    defender = (st.session_state.get("sim_defender") or "").strip()
    if not attacker or not defender:
        st.warning("请填写攻方与守方单位名。")
        return

    # 评审 H11：loadout 畸形 → st.error 友好提示并返回，不让裸 traceback 冲垮面板
    from engines.simulator.cli import LoadoutParseError
    try:
        options = _options_from_inputs(st)
    except LoadoutParseError as exc:
        st.error(f"装配 loadout 格式错误：{exc}")
        return

    from agent.tools import simulate_combat
    with st.spinner("逐骰模拟中…"):
        res = simulate_combat(attacker, defender, options)

    if not res.get("ok"):
        reason = res.get("reason")
        st.error(res.get("note", "模拟未完成"))
        if reason == "ambiguous" and res.get("candidates"):
            st.info("候选单位（请改用其中一个精确名再试）：" + "、".join(res["candidates"][:10]))
        elif reason == "loadout_required" and res.get("weapon_pool"):
            st.info("该单位武器为选项池，请在「攻方装配」填写 loadout。可选武器：\n\n"
                    + "、".join(res["weapon_pool"]))
            if res.get("model_tiers"):
                st.caption("模型档位：" + str(res["model_tiers"]))
        return

    st.success(f"✅ {res['attacker']} 打 {res['defender']}（{res['phase']}）")
    if res.get("warning"):
        st.warning(res["warning"])

    _render_report(st, res["report"], "击杀数分布")

    rev = res["report"].get("reverse")
    if rev:
        st.divider()
        st.markdown("#### ↩️ 守方幸存者反打")
        _render_report(st, rev, "反打·击杀数分布")

    # surface：守方防守技能提示 + 阵营分队名（诚实披露，未自动施加）。
    # 评审 M：这些技能没有自动接线（留待 P7），提示用户在上方手动开关/数值框自行填数。
    toggles = res.get("defender_toggles") or []
    if toggles:
        st.info("检测到守方防守技能（仅提示，本次未计入）：如适用，请在上方手动开关/数值框"
                "自行填入对应数值后重跑（自动接线留待 P7）：\n\n"
                + "\n".join(f"- **{t['name']}**：{t['note']}" for t in toggles))
    fo = res.get("faction_options") or {}
    if fo.get("detachments"):
        st.caption(f"守方阵营「{fo.get('faction_name')}」的分队（各含未建模的分队规则）："
                   + "、".join(fo["detachments"][:12])
                   + ("…" if len(fo["detachments"]) > 12 else ""))
