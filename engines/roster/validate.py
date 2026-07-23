"""engines/roster/validate.py — 编制约束校验（P6-PR1b 核心）。

点数 + 编制约束（warlord / Rule of Three / 强化）逐条查 → ValidationReport。
诚实降级红线：数据缺口（无 detachment / 无强化数据）标 surfaced_only=True，绝不默认判通过。
"""
from __future__ import annotations

from collections import Counter
from typing import List, Optional, Set

from engines.roster.compose_rules import (MAX_ENHANCEMENTS, RULE_OF_THREE,
                                          SIZE_LIMITS, datasheet_copy_limit,
                                          is_character, is_epic_hero,
                                          size_limit, unit_keywords_bulk)
from engines.roster.contracts import (ERROR, WARN, Roster, ValidationIssue,
                                      ValidationReport)
from engines.roster.points import recompute, total_points


def _valid_enhancement_names(db_path, detachment_id: Optional[str]) -> Optional[Set[str]]:
    """该 detachment 的合法强化名集合；无 detachment 或无数据 → None（触发 surface）。"""
    if not detachment_id:
        return None
    from db_compile.enhancements import list_for_detachment
    names = {e["name"] for e in list_for_detachment(db_path, detachment_id)}
    return names or None


def validate(db_path, roster: Roster) -> ValidationReport:
    """军表 → 合法性报告。内部先 recompute（点数为权威真源），再逐条查编制约束。

    总分 = 单位点数 + 强化点数——MFM 给强化列点数的唯一目的就是计入军队总分，
    漏计会把压线超分表判合法（gnhf 审查模块 3 F1 HIGH）。
    """
    priced = recompute(db_path, roster)
    issues: List[ValidationIssue] = []
    limit = size_limit(priced.size)
    enh_points, enh_point_issues = _enhancement_points(db_path, priced)
    total = total_points(priced) + enh_points
    issues.extend(enh_point_issues)
    # 一次性取全部单位关键词（避免按单位 N+1 连库）；不在返回里的 id = 单位不在库
    kw_map = unit_keywords_bulk(db_path, [u.canonical_id for u in priced.units])

    # ⓪′ 未知单位：只说系统知道的事实，跳过关键词/档位类断言——对不存在的单位断言
    # 「非 CHARACTER」「模型数不在档位内」全是编造（gnhf 审查模块 3 F3，诚实降级红线）。
    # 触发面：DB 重建/单位下线后，前端 localStorage 里的旧军表带过期 id。
    unknown_ids = {u.canonical_id for u in priced.units if u.canonical_id not in kw_map}
    for cid in sorted(unknown_ids):
        name = next(u.name_en for u in priced.units if u.canonical_id == cid)
        issues.append(ValidationIssue(
            "unit_not_found", WARN,
            f"{name}（id {cid}）不在单位库中（可能已随库重建下线），"
            "点数与编制约束均未校验",
            surfaced_only=True))

    # ⓪ 未知规模档：显式 surface（size_limit 会回退 2000，但不静默——否则报错消息会撒谎）
    size_label = priced.size
    if priced.size not in SIZE_LIMITS:
        issues.append(ValidationIssue(
            "unknown_size", WARN,
            f"未知规模档「{priced.size}」，按 strike_force {limit} 计",
            surfaced_only=True))
        size_label = f"strike_force({limit})"

    # ① 总分 ≤ 上限
    if total > limit:
        issues.append(ValidationIssue(
            "points_over", ERROR,
            f"总分 {total} 超出 {size_label} 上限 {limit}（超 {total - limit}）",
            anchor="11版 军表构筑·点数上限"))

    # ② 无法定价的单位（模型数不在档位内）—— warn，不静默计 0。
    # 未知单位跳过：它没定上价是因为不在库，「模型数不在档位内」的归因是编造的
    for u in priced.units:
        if u.points is None and u.canonical_id not in unknown_ids:
            issues.append(ValidationIssue(
                "unit_unpriced", WARN,
                f"{u.name_en}（{u.models} 模型）无法定价：该模型数不在点数档位内，未计入总分",
                surfaced_only=True))

    # ③ warlord：恰好 1 个，且须 CHARACTER
    warlords = [u for u in priced.units if u.is_warlord]
    if len(warlords) != 1:
        issues.append(ValidationIssue(
            "warlord_count", ERROR,
            f"须恰好 1 个 WARLORD，当前 {len(warlords)} 个",
            anchor="11版 军表构筑·Warlord"))
    for w in warlords:
        if w.canonical_id in unknown_ids:
            continue    # 单位不在库，是否 CHARACTER 无从判定（已由 unit_not_found 披露）
        if not is_character(kw_map.get(w.canonical_id, set())):
            issues.append(ValidationIssue(
                "warlord_not_character", ERROR,
                f"{w.name_en} 非 CHARACTER，不能任 WARLORD",
                anchor="11版 军表构筑·Warlord"))

    # ④ Rule of Three：同 datasheet 份数上限（battleline/DT 豁免、epic hero≤1）
    counts = Counter(u.canonical_id for u in priced.units)
    for cid, n in counts.items():
        if cid in unknown_ids:
            continue    # 关键词未知 → 豁免与否无从判定（已由 unit_not_found 披露）
        kw = kw_map.get(cid, set())
        cap = datasheet_copy_limit(kw)
        name = next(u.name_en for u in priced.units if u.canonical_id == cid)
        if cap is not None and n > cap:
            label = "EPIC HERO 至多 1 份" if is_epic_hero(kw) else f"至多 {cap} 份"
            issues.append(ValidationIssue(
                "rot_exceeded", ERROR,
                f"{name} 选了 {n} 份，超编（{label}）",
                anchor="11版 军表构筑·Rule of Three"))
        elif cap is None and n > RULE_OF_THREE:
            # 豁免上限未查证（gnhf 审查模块 3 F2）：11 版编制规则不在语料内，
            # 十版对应上限为 6 份——设计文档裁决「不确定的 warn 不 error」，不静默豁免
            issues.append(ValidationIssue(
                "rot_exempt_uncapped", WARN,
                f"{name} 选了 {n} 份：BATTLELINE/DEDICATED TRANSPORT 豁免 Rule of "
                f"Three，但 11 版豁免上限未查证（十版为 6 份），份数合法性未完全校验",
                surfaced_only=True))

    # ⑤ 强化：≤3 个、仅 CHARACTER 非 EPIC HERO、全军唯一、属于本 detachment
    _validate_enhancements(db_path, priced, kw_map, unknown_ids, issues)

    legal = not any(i.severity == ERROR for i in issues)
    return ValidationReport(total_points=total, limit=limit, legal=legal,
                            issues=tuple(issues))


def _enhancement_points(db_path, roster: Roster):
    """强化点数合计 + 无法定价告警（cost NULL 的 131 条与错分队/无分队数据一律
    surfaced，不静默计 0——诚实降级红线）。"""
    enhanced = [u for u in roster.units if u.enhancement]
    if not enhanced:
        return 0, []
    catalog = {}
    if roster.detachment_id:
        from db_compile.enhancements import list_for_detachment
        catalog = {e["name"]: e["cost"]
                   for e in list_for_detachment(db_path, roster.detachment_id)}
    total = 0
    issues: List[ValidationIssue] = []
    for u in enhanced:
        cost = catalog.get(u.enhancement)
        if cost is None:
            issues.append(ValidationIssue(
                "enh_unpriced", WARN,
                f"强化「{u.enhancement}」点数未知（无分队数据、不属于当前分队或库中"
                "缺 cost），未计入总分",
                surfaced_only=True))
        else:
            total += cost
    return total, issues


def _validate_enhancements(db_path, roster: Roster, kw_map, unknown_ids,
                           issues: List[ValidationIssue]) -> None:
    enhanced = [u for u in roster.units if u.enhancement]
    if not enhanced:
        return

    # 数量上限
    if len(enhanced) > MAX_ENHANCEMENTS:
        issues.append(ValidationIssue(
            "enh_too_many", ERROR,
            f"强化 {len(enhanced)} 个，超上限 {MAX_ENHANCEMENTS}",
            anchor="11版 军表构筑·Enhancements"))

    # 全军唯一
    dup = [name for name, c in Counter(u.enhancement for u in enhanced).items() if c > 1]
    for name in dup:
        issues.append(ValidationIssue(
            "enh_duplicate", ERROR, f"强化「{name}」重复挂载（每个强化全军唯一）",
            anchor="11版 军表构筑·Enhancements"))

    # 仅 CHARACTER 非 EPIC HERO（未知单位跳过：是否 CHARACTER 无从判定，
    # 已由 unit_not_found 披露——对不存在的单位断言「非 CHARACTER」是编造）
    for u in enhanced:
        if u.canonical_id in unknown_ids:
            continue
        kw = kw_map.get(u.canonical_id, set())
        if not is_character(kw):
            issues.append(ValidationIssue(
                "enh_not_character", ERROR,
                f"{u.name_en} 非 CHARACTER，不能挂强化「{u.enhancement}」",
                anchor="11版 军表构筑·Enhancements"))
        elif is_epic_hero(kw):
            issues.append(ValidationIssue(
                "enh_epic_hero", ERROR,
                f"{u.name_en} 是 EPIC HERO，不能挂强化「{u.enhancement}」",
                anchor="11版 军表构筑·Enhancements"))

    # 属于本 detachment（数据缺口则 surface 不假通过）
    valid = _valid_enhancement_names(db_path, roster.detachment_id)
    if valid is None:
        issues.append(ValidationIssue(
            "enh_unverified", WARN,
            "未指定 detachment 或该分队无强化数据，强化归属合法性未校验",
            surfaced_only=True))
    else:
        for u in enhanced:
            if u.enhancement not in valid:
                issues.append(ValidationIssue(
                    "enh_wrong_detachment", ERROR,
                    f"强化「{u.enhancement}」不属于当前分队",
                    anchor="11版 军表构筑·Enhancements"))
