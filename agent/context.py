"""agent/context.py — 会话上下文骨架（spec 第七节「会话上下文」）。

纯内存结构，不落盘；生命周期由宿主 UI 持有（Streamlit 阶段用 session_state，
网站阶段用服务端内存 session，均在本迭代范围之外）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SessionContext:
    """记住用户军表/阵营等会话级状态，供 Agent 循环解析"我的军表"之类的指代。"""

    roster_text: Optional[str] = None
    faction: Optional[str] = None
    history: List[Dict[str, str]] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)

    def remember_roster(self, roster_text: str, faction: Optional[str] = None) -> None:
        self.roster_text = roster_text
        if faction:
            self.faction = faction

    def append_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
