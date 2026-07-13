"""engines/roster/ — 军表系统（P6）。

军表对象 + 点数重算 + 编制约束校验。数据流：
  输入（UI 搭 / 文本解析）→ Roster → recompute + validate → ValidationReport
纯数据契约（contracts）+ 分层（compose_rules/points/validate），可脱库单测、网站化复用。
"""
from engines.roster.contracts import (Roster, RosterUnit, ValidationIssue,
                                      ValidationReport)
from engines.roster.points import recompute, total_points, unit_cost
from engines.roster.validate import validate

__all__ = [
    "Roster", "RosterUnit", "ValidationIssue", "ValidationReport",
    "recompute", "total_points", "unit_cost", "validate",
]
