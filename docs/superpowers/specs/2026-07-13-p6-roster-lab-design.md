# P6 军表系统 —— 立项设计（spec v1）

> 蓝图 T3 / BUILD-PLAN 第 6 件。前置已就位：P4/P5 模拟器、`calc_points`、实体解析器、
> 结构库（`db/wh40k.sqlite` 已是 11 版数值真源）。本 spec 照 P4/P5 惯例先立项再开工。
> 三项根本决策已与用户敲定（见文末「决策记录」）。

## 一、要解决的问题

用户手里一份 2000 分军表，想知道三件事：
1. **合法吗**——总分没超、每个单位点数对、编制约束（warlord/强化/battleline）满足；
2. **强不强**——这套配置打得动主流对手吗（接 P4/P5 模拟器做强度评估）；
3. **改一行会怎样**——增删单位/换装即时看点数与合法性变化。

现状：这些能力零散在 `calc_points`（能算分）和模拟器（能对战）里，没有「军表」这个一等对象把
它们串起来，也没有编制合法性校验。P6 建 `engines/roster/` 补齐蓝图 L4 最后一块。

## 二、范围边界（P6 做 / 不做，硬划线）

### 首期（PR1）做
- **军表对象**：一份军表 = 阵营 + detachment + 单位列表（每单位带 canonical_id / 模型数 / loadout / 是否 warlord / 挂的 enhancement）。
- **两个输入入口**：① UI 逐单位搭建（复用图鉴选择器）；② 粘贴导出文本（BattleScribe / 官方 App）→ 解析。
- **验表**：点数 + 编制约束（下方第五节逐条）。
- **最小面板**：搭表 → 算分 → 报合法性（红/黄/绿），跑通闭环。

### 后续 PR
- **PR2 点评档**：接模拟器给「这套配置强度评估」（每单位性价比、对典型目标的期望输出、明显短板）。
- **PR3 实时重算 + web 页签**：改一行即时重算；Stage 4 第四页签 `/roster`（前端复用契约真源模式）。

### 明确不碰
- **对战列表构筑合法性的完整规则**（任务卡、次要目标、地形部署）——超出「军表校验」范畴。
- **阵营/分队规则的数值生效**——P5 已裁「宁漏不错，只 surface 不施加」，P6 沿用；点评只用已建模的武器/USR 效果。
- **多分队 / 联盟军**——首期单 detachment。

## 三、数据就绪度盘点（实测 2026-07-13，`db/wh40k.sqlite`）

### 够用的（首期验表能直接吃）
- **单位关键词** `units.keywords_json`：CHARACTER 686 / BATTLELINE 92 / EPIC HERO 222 /
  DEDICATED TRANSPORT 70 / INFANTRY 937 / FORTIFICATION 45（共 1715 单位）。
  → warlord 资格（须 CHARACTER）、battleline 识别、Rule of Three 豁免（battleline/dedicated
  transport）全查得到。
- **点数** `calc_points` / `points_json`：按 canonical_id 查，MFM 真源，1224/1224 校验一致。
- **detachment 清单** `detachments`（284 行，带 `faction`/`name_en`/`rule_text`）。

### 缺的（首期必须先补的数据层子任务）
- **⚠️ 强化清单 `detachments.enhancements_json` = 0/284 全空**。要验「enhancement ≤3、仅
  CHARACTER、每分队唯一、非 EPIC HERO」必须有每分队的强化名单 + 点数。
  → **PR1 前置子任务 `db_compile enhancements`**：从 Wahapedia/BSData 抽强化名+点数+归属分队
  灌进 `enhancements_json`（照 fp_errata 惯例带 from 守卫 + restore 挂钩防重建丢）。
  数据补齐前，enhancement 校验降级为「surface 未校验」诚实标注，不假装通过。

### 核心规则常量（无数据缺口，写进代码常量）
- 军表规模：Incursion 1000 / Strike Force 2000 / Onslaught 3000。
- 强化：0-3 个，每个唯一，仅 CHARACTER（非 EPIC HERO），每 CHARACTER 至多 1 个。
- warlord：恰好 1 个 CHARACTER。
- Rule of Three：同一 datasheet 至多 3 份（battleline / dedicated transport 例外，上限更高）。

## 四、模块结构 `engines/roster/`（照 `engines/simulator/` 惯例：纯数据契约 + 分层）

```
engines/roster/
  contracts.py     # RosterUnit / Roster / ValidationIssue / ValidationReport（frozen dataclass，零依赖）
  points.py        # 军表逐单位/总分重算（薄封装 calc_points，按 canonical_id）
  validate.py      # 编制约束校验 → List[ValidationIssue]（每条带 severity + 规则锚点 + 诚实降级标注）
  compose_rules.py # 核心规则常量（规模档/强化/warlord/RoT）+ 关键词判定辅助
  parse.py         # 粘贴文本 → Roster（BattleScribe/App 格式，容错解析，无法解析的行显式列出不静默丢）
  __init__.py
```
数据流：`输入（UI 搭 / parse 文本）→ Roster → points.recompute + validate → ValidationReport`。

## 五、验表规则清单（PR1 逐条，每条 severity + 是否可从现有数据判）

| 规则 | severity | 数据 | 判法 |
|---|---|---|---|
| 总分 ≤ 规模档上限 | error | ✅ | Σ 单位点数 vs 档位常量 |
| 每单位点数对齐 MFM | warn | ✅ | calc_points vs 军表声明（防手输错） |
| 恰好 1 warlord | error | ✅ | count(is_warlord)==1 且该单位含 CHARACTER |
| warlord 必须 CHARACTER | error | ✅ | keyword 判定 |
| 同 datasheet ≤3（RoT） | error | ✅ | 计数，battleline/dedicated transport 豁免 |
| enhancement ≤3 且唯一 | error | ⚠️缺 | enhancements_json 补齐后启用；缺则 surface「未校验」 |
| enhancement 仅 CHARACTER 非 EPIC HERO | error | ⚠️缺 | 同上 |
| 单位模型数在编制内 | warn | 部分 | models 表有档位则校验，否则 surface |

诚实降级红线：数据缺口一律 surface「此项未校验」，**绝不默认判通过**（对照 P5 surface-don't-fake）。

## 六、数据契约（`contracts.py` 草案）

```python
@dataclass(frozen=True)
class RosterUnit:
    canonical_id: str
    name_en: str
    models: int
    loadout: Tuple[Tuple[str, int], ...]   # 复用模拟器 loadout 格式
    is_warlord: bool = False
    enhancement: Optional[str] = None
    points: Optional[int] = None            # recompute 后填

@dataclass(frozen=True)
class Roster:
    faction_id: str
    detachment_id: Optional[str]
    size: str                               # incursion|strike_force|onslaught
    units: Tuple[RosterUnit, ...]

@dataclass(frozen=True)
class ValidationIssue:
    code: str                               # points_over / warlord_count / rot_exceeded / enh_unverified …
    severity: str                           # error|warn|info
    message: str
    anchor: str = ""                        # 11版规则锚点
    surfaced_only: bool = False             # True=数据缺口未真校验（诚实降级）

@dataclass(frozen=True)
class ValidationReport:
    total_points: int
    limit: int
    legal: bool                             # 无 error（surfaced_only 不算 error）
    issues: Tuple[ValidationIssue, ...]
```

## 七、输入层双入口

- **UI 搭建**：复用图鉴 `UnitPicker` 选阵营→单位，加「加入军表」；军表区每行可设模型数/装备/warlord/强化。
- **文本粘贴**：`parse.py` 吃 BattleScribe/官方 App 导出。策略同「PDF 勿用固定正则」教训——
  多格式容错，逐行匹配单位名（走实体解析器 canonical_id），**无法解析的行显式回报**（不静默丢，
  对照批量任务对账纪律）。解析出的军表进 UI 供二次编辑，不直接跑。

## 八、里程碑（PR 拆分，每步可验证产出）

- **PR1a 数据层**：`db_compile enhancements` 补 `enhancements_json`（284 分队），带对账（目标 vs 实际）。
- **PR1b 引擎**：`engines/roster/` contracts + points + validate + compose_rules，纯 pytest 覆盖
  每条规则（含数据缺口的 surfaced_only 自证）。
- **PR1c 面板 + parse**：最小 Streamlit 面板（搭表→算分→合法性）+ 文本解析，AppTest 端到端。
- **PR2**：点评档（接 `simulate_combat` 批量评估）。
- **PR3**：实时重算 + Stage 4 `/roster` web 页签（`web_api` 端点 + 前端契约镜像）。

## 九、风险与应对

| 风险 | 应对 |
|---|---|
| 强化数据抓取质量（Wahapedia 滚更） | 照 fp_errata 惯例带 from 守卫 + restore 挂钩；补齐前 surfaced_only 降级 |
| BattleScribe 格式碎片化 | 首期只保证官方 App + BattleScribe 两种主流；无法解析行显式回报，不猜 |
| RoT 豁免边界（battleline 上限） | 查 11 版核心规则确切上限写常量，附锚点；不确定的 warn 不 error |
| 编制约束「宁漏不错」尺度 | 沿用 P5 裁决：能确定判的 error，数据不足的 surface，绝不假通过 |

## 十、决策记录（2026-07-13 与用户敲定）

1. **军表输入 = UI 搭建 + 文本粘贴双入口**（两条路径都维护）。
2. **验表深度 = 点数 + 编制约束**（warlord / enhancement / battleline），需补 enhancement 数据。
3. **首期 = 验表 MVP 先闭环**（PR1），点评档 PR2，实时重算 + web 页签 PR3。

## 自审清单
- [x] 三项决策已落文
- [x] 数据就绪度实测（非假设）：keywords 齐、enhancements_json 0/284 缺口已定位
- [x] 模块结构照 engines/simulator/ 惯例
- [x] 诚实降级红线贯穿（数据缺口 surface 不假通过）
- [x] PR 拆分每步可验证、ADHD 友好（PR1a 数据→1b 引擎→1c 面板）
- [ ] 待用户确认后开工 PR1a
