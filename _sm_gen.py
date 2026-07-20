# -*- coding: utf-8 -*-
"""P7-PR20 Space-Marines DSL 载荷生成器：从（已打 fp-rules 补丁的）DB 拉正文+指纹，
按人工分类拼 dsl_payloads/spacemarines.json。零新引擎通道、零新态势开关。"""
import hashlib, json, re, sqlite3
from pathlib import Path

DB = "db/wh40k.sqlite"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
_TAG = re.compile(r"<[^>]+>")
def _norm(v):
    if v is None: return ""
    s = _TAG.sub("", str(v))
    for a, b in (("’","'"),("‘","'"),("“",'"'),("”",'"'),("‑","-"),("–","-"),("—","-")):
        s = s.replace(a, b)
    return " ".join(s.split()).strip().lower()
def fp(text): return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()

def dbtext(table, rid):
    col = {"stratagems":"text_zh","enhancements":"description","detachments":"rule_text"}[table]
    r = con.execute(f"SELECT {col} FROM {table} WHERE id=?", (rid,)).fetchone()
    assert r is not None, f"missing {table}:{rid}"
    return r[0]
def dbnames(table, rid):
    if table == "enhancements":
        r = con.execute("SELECT name, NULL FROM enhancements WHERE id=?", (rid,)).fetchone()
        return r[0], None
    r = con.execute(f"SELECT name_en, name_zh FROM {table} WHERE id=?", (rid,)).fetchone()
    return r[0], r[1]

ENTRIES = []
BY = "manual-2026-07-20"

def E(phase, op, params, cond, source):
    return {"phase": phase, "op": op, "params": params, "condition": cond, "source": source}

def rule(det_id, cont, status, effects=(), toggles=(), notes=()):
    """分队规则 → abilities 物化条目（materialize detachments.rule_text）。"""
    nen, nzh = dbnames("detachments", det_id)
    e = {"table": "abilities", "id": "det"+det_id, "side": "attacker", "detachment": cont,
         "name_en": nen, "name_zh": nzh, "status": status, "effects": list(effects),
         "requires_toggles": list(toggles), "not_modeled_notes_zh": list(notes),
         "provenance": {"text_sha256": fp(dbtext("detachments", det_id))}, "encoded_by": BY,
         "materialize": {"from_table": "detachments", "from_id": det_id, "from_column": "rule_text"}}
    ENTRIES.append(e)

def row(table, rid, cont, side, status, effects=(), toggles=(), notes=(), wf=None):
    nen, nzh = dbnames(table, rid)
    e = {"table": table, "id": rid, "side": side, "detachment": cont,
         "name_en": nen, "name_zh": nzh, "status": status, "effects": list(effects),
         "requires_toggles": list(toggles), "not_modeled_notes_zh": list(notes),
         "provenance": {"text_sha256": fp(dbtext(table, rid))}, "encoded_by": BY}
    if wf: e["weapon_filter"] = wf
    ENTRIES.append(e)

def strat(rid, cont, side, status, effects=(), toggles=(), notes=(), wf=None):
    row("stratagems", rid, cont, side, status, effects, toggles, notes, wf)
def enh(rid, cont, side, status, effects=(), toggles=(), notes=(), wf=None):
    row("enhancements", rid, cont, side, status, effects, toggles, notes, wf)

# 共用效果
def AOC():
    return [E("save","ap_improve",[-1],[],"傲慢之甲（被攻 AP 恶化 1，射击/近战两相位）")]
AOC_NOTE = ["触发时机为敌方选中目标后——点名即假设已使用；射击与近战两相位均适用"]
def LETHAL(gate, src): return [E("hit","auto_wound",[],[gate],src)]
def SUS1(gate, src): return [E("hit","extra_hits",[1],[gate],src)]
def IGCOV(src): return [E("save","ignores_cover",[],["phase_shooting"],src)]

# ══════════════════════════════════════════════════════════════════════
# LIBRARIUS CONCLAVE
C = "Librarius Conclave"
rule("000009784", C, "not_modeled", notes=[
    "军规：每大回合选一心灵领域（生物操纵/预言/焰控/念动/心灵感应），全军 PSYKER 单位获对应效果——"
    "灵能领域选择状态机 + PSYKER 单位域，无引擎载体，不编"])
strat("000009791002", C, "attacker", "not_modeled", notes=["指挥阶段 pin 敌方（-2M/-2冲锋）+ 心灵感应触发战斗震慑——移动减益/士气域未建模"])
strat("000009791003", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000009791004", C, "target", "partial",
      [E("hit","modify",[-1],["phase_melee"],"炽焰护盾（近战被攻命中-1）")],
      notes=["WHEN=战斗阶段敌方选中目标后（仅近战），焰控领域附加 [HAZARDOUS] 为武器关键词域未建模；仅编近战命中-1"])
strat("000009791005", C, "attacker", "partial",
      [E("wound","s_improve",[1],["phase_melee"],"铁腕（近战武器 +1 S，特征值通道）")],
      notes=["生物操纵领域激活时改 +2 S——领域状态机无载体，仅编基础 +1（防高估）；近战门"])
strat("000009791006", C, "attacker", "not_modeled", notes=["6D6、4+ 各 1 致命伤——固定致命伤池不在攻击序列内，念动领域 +1 分支依赖领域状态，均不编"])
strat("000009791007", C, "attacker", "partial",
      LETHAL("phase_shooting","预知精准（远程 [LETHAL HITS]——暴击自动致伤）"),
      notes=["预言领域激活时附加 [IGNORES COVER]——领域状态机无载体，仅编基础 [LETHAL HITS]；射击门"])
enh("000009785002", C, "attacker", "not_modeled", notes=["敌方结束移动后反应移动——移动域未建模"])
enh("000009785003", C, "attacker", "not_modeled", notes=["加速/撤退后可冲锋——移动资格域未建模"])
enh("000009785004", C, "attacker", "not_modeled", notes=["禁敌方掩护射击 + 心灵感应远程射程限制——掩护射击/射程门域未建模"])
enh("000009785005", C, "attacker", "not_modeled", notes=["[ANTI-MONSTER/VEHICLE 5+]（关键词条件暴击阈值 + 领域附加 [SUSTAINED]/射程）——ANTI 关键词门无载体，不编"])

# ══════════════════════════════════════════════════════════════════════
# ARMOURED SPEARTIP
C = "Armoured Speartip"
rule("000010777", C, "not_modeled", notes=["军规：下车单位常规移动 D6/D3+3、Heavy Transport 关键词——移动/编成域未建模"])
strat("000010780002", C, "attacker", "not_modeled", notes=["被毁 Heavy Transport 死前移动——移动/Deadly Demise 域未建模"])
strat("000010780003", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010780004", C, "attacker", "not_modeled", notes=["战斗阶段末登车——移动/登车域未建模"])
strat("000010780005", C, "attacker", "not_modeled", notes=["穿越地形/敌方模型移动——移动域未建模"])
strat("000010780006", C, "attacker", "not_modeled", notes=["加速后下车——移动/下车域未建模"])
strat("000010780007", C, "attacker", "partial",
      [E("hit","modify",[1],["phase_shooting"],"净化教条（射击命中+1）")],
      notes=["WHEN=射击阶段（条件自含射击门）；下车自 Heavy Transport 时附加致伤+1——下车态无射击复合载体，仅编命中+1"])
enh("000010779002", C, "attacker", "not_modeled", notes=["目标点持续控制——目标点域未建模"])
enh("000010779003", C, "attacker", "not_modeled", notes=["运输载具 Scouts 6\"——部署域未建模"])
enh("000010779004", C, "attacker", "partial",
      SUS1("phase_shooting","震慑下车（下车后远程 [SUSTAINED HITS 1]）"),
      toggles=["bearer_leading","disembarked_this_turn"],
      notes=["限携带者（Terminator/Gravis）单位本回合下车后远程武器——下车态用开关门控，射击门自含"])
enh("000010779005", C, "attacker", "not_modeled", notes=["预备队出场轮次+1——预备队域未建模"])

# ══════════════════════════════════════════════════════════════════════
# HEADHUNTER TASK FORCE
C = "Headhunter Task Force"
rule("000010782", C, "not_modeled", notes=["军规：Tank Ace 加速 +6\"M、驻停重投伤害 + Tank Ace/Character 关键词授予——移动/重投伤害/编成域未建模"])
strat("000010784002", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010784003", C, "attacker", "not_modeled", notes=["对 Monster/Vehicle +1 AP——射击×关键词（M/V 二选）无复合载体，裸 target_has_keyword 只能表达单关键词且不含射击门，不编"])
strat("000010784004", C, "attacker", "not_modeled", notes=["对 Monster/Vehicle 重投致伤 1（低于起始编制则全量重投）——重骰 1/关键词门/编制状态均无载体，不编"])
strat("000010784005", C, "attacker", "not_modeled", notes=["撤退后可射击——移动资格域未建模"])
strat("000010784006", C, "attacker", "not_modeled", notes=["敌方移动后反应移动——移动域未建模"])
strat("000010784007", C, "attacker", "not_modeled", notes=["对手射击阶段还击射击——阶段外射击域未建模"])
enh("000010783002", C, "target", "partial",
      [E("save","invuln",[5],[],"坚毅机魂（携带者 5+ 无效保护）")], toggles=["defender_bearer_leading"],
      notes=["限携带者（Vehicle）模型（点名即声明守方为携带者）；指挥阶段回 1 伤——回血域未建模，仅编 5+ 无效保护"])
enh("000010783003", C, "attacker", "not_modeled", notes=["每阶段重投一次命中/致伤/伤害骰——单次重投无载体，未建模"])
enh("000010783004", C, "attacker", "partial",
      SUS1("phase_shooting","风暴协调（携带者远程 [SUSTAINED HITS 1]）"), toggles=["bearer_leading"],
      notes=["限携带者（Vehicle）模型远程武器（单人物模拟准确，附属单位整体注入会高估）；射击门"])
enh("000010783005", C, "attacker", "not_modeled", notes=["光环授予友方 Vehicle [ASSAULT]——光环/移动域未建模"])

# ══════════════════════════════════════════════════════════════════════
# CERAMITE SENTINELS
C = "Ceramite Sentinels"
rule("000010758", C, "not_modeled", notes=["军规：地形内重投命中1/致伤1 + Entrenched 关键词——重骰 1/地形状态域无载体，不编"])
strat("000010760002", C, "attacker", "not_modeled", notes=["+1 OC——目标点域未建模"])
strat("000010760003", C, "attacker", "not_modeled", notes=["对 Character/Monster/Vehicle 全量重投致伤——关键词门（三选）无载体，裸编会对全目标过度施加，不编"])
strat("000010760004", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010760005", C, "attacker", "not_modeled", notes=["被毁模型死后一击——战斗序列/复活域未建模"])
strat("000010760006", C, "attacker", "not_modeled", notes=["[SUSTAINED HITS 1] 或 [LETHAL HITS] 二选一（Entrenched 则两者）——一次性二选一单分支无载体，不编"])
strat("000010760007", C, "attacker", "not_modeled", notes=["敌方射击后反应移动——移动域未建模"])
enh("000010759002", C, "attacker", "not_modeled", notes=["首次被毁 2+ 复活——复活域未建模"])
enh("000010759003", C, "attacker", "not_modeled", notes=["撤退后可行动/射击冲锋——移动资格域未建模"])
enh("000010759004", C, "attacker", "partial",
      IGCOV("侦骷数据链（携带者单位远程 [无视掩体]）"), toggles=["bearer_leading"],
      notes=["限携带者单位远程武器；[无视掩体] 自含射击语义"])
enh("000010759005", C, "attacker", "not_modeled", notes=["部署后重部署——部署域未建模"])

# ══════════════════════════════════════════════════════════════════════
# BLADE OF ULTRAMAR
C = "Blade of Ultramar"
rule("000010632", C, "not_modeled", notes=["军规：至多三次指挥阶段选战斗教条（毁灭者/战术/突击）——教条选择状态机无载体，不编"])
strat("000010634002", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010634003", C, "attacker", "not_modeled", notes=["守方 S≥T 时被伤-1——引擎 wound_s_gt_t 为 S>T 严格，漏 S=T 档不等价，不编（防错编）"])
strat("000010634004", C, "attacker", "partial",
      [E("wound","modify",[1],["melee_charging"],"荣耀与荣光（近战 [LANCE]——冲锋回合致伤+1）")],
      notes=["[LANCE]=冲锋回合近战致伤+1（melee_charging 复合门）；突击教条附加 +1 AP——教条状态机无载体，不编 AP 分支"])
strat("000010634005", C, "attacker", "not_modeled", notes=["指挥阶段为本单位选战斗教条——教条状态机无载体，不编"])
strat("000010634006", C, "attacker", "partial",
      IGCOV("模范警惕（远程 [无视掩体]）"),
      notes=["WHEN=射击阶段（射击门自含）；毁灭者教条附加 +1 AP——教条状态机无载体，不编 AP 分支"])
strat("000010634007", C, "attacker", "not_modeled", notes=["敌方移动后反应移动——移动域未建模"])
enh("000010633002", C, "target", "partial",
      [E("fnp","fnp",[5],[],"安东尼努斯之铠（携带者 FNP 5+）")], toggles=["defender_bearer_leading"],
      notes=["限携带者（点名即声明守方为携带者）；Sv 改 2+ 依赖基础护甲无净算载体——仅编 FNP 5+"])
enh("000010633003", C, "attacker", "partial",
      [E("attacks","modify",[1],["phase_melee"],"马克拉格之誓（携带者近战武器 A+1）"),
       E("wound","s_improve",[1],["phase_melee"],"马克拉格之誓（携带者近战武器 +1 S，特征值通道）")],
      toggles=["bearer_leading"],
      notes=["限携带者模型近战武器（附属单位整体注入会高估）；突击教条时改 +2 A/S——教条状态机无载体，仅编 +1（防高估）；近战门"])
enh("000010633004", C, "attacker", "not_modeled", notes=["指挥阶段为本单位强制战术教条——教条状态机无载体，不编"])
enh("000010633005", C, "attacker", "partial",
      SUS1("phase_shooting","贝希摩斯老兵（携带者单位远程 [SUSTAINED HITS 1]）"), toggles=["bearer_leading"],
      notes=["限携带者率领单位远程武器；毁灭者教条重投加速——教条/移动域未建模；射击门"])

# ══════════════════════════════════════════════════════════════════════
# HAMMER OF AVERNII
C = "Hammer of Avernii"
rule("000010620", C, "not_modeled", notes=["军规：对誓约目标重投致伤 1——重骰 1 无载体（引擎重骰=全部失败骰）+ 誓约目标机制不在 P7 编码范围，不编"])
rule("000010621", C, "not_modeled", notes=["Caanok Var 重新指定誓约目标——誓约标记机制不在 P7 编码范围，不编"])
strat("000010624002", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010624003", C, "attacker", "partial",
      [E("hit","modify",[1],[],"无情屠戮（命中+1，射击/近战两相位）")],
      notes=["WHEN=射击或战斗阶段（两相位均可，故不挂相位门）；本单位低于起始编制时附加致伤+1——攻方本单位编制状态无载体，不编致伤分支"])
strat("000010624004", C, "attacker", "not_modeled", notes=["目标点持续控制——目标点域未建模"])
strat("000010624005", C, "attacker", "not_modeled", notes=["近战 [SUSTAINED HITS 1] 或 [LETHAL HITS] 二选一——一次性二选一单分支无载体，不编"])
strat("000010624006", C, "target", "partial",
      [E("damage","damage_reduction",[1],["phase_melee"],"机械坚韧（被近战攻击伤害-1）")],
      notes=["WHEN=对手冲锋阶段末（点名即假设已触发接战），持续至回合末——对手相位序中射击在冲锋前，触发后本回合仅剩近战能生效，故门 phase_melee（避免过度施加到射击）"])
strat("000010624007", C, "attacker", "not_modeled", notes=["撤出置入预备队——预备队域未建模"])
enh("000010623002", C, "attacker", "partial",
      [E("attacks","modify",[1],["phase_melee"],"铁血之魂（携带者近战武器 A+1）")], toggles=["bearer_leading"],
      notes=["限携带者模型近战武器；每场一次全单位 A+1——一次性单位增益无载体，仅编携带者 +1；近战门"])
enh("000010623003", C, "attacker", "not_modeled", notes=["敌方战斗震慑失败则毁模型——士气/战斗震慑域未建模"])
enh("000010623004", C, "attacker", "not_modeled", notes=["+1 OC——目标点域未建模"])
enh("000010623005", C, "attacker", "not_modeled", notes=["指挥阶段复活 Bodyguard 模型——复活域未建模"])

# ══════════════════════════════════════════════════════════════════════
# SPEARPOINT TASK FORCE
C = "Spearpoint Task Force"
rule("000010626", C, "not_modeled", notes=["军规：加速/撤退后可冲锋——移动资格域未建模"])
rule("000010627", C, "not_modeled", notes=["Suboden Khan 战斗阶段末击杀后移动——移动域未建模"])
strat("000010630002", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010630003", C, "attacker", "not_modeled", notes=["[LANCE] 或 [LETHAL HITS] 二选一（Mounted 则两者）——一次性二选一单分支无载体，不编"])
strat("000010630004", C, "attacker", "not_modeled", notes=["加速/撤退后可射击——移动资格域未建模"])
strat("000010630005", C, "attacker", "not_modeled", notes=["敌方移动后反应移动——移动域未建模"])
strat("000010630006", C, "target", "partial",
      [E("hit","modify",[-1],["phase_shooting"],"闪避机动（守方被射击命中-1）"),
       E("wound","modify",[-1],["phase_shooting"],"闪避机动（守方被射击致伤-1）")],
      notes=["限 Mounted/Fly Vehicle 守方；WHEN=对手射击阶段选中目标后（射击门自含），近战不注入"])
strat("000010630007", C, "attacker", "not_modeled", notes=["撤出置入预备队——预备队域未建模"])
enh("000010629002", C, "attacker", "partial",
      [E("wound","s_improve",[1],["phase_melee"],"矛尖楷模（携带者近战武器 +1 S，特征值通道）"),
       E("save","ap_improve",[1],["phase_melee"],"矛尖楷模（携带者近战武器 AP 改善 1）")],
      toggles=["bearer_leading"],
      notes=["限携带者模型近战武器；冲锋后改 +2 S/AP——一次性冲锋增益无载体，仅编基础 +1（防高估）；近战门"])
enh("000010629003", C, "attacker", "not_modeled", notes=["重投加速——移动域未建模"])
enh("000010629004", C, "attacker", "partial",
      [E("hit","extra_hits",[1],["phase_shooting"],"猎手之眼（携带者单位远程 [SUSTAINED HITS 1]）"),
       E("save","ignores_cover",[],["phase_shooting"],"猎手之眼（携带者单位远程 [无视掩体]）")],
      toggles=["bearer_leading"],
      notes=["限携带者率领单位远程武器（单人物模拟准确，附属单位整体注入会高估）；射击门"])
enh("000010629005", C, "attacker", "not_modeled", notes=["预备队出场轮次+1——预备队域未建模"])

# ══════════════════════════════════════════════════════════════════════
# FORGEFATHER'S SEEKERS
C = "Forgefather’s Seekers"
rule("000010367", C, "partial",
      [E("wound","s_improve",[1],["ranged_within_12"],"火神追寻（远程攻击 12\" 内 +1 S，特征值通道）")],
      notes=["[ASSAULT]（加速后可射击）为移动域未建模；Seeker's Companions（Infernus 行动资格）未建模；ranged_within_12 自含射击门"])
strat("000010369002", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010369003", C, "attacker", "not_modeled", notes=["对 6\" 内最近合格目标 +1 致伤——空间「最近目标」判据无载体，不编"])
strat("000010369004", C, "attacker", "not_modeled", notes=["撤退后可射击——移动资格域未建模"])
strat("000010369005", C, "attacker", "not_modeled", notes=["Torrent 武器 [DEVASTATING WOUNDS]——Torrent 为武器关键词非名字子串，weapon_filter 无法选取，裸编对非 Torrent 过度施加，不编"])
strat("000010369006", C, "attacker", "not_modeled", notes=["下车+还击射击——移动/阶段外射击域未建模"])
strat("000010369007", C, "attacker", "not_modeled", notes=["-2 敌方冲锋骰——士气/移动域未建模"])
enh("000010368002", C, "attacker", "not_modeled", notes=["Torrent 武器 A+1——Torrent 为关键词非名字子串，weapon_filter 无法选取，不编"])
enh("000010368003", C, "attacker", "partial",
      [E("wound","s_improve",[3],["phase_melee"],"战火淬炼军械（携带者近战武器 +3 S，特征值通道）")],
      toggles=["bearer_leading"],
      notes=["限携带者（Infantry）模型近战武器；+3 S 延迟判定在引擎最终 S 处结算；近战门"])
enh("000010368004", C, "attacker", "not_modeled", notes=["每回合一次把命中/保存骰改为 6——单骰结果操纵无载体，未建模"])
enh("000010368005", C, "target", "partial",
      [E("damage","damage_reduction",[1],[],"精金披风（携带者被攻伤害-1，射击/近战两相位）")],
      toggles=["defender_bearer_leading"],
      notes=["限携带者（点名即声明守方为携带者）；Melta/Torrent 攻击改伤害为 1——武器关键词门无载体，仅编基础伤害-1（防高估）"])

# ══════════════════════════════════════════════════════════════════════
# EMPEROR'S SHIELD
C = "Emperor’s Shield"
rule("000010459", C, "not_modeled", notes=["军规：对誓约目标重投致伤 1 / Lysander 单位全量重投——重骰 1/誓约目标机制不在 P7 编码范围，不编"])
strat("000010461002", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010461003", C, "attacker", "partial",
      [E("hit","modify",[1],[],"首连之怒（命中+1，射击/近战两相位）")],
      notes=["WHEN=射击或战斗阶段（两相位均可，不挂相位门）；本单位低于起始编制时附加致伤+1——攻方本单位编制状态无载体，不编致伤分支"])
strat("000010461004", C, "attacker", "not_modeled", notes=["被毁模型死后一击——战斗序列/复活域未建模"])
strat("000010461005", C, "attacker", "not_modeled", notes=["目标点持续控制——目标点域未建模"])
strat("000010461006", C, "attacker", "partial",
      [E("save","ignores_cover",[],["phase_shooting"],"纪律歼灭（远程 [无视掩体]）"),
       E("save","ap_improve",[1],["phase_shooting"],"纪律歼灭（远程攻击 AP 改善 1）")],
      notes=["限 Terminator/老兵单位远程武器（选本战略即声明）；射击门"])
strat("000010461007", C, "attacker", "not_modeled", notes=["撤出置入预备队——预备队域未建模"])
enh("000010460002", C, "attacker", "partial",
      [E("attacks","modify",[1],["phase_melee"],"盛宴勇士（携带者近战武器 A+1）")], toggles=["bearer_leading"],
      notes=["限携带者模型近战武器；每场一次全单位 A+1——一次性单位增益无载体，仅编携带者 +1；近战门"])
enh("000010460003", C, "attacker", "not_modeled", notes=["+1 OC——目标点域未建模"])
enh("000010460004", C, "attacker", "not_modeled", notes=["首次被毁 2+ 带 3 伤复活——复活域未建模"])
enh("000010460005", C, "target", "partial",
      [E("wound","modify",[-1],["wound_s_gt_t"],"马洛德拉克斯军旗（守方被 S>T 攻击致伤-1）")],
      toggles=["defender_bearer_leading"],
      notes=["限旗手（Ancient）率领单位（点名即声明守方为携带者单位）；S>T 延迟判定在引擎最终 S 处结算；射击/近战两相位均适用"])

# ══════════════════════════════════════════════════════════════════════
# SHADOWMARK TALON
C = "Shadowmark Talon"
rule("000010463", C, "not_modeled", notes=["军规：远程攻击者非 12\" 内则守方 -1 命中且获掩体——「攻击者超 12\"」的远程距离门无守方载体，裸编会在近距离过度施加，不编"])
rule("000010464", C, "not_modeled", notes=["每大回合 0CP 用 Into Darkness——CP/战略域未建模"])
strat("000010467002", C, "target", "partial", AOC(), notes=AOC_NOTE)
strat("000010467003", C, "attacker", "not_modeled", notes=["近战 [PRECISION]——攻击分配域（点杀附属人物）未建模"])
strat("000010467004", C, "attacker", "not_modeled", notes=["撤退后可射击冲锋——移动资格域未建模"])
strat("000010467005", C, "attacker", "not_modeled", notes=["对 >12\" 敌 +1 BS/+1 AP + 战斗震慑——「超 12\"」远程距离门无载体，不编"])
strat("000010467006", C, "attacker", "not_modeled", notes=["敌方移动后反应移动——移动域未建模"])
strat("000010467007", C, "attacker", "not_modeled", notes=["撤出置入预备队——预备队域未建模"])
enh("000010466002", C, "attacker", "not_modeled", notes=["携带者单位获 Infiltrators——部署域未建模"])
enh("000010466003", C, "attacker", "not_modeled", notes=["敌方战略 CP 税光环——CP 域未建模"])
enh("000010466004", C, "target", "partial",
      [E("hit","modify",[-1],["phase_shooting"],"暗影猛禽（携带者获 Stealth，被远程攻击命中-1）")],
      toggles=["defender_bearer_leading"],
      notes=["Stealth 语义=被远程攻击命中-1（射击门自含）；Lone Operative（点名限制）未建模"])
enh("000010466005", C, "attacker", "not_modeled", notes=["预备队出场轮次+1——预备队域未建模"])

# ══════════════════════════════════════════════════════════════════════
# BASTION TASK FORCE
C = "Bastion Task Force"
rule("000010675", C, "not_modeled", notes=["军规：Battleline 加速/撤退后可射击冲锋 + auspex 标记重投命中 1——移动资格/重骰 1/标记状态域无载体，不编"])
strat("000010677002", C, "attacker", "not_modeled", notes=["重投命中 1（auspex 则重投致伤 1）——重骰 1 无载体，不编"])
strat("000010677003", C, "attacker", "not_modeled", notes=["auspex 标记敌方 pinned——移动减益/标记状态域未建模"])
strat("000010677004", C, "attacker", "not_modeled", notes=["[LETHAL HITS] 或 [SUSTAINED HITS 1] 二选一（限 auspex/Battleline）——一次性二选一 + 标记/编成门无载体，不编"])
strat("000010677005", C, "attacker", "not_modeled", notes=["auspex 标记敌方 suppressed（-1 命中）——标记状态/敌方减益域未建模"])
strat("fp11e-spacemarines-bastion-s6", C, "target", "partial",
      [E("wound","modify",[-1],["wound_s_gt_t"],"天使不屈（守方 Battleline 被 S>T 攻击致伤-1）")],
      notes=["限 Battleline 守方；WHEN=对手射击或战斗阶段选中目标后；S>T 延迟判定在引擎最终 S 处结算；两相位均适用"])
strat("000010677007", C, "attacker", "not_modeled", notes=["加速/撤退后可射击冲锋（须打 auspex 目标）——移动资格/标记域未建模"])
enh("000010676002", C, "attacker", "not_modeled", notes=["Battleline 远程 [PRECISION]——攻击分配域未建模"])
enh("000010676003", C, "attacker", "not_modeled", notes=["携带者获 Battleline 关键词——编成域未建模"])
enh("000010676004", C, "attacker", "partial",
      [E("save","ap_improve",[1],["phase_melee"],"英勇之刃（携带者及单位 Battleline 模型近战武器 AP 改善 1）")],
      toggles=["bearer_leading"],
      notes=["限携带者及单位内 Battleline 模型近战武器（附属单位整体注入会高估）；近战门"])
enh("000010676005", C, "attacker", "not_modeled", notes=["被战略指定时 4+ 回 1CP——CP 域未建模"])

# ══════════════════════════════════════════════════════════════════════
# ORBITAL ASSAULT FORCE
C = "Orbital Assault Force"
rule("000010679", C, "not_modeled", notes=["军规：按战斗规模授 Deep Strike + 本回合部署/下车 Drop Pod 重投致伤 1/命中 1——预备队/重骰 1 无载体，不编"])
strat("000010681002", C, "attacker", "not_modeled", notes=["战斗震慑 suppressed——士气域未建模"])
strat("000010681003", C, "attacker", "not_modeled", notes=["[PRECISION] + 对 Character +1 命中——攻击分配/关键词门无载体，不编"])
strat("000010681004", C, "attacker", "not_modeled", notes=["跟进/巩固移动 6\"——移动域未建模"])
strat("000010681005", C, "attacker", "not_modeled", notes=["[LETHAL HITS] 或 [SUSTAINED HITS 1] 二选一（限下车/12\" 内）——一次性二选一单分支无载体，不编"])
strat("000010681006", C, "target", "partial",
      [E("hit","modify",[-1],["phase_shooting"],"致盲屏障（守方获 Stealth，被远程攻击命中-1）"),
       E("save","cover",[],["phase_shooting"],"致盲屏障（守方获掩体）")],
      notes=["限烟幕载具/Drop Pod 9\" 内友方（点名即假设已满足）；WHEN=对手射击阶段（射击门自含），近战不注入"])
strat("000010681007", C, "attacker", "not_modeled", notes=["战斗阶段末登车——移动/登车域未建模"])
enh("000010680002", C, "attacker", "not_modeled", notes=["部署回合重投冲锋——移动域未建模"])
enh("000010680003", C, "attacker", "not_modeled", notes=["单位 Scouts 6\"——部署域未建模"])
enh("000010680004", C, "attacker", "not_modeled", notes=["部署后重部署——部署域未建模"])
enh("000010680005", C, "attacker", "not_modeled", notes=["撤出置入预备队——预备队域未建模"])

# ══════════════════════════════════════════════════════════════════════
# RECLAMATION FORCE
C = "Reclamation Force"
rule("000010683", C, "not_modeled", notes=["军规：近战对目标点范围内目标 +1 AP + 守方目标点范围内 S>T 被伤-1——两分支均依赖目标点范围空间门，无载体，不编"])
strat("000010685002", C, "attacker", "not_modeled", notes=["+1 OC——目标点域未建模"])
strat("000010685003", C, "attacker", "partial",
      [E("attacks","modify",[1],["phase_melee"],"狂热奉献（近战武器 A+1）")],
      notes=["WHEN=冲锋或战斗阶段；+2 冲锋骰为移动域未建模；仅编近战 A+1（近战门）"])
strat("000010685004", C, "attacker", "not_modeled", notes=["被毁模型死后一击——战斗序列/复活域未建模"])
strat("000010685005", C, "attacker", "not_modeled", notes=["撤退后可射击冲锋——移动资格域未建模"])
strat("000010685006", C, "attacker", "not_modeled", notes=["目标点持续控制——目标点域未建模"])
strat("000010685007", C, "attacker", "not_modeled", notes=["敌方撤退后反应移动——移动域未建模"])
enh("000010684002", C, "target", "partial",
      [E("save","invuln",[5],[],"重征之封（携带者单位 5+ 无效保护）")], toggles=["defender_bearer_leading"],
      notes=["限携带者率领单位（点名即声明守方为携带者单位）"])
enh("000010684003", C, "attacker", "not_modeled", notes=["光环触发敌方战斗震慑——士气域未建模"])
enh("000010684004", C, "attacker", "not_modeled", notes=["宣布冲锋时重投冲锋骰——移动域未建模"])
enh("000010684005", C, "attacker", "not_modeled", notes=["对目标点范围内目标重投命中/致伤——目标点范围空间门无载体，不编"])

# ══════════════════════════════════════════════════════════════════════
# FULGURIS TASK FORCE（新分队）
C = "Fulguris Task Force"
rule("fp11e-spacemarines-fulguris", C, "not_modeled", notes=["军规：SPEEDER 关键词授予 + 首个移动阶段 ingress move——移动/部署域未建模"])
enh("fp11e-spacemarines-fulguris-e1", C, "attacker", "not_modeled", notes=["重投伤害骰与武器攻击次数骰——伤害/攻击次数重投无载体，未建模"])
enh("fp11e-spacemarines-fulguris-e2", C, "attacker", "partial",
      IGCOV("猛禽逻辑核（携带者单位远程 [无视掩体]）"), toggles=["bearer_leading"],
      notes=["限携带者（SPEEDER）单位远程武器；[无视掩体] 自含射击语义"])
strat("fp11e-spacemarines-fulguris-s1", C, "attacker", "not_modeled", notes=["敌方 +6\" 侦测范围——侦测/几何域未建模"])
strat("fp11e-spacemarines-fulguris-s2", C, "attacker", "not_modeled", notes=["反应常规移动 D3+3\"——移动域未建模"])
strat("fp11e-spacemarines-fulguris-s3", C, "attacker", "not_modeled", notes=["撤出置入战略预备队——预备队域未建模"])

# ══════════════════════════════════════════════════════════════════════
# SUBVERSION ASSETS（新分队）
C = "Subversion Assets"
rule("fp11e-spacemarines-subversion", C, "not_modeled", notes=["军规：PHOBOS/SCOUT 标记敌方 detected（+3\" 侦测范围）——侦测/标记状态域未建模"])
enh("fp11e-spacemarines-subversion-e1", C, "target", "partial",
      [E("hit","modify",[-1],["phase_shooting"],"遮蔽力场（携带者获 Stealth，被远程攻击命中-1）")],
      toggles=["defender_bearer_leading"],
      notes=["Stealth 语义=被远程攻击命中-1（射击门自含）；Lone Operative（点名限制）未建模"])
enh("fp11e-spacemarines-subversion-e2", C, "attacker", "not_modeled", notes=["对 hidden 目标 +1 命中——目标 hidden 状态门无载体，不编"])
strat("fp11e-spacemarines-subversion-s1", C, "attacker", "not_modeled", notes=["行动不阻止射击资格——行动/射击资格域未建模"])
strat("fp11e-spacemarines-subversion-s2", C, "attacker", "not_modeled", notes=["射击后保持 hidden——隐蔽状态域未建模"])
strat("fp11e-spacemarines-subversion-s3", C, "attacker", "not_modeled", notes=["-3\" 侦测范围——侦测/几何域未建模"])

# ══════════════════════════════════════════════════════════════════════
con.close()
by = {}
for e in ENTRIES:
    by[e["status"]] = by.get(e["status"], 0) + 1
by_table = {}
for e in ENTRIES:
    by_table[e["table"]] = by_table.get(e["table"], 0) + 1
print("total:", len(ENTRIES), "by_status:", by, "by_table:", by_table)

payload = {
    "_comment": ("P7 阵营技能 DSL 唯一真源（Space Marines / 通用星际战士 Codex 分队，P7-PR20）。"
    "DB effect_dsl_json/dsl_status 只是投影，由 `python -m db_compile dsl-apply` 写入并挂 restore。"
    "Space Marines FP（VERSION 1.0，2026-06-20 生效）定义 15 个分队，均挂 faction='SM'（战团/亚阵营混存）："
    "13 现有（Librarius Conclave + Armoured Speartip/Headhunter Task Force/Ceramite Sentinels/"
    "Blade of Ultramar/Hammer of Avernii/Spearpoint Task Force/Forgefather's Seekers/Emperor's Shield/"
    "Shadowmark Talon/Bastion Task Force/Orbital Assault Force/Reclamation Force，文本与 11 版 FP 逐字一致，"
    "Wahapedia 已滚入，零 text_patches）+ 2 新迷你分队（Fulguris Task Force / Subversion Assets，各 1 规则 + "
    "2 增强 + 3 战略，fp_rules inserts 补录 id 前缀 fp11e-spacemarines-）+ Bastion 漏录战略 Angels Defiant"
    "（补回 000010677006）。分队规则条目物化到 abilities 新行（spec D5）。零新引擎通道、零新态势开关"
    "（沿 PR9-19 约定）。A/B 工作单见 docs/superpowers/plans/2026-07-20-p7-pr20-spacemarines-worklist.md。"),
    "dsl_version": 1,
    "faction": "SM",
    "entries": ENTRIES,
}
Path("dsl_payloads/spacemarines.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
print("written dsl_payloads/spacemarines.json")
