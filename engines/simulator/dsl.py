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

from engines.simulator.contracts import AttackerProfile, DiceExpr, Effect
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
    conflicts_with_toggles: Tuple = ()  # 与之互斥的开关名——开着任一则拒注入并显式披露
                                        # （审查 PR3-H1：CTE 的攻方=Observer，规则原文
                                        # Observer 排除在 Guided 外，与 guided 双开会
                                        # 规则外双重叠加 BS 改善）
    not_modeled_notes_zh: Tuple = ()
    provenance: Dict = None
    encoded_by: str = ""


# op → params 形状校验（PR2 审查 M3）：int 型 op 必须恰 1 个 int；无参 op 必须空；
# DiceExpr 型 op 按 PR3 编码约定解析（见 _parse_dice）
_INT_PARAM_OPS = frozenset({
    ("hit", "modify"), ("hit", "bs_improve"), ("hit", "crit_threshold"),
    ("wound", "modify"), ("wound", "crit_threshold"),
    ("attacks", "blast"),
    ("fnp", "fnp"), ("damage", "damage_reduction"),
    ("save", "ap_improve"),
})
_NO_PARAM_OPS = frozenset({
    ("hit", "auto_wound"), ("hit", "auto_hit"), ("hit", "indirect_fixed"),
    ("hit", "ignore_hit_mods"),
    ("wound", "mortal_pool"),
    ("save", "ignores_cover"), ("save", "cover"),
})
_DICE_PARAM_OPS = frozenset({
    ("attacks", "modify"), ("damage", "modify"), ("hit", "extra_hits"),
})
# 失败重骰型 op：params 固定 ["fail"]（引擎实现即"只重骰失败"最优策略，无其他模式）
_REROLL_OPS = frozenset({("wound", "reroll"), ("hit", "reroll")})


def _parse_dice(raw, entry_name: str, key) -> DiceExpr:
    """DiceExpr 的 JSON 编码约定（PR3 解锁项）：
      · 非负 int         → 常量（SUSTAINED HITS 1 → 1）
      · {"n","faces","k"} → NdM+K（RAPID FIRE D3 → {"n":1,"faces":3,"k":0}）
    恰这两种形状，键不许多不许少——手录笔误在校验期就炸（不静默）。"""
    if isinstance(raw, bool):
        raise DslError(f"{entry_name}：{key} 的 DiceExpr 参数不接受布尔，收到 {raw!r}")
    if isinstance(raw, int):
        if raw < 0:
            raise DslError(f"{entry_name}：{key} 的 DiceExpr 常量必须非负，收到 {raw}")
        return DiceExpr(k=raw)
    if isinstance(raw, dict):
        if set(raw) != {"n", "faces", "k"}:
            raise DslError(f"{entry_name}：{key} 的 DiceExpr 对象必须恰含 n/faces/k 三键，"
                           f"收到 {sorted(raw)!r}")
        n, faces, k = raw["n"], raw["faces"], raw["k"]
        for label, v in (("n", n), ("faces", faces), ("k", k)):
            if isinstance(v, bool) or not isinstance(v, int):
                raise DslError(f"{entry_name}：{key} 的 DiceExpr.{label} 必须是整数，收到 {v!r}")
        if n < 0 or faces < 0 or (n > 0 and faces < 2) or (n == 0 and faces != 0):
            raise DslError(f"{entry_name}：{key} 的 DiceExpr 不合法（n={n}, faces={faces}——"
                           f"有骰必须 faces≥2；常量必须 n=0 且 faces=0（或直接写 int），"
                           f"非规范形状按录入笔误拒载）")
        return DiceExpr(n=n, faces=faces, k=k)
    raise DslError(f"{entry_name}：{key} 的 DiceExpr 参数须为非负 int 或 "
                   f'{{"n","faces","k"}} 对象，收到 {type(raw).__name__}')


def _normalize_params(phase: str, op: str, params: tuple, entry_name: str) -> tuple:
    """按 op 形状校验并归一参数（DiceExpr 型转 contracts.DiceExpr），返回入 Effect 的 params。"""
    key = (phase, op)
    if key in _DICE_PARAM_OPS:
        if len(params) != 1:
            raise DslError(f"{entry_name}：(phase={phase}, op={op}) 需要恰 1 个 DiceExpr 参数，"
                           f"收到 {params!r}")
        return (_parse_dice(params[0], entry_name, key),)
    if key in _INT_PARAM_OPS:
        if len(params) != 1 or isinstance(params[0], bool) or not isinstance(params[0], int):
            raise DslError(f"{entry_name}：(phase={phase}, op={op}) 需要恰 1 个整数参数，"
                           f"收到 {params!r}")
    elif key in _NO_PARAM_OPS:
        if params:
            raise DslError(f"{entry_name}：(phase={phase}, op={op}) 不接受参数，收到 {params!r}")
    elif key in _REROLL_OPS:
        if tuple(params) != ("fail",):
            raise DslError(f"{entry_name}：(phase={phase}, op={op}) 参数必须为 [\"fail\"]"
                           f"（引擎语义=只重骰失败骰），收到 {params!r}")
    return params


def _parse_effect(raw: dict, side: str, entry_name: str) -> Effect:
    phase, op = raw.get("phase"), raw.get("op")
    consumed = ATTACKER_CONSUMED if side == "attacker" else TARGET_CONSUMED
    if (phase, op) not in consumed:
        raise DslError(
            f"{entry_name}：(phase={phase!r}, op={op!r}) 不在 {side} 侧引擎消费点白名单"
            f"——引擎没接该通道，标 encoded/partial 会撒谎（评审 F7 判据④）")
    params = _normalize_params(phase, op, tuple(raw.get("params") or ()), entry_name)
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
    return Effect(phase=phase, op=op, params=params,
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
    if side == "target" and effects:
        # PR2 审查 H1：注入层只有 inject_attacker，target 侧条目会被静默吞——
        # fail fast 拒载，待 inject_target 消费点落地（PR3+）后放开
        raise DslError(f"{name}：side=target 且带 effects——引擎注入层未接 target 侧，"
                       f"该条目会静默零效果；防守向规则暂标 not_modeled 或等 inject_target")
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
    conflicts = tuple(raw.get("conflicts_with_toggles") or ())
    overlap = set(conflicts) & set(raw.get("requires_toggles") or ())
    if overlap:
        raise DslError(f"{name}：开关 {sorted(overlap)} 同时出现在 requires 与 conflicts"
                       f"——条目永远无法生效，必是录入笔误")
    return DslEntry(
        table=raw["table"], row_id=raw["id"], side=side,
        faction=raw["faction"], detachment=raw.get("detachment"),
        name_en=raw.get("name_en") or "", name_zh=raw.get("name_zh"),
        status=status, effects=effects,
        requires_toggles=tuple(raw.get("requires_toggles") or ()),
        conflicts_with_toggles=conflicts,
        not_modeled_notes_zh=notes, provenance=prov,
        encoded_by=raw.get("encoded_by") or "")


def load_payload_file(path) -> List[DslEntry]:
    """读一个 dsl_payloads/*.json 真源文件 → 已校验条目列表（坏载荷快速失败）。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise DslError(f"{path}：载荷文件须有 entries 数组")
    out = []
    seen = set()
    for raw in entries:
        raw = dict(raw)
        raw.setdefault("dsl_version", data.get("dsl_version"))
        raw.setdefault("faction", data.get("faction"))
        entry = parse_entry(raw)
        key = (entry.table, entry.row_id)
        if key in seen:
            # PR2 审查 M2：重复条目静默"后者覆盖前者"是铺量期复制粘贴错 id 的温床
            raise DslError(f"{path}：重复条目 {key}——同一 (table, id) 只许一条")
        seen.add(key)
        out.append(entry)
    return out


def parse_db_payload(payload_json: str) -> DslEntry:
    """解析 DB effect_dsl_json 列里的单条投影（dsl_apply 写入的就是 entry 原始 dict）。"""
    return parse_entry(json.loads(payload_json))


def _norm_token(s: str) -> str:
    """名字/分队匹配归一：弯撇号 ’ 统一成 '，casefold + 去首尾空白。
    DB 拼写带弯撇号（Mont’ka，以 enhancements.detachment_name 为准——评审 F3），
    用户从 CLI/网页输入直撇号是常态，不许因引号形状静默匹配失败。"""
    return s.strip().casefold().replace("’", "'")


def select_entries(
    entries: List[DslEntry],
    detachment: str | None = None,
    stratagems: Tuple = (),
) -> Tuple[List[DslEntry], List[str]]:
    """按所选分队 + 被点名战略过滤条目 → (入选条目, 披露注记)。P7-PR3 选择层：

    - 非 stratagems 条目（军规/分队规则）：detachment 为 None（军队级）恒入选；
      带 detachment 的仅当与所选分队匹配才入选（未选/不符 → 注记披露，不静默）。
    - stratagems 表条目 = 一次性 opt-in：必须被 `stratagems` 点名（token 匹配
      row_id / name_en / name_zh 任一，弯撇号归一）；点名了但分队不符 → 拒入选并披露。
      未选分队时点名战略照常入选（假设军队就是该分队，注记披露该假设）。
    - 点名 token 无匹配 → 注记披露（错名字不静默吞——批量期复制粘贴错名的温床）。
    """
    want_det = _norm_token(detachment) if detachment else None
    tokens = [str(t) for t in stratagems if str(t).strip()]
    selected: List[DslEntry] = []
    notes: List[str] = []
    matched_tokens: set = set()

    def _entry_matches(entry: DslEntry, token: str) -> bool:
        t = _norm_token(token)
        cands = [entry.row_id, entry.name_en or "", entry.name_zh or ""]
        return any(t == _norm_token(c) for c in cands if c)

    for entry in entries:
        e_det = _norm_token(entry.detachment) if entry.detachment else None
        if entry.table == "stratagems":
            hit = [tok for tok in tokens if _entry_matches(entry, tok)]
            if not hit:
                continue
            matched_tokens.update(hit)
            if want_det and e_det and e_det != want_det:
                notes.append(
                    f"战略 {entry.name_zh or entry.name_en} 属分队 {entry.detachment}，"
                    f"与所选分队 {detachment} 不符——本次未施加")
                continue
            if not want_det and e_det:
                notes.append(
                    f"战略 {entry.name_zh or entry.name_en}：未指定分队，"
                    f"按军队即为 {entry.detachment} 分队假设施加")
            selected.append(entry)
        else:
            if e_det is None:
                selected.append(entry)          # 军队级规则（FTGG）恒入选
            elif want_det == e_det:
                selected.append(entry)
            elif want_det:
                notes.append(
                    f"分队规则 {entry.name_zh or entry.name_en}（{entry.detachment}）"
                    f"与所选分队 {detachment} 不符——本次未施加")
            # 未选分队 → 分队规则不入选也不逐条刷屏（dsl_available 已 surface 可选项）
    for tok in tokens:
        if tok not in matched_tokens:
            notes.append(f"战略点名 {tok!r} 无匹配 DSL 条目（查 id / 英文名 / 中文名），"
                         f"本次未施加")
    return selected, notes


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
            elif entry.effects:
                # 防御性披露（审查 H1 纵深）：parse_entry 已拒 target+effects，
                # 此分支只在 DB 投影被手改时可达——照样不许静默吞
                not_modeled.append(
                    f"DSL {entry.name_en}（side={entry.side}）引擎注入层未接该侧，"
                    f"本次未施加")
            continue
        missing = [t for t in entry.requires_toggles if t not in toggles]
        if missing:
            not_modeled.append(
                f"DSL {entry.name_en} 未启用（需开关 {'/'.join(missing)}），本次未施加")
            continue
        conflict = [t for t in entry.conflicts_with_toggles if t in toggles]
        if conflict:
            # 审查 PR3-H1：互斥开关同开 → 硬性拒注入并显眼披露（不许规则外叠加），
            # 不做"保留最高值"的静默修正——用户必须自己关掉其一
            not_modeled.append(
                f"⚠ DSL {entry.name_zh or entry.name_en} 与开关 {'/'.join(conflict)} 互斥"
                f"（规则原文两种状态不能共存），本次未施加——关闭其一后重跑")
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
