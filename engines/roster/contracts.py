"""engines/roster/contracts.py — 军表纯数据契约（P6-PR1b，零依赖）。

军表 = 阵营 + detachment + 单位列表。校验产出带 severity + 规则锚点的 issue 清单。
诚实降级：数据缺口的 issue 标 surfaced_only=True（未真校验），不混入 error 判死刑。
仿 engines/simulator/contracts.py：frozen dataclass，可脱库单测、网站化直接复用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

# severity
ERROR = "error"     # 违反硬规则 → 军表非法
WARN = "warn"       # 可疑但不必然非法（如模型数无法定价）
INFO = "info"       # 提示


@dataclass(frozen=True)
class RosterUnit:
    """军表里的一个单位条目。points 由 recompute 填（None=未定价）。"""
    canonical_id: str
    name_en: str
    models: int
    is_warlord: bool = False
    enhancement: Optional[str] = None          # 强化名（英文权威名）
    loadout: Tuple[Tuple[str, int], ...] = ()  # 预留：接模拟器/点评用
    points: Optional[int] = None


@dataclass(frozen=True)
class Roster:
    faction_id: str
    detachment_id: Optional[str]
    size: str                                  # incursion|strike_force|onslaught
    units: Tuple[RosterUnit, ...] = ()


@dataclass(frozen=True)
class ValidationIssue:
    code: str                                  # points_over / warlord_count / ...
    severity: str
    message: str
    anchor: str = ""                           # 11 版规则锚点
    surfaced_only: bool = False                # True=数据缺口未真校验（诚实降级）


@dataclass(frozen=True)
class ValidationReport:
    total_points: int
    limit: int
    legal: bool                                # 无 error（surfaced_only 不算 error）
    issues: Tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def errors(self) -> Tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == ERROR)

    @property
    def warnings(self) -> Tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == WARN)
