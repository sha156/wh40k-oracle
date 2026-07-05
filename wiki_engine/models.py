"""wiki_engine/models.py — 数据模型：EntityPage, WikiIndex, LogEntry, LintIssue。

所有模块共享的基础数据结构。YAML frontmatter 使用 PyYAML（safe_dump/safe_load），
保证序列化/解析往返对称，且与 Obsidian 标准 frontmatter（--- 包围）兼容。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ── 数据模型 ──────────────────────────────────────────────────────────

@dataclass
class WikiPageFrontmatter:
    """实体页 YAML frontmatter。

    对应 v2 蓝图 entity page schema（spec 行 108-135）。
    """
    id: str                          # 全局唯一 canonical ID：tau-empire/units/fire-warriors
    name_zh: Optional[str] = None    # 中文名
    name_en: Optional[str] = None    # 英文 canonical 名
    aliases: List[str] = field(default_factory=list)
    faction: str = ""
    type: str = ""                   # unit | stratagem | detachment | enhancement | core-rule
    points: Optional[Dict[str, int]] = None
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)  # Obsidian tag 面板用
    version: Optional[Dict[str, str]] = None       # {"points": "MFM v1.4", "rules": "..."}
    sources: List[Dict[str, object]] = field(default_factory=list)
    raw: List[str] = field(default_factory=list)   # data_refined 相对路径回链
    updated: str = ""                # ISO 日期
    verify_warn: bool = False        # LLM 合成时数字校验发现幻觉数字

    def to_yaml_text(self) -> str:
        """序列化为 YAML frontmatter 文本（不含外围 ---）。"""
        fm_dict: Dict[str, object] = {}
        field_order = [
            "id", "name_zh", "name_en", "aliases", "faction", "type",
            "points", "keywords", "tags", "version", "sources", "raw",
            "updated", "verify_warn",
        ]
        for fname in field_order:
            val = getattr(self, fname, None)
            # 跳过空值（verify_warn 仅在 True 时输出，避免全量页面噪音）
            if val is None or val == "" or val == [] or val == {}:
                continue
            if fname == "verify_warn" and not val:
                continue
            fm_dict[fname] = val
        return yaml.safe_dump(
            fm_dict,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ).rstrip("\n")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WikiPageFrontmatter":
        """从 dict 反序列化（用于解析已有 .md 文件）。"""
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        # 旧格式文件的裸日期会被 YAML 解析成 date 对象 → 统一回 ISO 字符串
        if isinstance(known.get("updated"), (date, datetime)):
            known["updated"] = known["updated"].isoformat()
        return cls(**known)

    def generate_tags(self) -> None:
        """自动生成 Obsidian tags。

        规则：type/faction 各一条，每个 keyword 一条。
        例：["unit/tau-empire", "battleline", "infantry"]
        """
        tags: List[str] = []
        if self.type and self.faction:
            tags.append("{}/{}".format(self.type, self.faction))
        if self.faction:
            tags.append(self.faction)
        if self.type:
            tags.append(self.type)
        for kw in self.keywords:
            slug = kw.lower().replace(" ", "-").replace("'", "")
            tags.append(slug)
        self.tags = sorted(set(tags))


@dataclass
class WikiPage:
    """完整 wiki 实体页：frontmatter + Markdown body。"""
    fm: WikiPageFrontmatter
    body: str                          # Markdown 正文（不含 frontmatter 外围 ---）

    def to_markdown(self) -> str:
        """渲染为文件就绪的 .md 文本。"""
        return "---\n{0}\n---\n\n{1}".format(self.fm.to_yaml_text(), self.body)

    @classmethod
    def from_markdown(cls, text: str) -> Optional["WikiPage"]:
        """从 .md 文件解析 WikiPage。

        期望格式：
        ---
        id: tau-empire/units/...
        ...
        ---
        <body>
        """
        parts = text.split("---", 2)
        if len(parts) < 3:
            return None
        frontmatter_text = parts[1]
        body = parts[2].strip()
        try:
            fm_dict = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError:
            return None
        if not isinstance(fm_dict, dict):
            return None
        return cls(fm=WikiPageFrontmatter.from_dict(fm_dict), body=body)


@dataclass
class WikiIndexEntry:
    """wiki/index.md 中的一行。"""
    path: str                        # wiki/ 内相对路径
    title_zh: Optional[str]
    title_en: Optional[str]
    faction: str
    type: str
    summary: str                     # 从 body 首段提取
    updated: str


@dataclass
class LogEntry:
    """wiki/log.md 追加条目。"""
    timestamp: str
    operation: str                   # ingest | lint | archive | rebuild
    description: str
    affected_pages: List[str] = field(default_factory=list)
    cascade_updates: List[str] = field(default_factory=list)

    def to_markdown_line(self) -> str:
        """渲染为 log.md 格式：| timestamp | operation | description | affected | cascade |"""
        return "| {0} | {1} | {2} | {3} | {4} |".format(
            self.timestamp,
            self.operation,
            self.description,
            ", ".join(self.affected_pages) if self.affected_pages else "-",
            ", ".join(self.cascade_updates) if self.cascade_updates else "-",
        )

    @classmethod
    def log_table_header(cls) -> str:
        return "| Timestamp | Operation | Description | Affected Pages | Cascade Updates |\n" \
               "|-----------|-----------|-------------|----------------|-----------------|"


@dataclass
class LintIssue:
    """一条 lint 发现。"""
    severity: str                    # error | warning | info
    rule: str                        # 规则名（如 "broken-links"）
    page_path: Optional[str]
    message: str
    auto_fixable: bool = False
    fix_description: Optional[str] = None

    def to_markdown(self) -> str:
        """渲染为 lint-report.md 中的一项。"""
        sev_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.severity, "•")
        page_str = "`{}` — ".format(self.page_path) if self.page_path else ""
        fix_str = "（可自动修复: {}）".format(self.fix_description) if self.auto_fixable else ""
        return "- {0} **[{1}]** {2}{3}{4}".format(sev_icon, self.rule, page_str, self.message, fix_str)


@dataclass
class LintResult:
    """lint 运行结果。"""
    issues: List[LintIssue] = field(default_factory=list)
    auto_fixed: int = 0
    total: int = 0

    def to_report(self) -> str:
        """生成 wiki/lint-report.md 全文。"""
        lines = [
            "# Lint Report",
            "",
            "_Generated: {}_".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]
        counts = {"error": 0, "warning": 0, "info": 0}
        for iss in self.issues:
            counts[iss.severity] = counts.get(iss.severity, 0) + 1
        for sev in ("error", "warning", "info"):
            if counts[sev] > 0:
                lines.append("| {0} | {1} |".format(sev, counts[sev]))
        lines.append("")
        lines.append("**Total issues:** {}  |  **Auto-fixed:** {}".format(self.total, self.auto_fixed))
        lines.append("")
        if self.issues:
            for iss in sorted(self.issues, key=lambda x: (0 if x.severity == "error" else 1 if x.severity == "warning" else 2)):
                lines.append(iss.to_markdown())
        else:
            lines.append("✅ 没有发现问题。")
        return "\n".join(lines) + "\n"


# ── 工具函数 ──────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """将中文/英文实体名转为文件安全的 slug。

    >>> slugify("火战士队")
    'huo-zhan-shi-dui'
    >>> slugify("Fire Warriors")
    'fire-warriors'
    """
    # 简单策略：保留字母数字和中文，其余→连字符
    result: List[str] = []
    for ch in name.strip().lower():
        if ch.isalnum() or "一" <= ch <= "鿿":
            result.append(ch)
        elif ch in " -_/":
            result.append("-")
    slug = "".join(result)
    # 压缩连续连字符
    import re
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "unnamed"


def faction_slug(faction_id: str) -> str:
    """从 faction_id 生成目录名。"""
    return slugify(faction_id or "unknown")


def entity_page_path(wiki_root: Path, fm: WikiPageFrontmatter) -> Path:
    """根据 frontmatter 推导页面的文件路径。

    规则：
      - core-rules → wiki/core-rules/<slug>.md
      - unit/stratagem/detachment/enhancement → wiki/factions/<slug>/<type>s/<name_slug>.md
    """
    if fm.type == "core-rule":
        return wiki_root / "core-rules" / "{}.md".format(slugify(fm.id))
    if fm.type in ("unit", "stratagem", "detachment", "enhancement"):
        fs = faction_slug(fm.faction)
        type_dir = "{0}s".format(fm.type)  # units, stratagems, detachments, enhancements
        name = fm.name_en or fm.name_zh or fm.id
        return wiki_root / "factions" / fs / type_dir / "{}.md".format(slugify(name))
    # fallback
    return wiki_root / "{}.md".format(slugify(fm.id))
