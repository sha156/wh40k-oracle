"""P7 阵营技能 DSL：载荷解析/校验/注入（spec 2026-07-14-p7-faction-dsl-pilot-design.md）。

**真源与投影**：DSL 唯一真源是 `dsl_payloads/*.json`（git 管理，逐条人工录入）；
DB 的 `effect_dsl_json`/`dsl_status` 列只是运行时投影（db_compile/dsl_apply.py 负责
写入并挂 restore，防 rebuild 清零——评审 F1）。本模块不碰 sqlite。

**三态判据（评审 F7 第④条已内置进校验）**：
  encoded     效果全部落入 effects、手算等价、且每个 (phase,op) 在施加侧有引擎消费点
  partial     可建模子集落 effects（同样过消费点校验），其余逐条写 not_modeled_notes_zh
  not_modeled effects 为空，notes 写明原因
白名单唯一真源 = sequence.ATTACKER_CONSUMED / TARGET_CONSUMED / KNOWN_CONDITION_TAGS
（不手抄第二份，引擎加分支需先登记，测试有护栏）。

**condition 契约（评审 F2）**：`(tag, *args)` 单 tag；合取列表在校验层直接拒载，
复合语义用复合 tag（如 guided_vs_spotted 自含"射击阶段+guided 开关"）。

**注入（评审 F5 成对语义）**：inject_attacker 只在 requires_toggles 全开时把 effects
追加到每把武器（dataclasses.replace，frozen 先例 engine._scale_loadout），并返回
modeled/not_modeled 注记——「报告出现 ⇄ 结果被影响」由调用方把注记挂进 SimReport。
铁律：逐条人工录入，LLM 只出初稿；宁 partial 不错编。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, FrozenSet, List, Tuple

from engines.simulator.contracts import AttackerProfile, Effect
from engines.simulator.sequence import (
    ATTACKER_CONSUMED,
    KNOWN_CONDITION_TAGS,
    TARGET_CONSUMED,
)

DSL_VERSION = 1
_STATUSES = ("encoded", "partial", "not_modeled")
_SIDES = ("attacker", "target")
_TABLES = ("abilities", "stratagems", "detachments")


class DslError(ValueError):
    """DSL 载荷不合法——快速失败，绝不静默降级成'无效果'。"""


@dataclass(frozen=True)
class DslEntry:
    table: str
    row_id: str
    side: str                        # attacker|target：效果施加侧（决定消费点白名单）
    faction: str
    detachment: str | None
    name_en: str
    name_zh: str | None
    status: str                      # encoded|partial|not_modeled
    effects: Tuple = ()              # tuple[Effect]
    requires_toggles: Tuple = ()     # 生效所需的手动态势开关名（Stance 字段名）
    not_modeled_notes_zh: Tuple = ()
    provenance: Dict = None
    encoded_by: str = ""


def _parse_effect(raw: dict, side: str, entry_name: str) -> Effect:
    phase, op = raw.get("phase"), raw.get("op")
    consumed = ATTACKER_CONSUMED if side == "attacker" else TARGET_CONSUMED
    if (phase, op) not in consumed:
        raise DslError(
            f"{entry_name}：(phase={phase!r}, op={op!r}) 不在 {side} 侧引擎消费点白名单"
            f"——引擎没接该通道，标 encoded/partial 会撒谎（评审 F7 判据④）")
    condition = tuple(raw.get("condition") or ())
    if condition:
        tag = condition[0]
        if tag not in KNOWN_CONDITION_TAGS:
            raise DslError(
                f"{entry_name}：未知 condition tag {tag!r}——契约是 (tag, *args) 单 tag，"
                f"合取列表不支持；复合语义先在 sequence 注册复合 tag（评审 F2）")
        for extra in condition[1:]:
            if extra in KNOWN_CONDITION_TAGS:
                raise DslError(
                    f"{entry_name}：condition {condition!r} 疑似合取列表"
                    f"（第二元素 {extra!r} 也是已知 tag）——引擎只读 condition[0]，拒载")
    if not raw.get("source"):
        raise DslError(f"{entry_name}：effect 缺 source（进报告 modeled_effects 的来源标签）")
    return Effect(phase=phase, op=op, params=tuple(raw.get("params") or ()),
                  condition=condition, source=raw["source"])


def parse_entry(raw: dict) -> DslEntry:
    name = f"{raw.get('table')}:{raw.get('id')}({raw.get('name_en')})"
    version = raw.get("dsl_version")
    if version != DSL_VERSION:
        raise DslError(f"{name}：dsl_version={version!r} 不受支持（只接受 {DSL_VERSION}，评审 F15）")
    if raw.get("table") not in _TABLES:
        raise DslError(f"{name}：table 必须是 {_TABLES}")
    if not raw.get("id"):
        raise DslError(f"{name}：缺 id")
    side = raw.get("side")
    if side not in _SIDES:
        raise DslError(f"{name}：side 必须是 {_SIDES}（决定消费点白名单侧）")
    status = raw.get("status")
    if status not in _STATUSES:
        raise DslError(f"{name}：status 必须是 {_STATUSES}")
    if not raw.get("faction"):
        raise DslError(f"{name}：缺 faction（检索链接载体，评审 F3）")
    effects = tuple(_parse_effect(e, side, name) for e in (raw.get("effects") or ()))
    notes = tuple(raw.get("not_modeled_notes_zh") or ())
    if status == "encoded" and not effects:
        raise DslError(f"{name}：encoded 但 effects 为空——应标 not_modeled")
    if status == "partial" and (not effects or not notes):
        raise DslError(f"{name}：partial 必须 effects 与 not_modeled_notes_zh 双非空"
                       f"（未建模残量一条不许漏写）")
    if status == "not_modeled" and effects:
        raise DslError(f"{name}：not_modeled 但带 effects——应标 encoded/partial")
    if status == "not_modeled" and not notes:
        raise DslError(f"{name}：not_modeled 必须写明原因")
    prov = raw.get("provenance") or {}
    if effects and not prov.get("text_sha256"):
        raise DslError(f"{name}：带 effects 必须有 provenance.text_sha256"
                       f"（原文指纹对账，评审 F12）")
    return DslEntry(
        table=raw["table"], row_id=raw["id"], side=side,
        faction=raw["faction"], detachment=raw.get("detachment"),
        name_en=raw.get("name_en") or "", name_zh=raw.get("name_zh"),
        status=status, effects=effects,
        requires_toggles=tuple(raw.get("requires_toggles") or ()),
        not_modeled_notes_zh=notes, provenance=prov,
        encoded_by=raw.get("encoded_by") or "")


def load_payload_file(path) -> List[DslEntry]:
    """读一个 dsl_payloads/*.json 真源文件 → 已校验条目列表（坏载荷快速失败）。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise DslError(f"{path}：载荷文件须有 entries 数组")
    out = []
    for raw in entries:
        raw = dict(raw)
        raw.setdefault("dsl_version", data.get("dsl_version"))
        raw.setdefault("faction", data.get("faction"))
        out.append(parse_entry(raw))
    return out


def parse_db_payload(payload_json: str) -> DslEntry:
    """解析 DB effect_dsl_json 列里的单条投影（dsl_apply 写入的就是 entry 原始 dict）。"""
    return parse_entry(json.loads(payload_json))


def inject_attacker(
    attacker: AttackerProfile,
    entries: List[DslEntry],
    toggles: FrozenSet[str],
) -> Tuple[AttackerProfile, List[str], List[str]]:
    """把开关满足的攻方侧 DSL 条目注入 loadout 每把武器，返回 (新attacker, modeled, not_modeled)。

    - 只在 requires_toggles ⊆ toggles 时注入并出 modeled 注记（评审 F5 成对语义：
      调用方须用同一 options 同时点亮 Stance 开关，条件 tag 才会放行）；
    - 开关未满足 → 不注入，出「未启用」注记进 not_modeled（不静默）；
    - partial 条目的未建模残量逐条透传 not_modeled。
    """
    modeled: List[str] = []
    not_modeled: List[str] = []
    new_loadout = list(attacker.loadout)
    for entry in entries:
        if entry.side != "attacker" or not entry.effects:
            if entry.status == "not_modeled" and entry.not_modeled_notes_zh:
                not_modeled.append(
                    f"DSL {entry.name_en}（{entry.status}）："
                    + "；".join(entry.not_modeled_notes_zh))
            continue
        missing = [t for t in entry.requires_toggles if t not in toggles]
        if missing:
            not_modeled.append(
                f"DSL {entry.name_en} 未启用（需开关 {'/'.join(missing)}），本次未施加")
            continue
        new_loadout = [replace(w, effects=w.effects + entry.effects)
                       for w in new_loadout]
        label = entry.name_zh or entry.name_en
        modeled.append(
            f"DSL 已施加：{label}（{entry.status}，开关 "
            f"{'/'.join(entry.requires_toggles) or '无'}）")
        for note in entry.not_modeled_notes_zh:
            not_modeled.append(f"DSL {label} 未建模残量：{note}")
    return replace(attacker, loadout=tuple(new_loadout)), modeled, not_modeled
