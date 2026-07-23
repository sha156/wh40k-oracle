"""wiki_engine/lint.py — 一致性检查与自动修复（wiki 编译器步骤⑥）。

规则：
  - broken-links：[[wikilink]] 指向不存在的文件
  - raw-backlinks：frontmatter raw: 回链的 data_refined 文件不存在
  - index-consistency：index.md 中链接指向的页面是否存在
  - missing-points：type=unit 但 points 为空
  - alias-conflicts：两个实体的 aliases 有重叠
  - faction-indexes：缺少 factions/<slug>/index.md 的阵营
"""
from __future__ import annotations

import difflib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from wiki_engine.models import (
    GENERATED_MD_NAMES,
    LintIssue,
    LintResult,
    WikiPage,
    faction_slug,
)


def scan_wiki_pages(wiki_root: Path) -> List[WikiPage]:
    """复用 build_outputs 的扫描逻辑。"""
    from wiki_engine.build_outputs import scan_wiki_pages as _scan
    return _scan(wiki_root)


def _all_md_files(wiki_root: Path) -> Set[str]:
    """返回 wiki/ 下所有 .md 文件的相对路径集合（链接目标全集）。

    注意：目标全集**不**排除生成产物——真实存在的文件都是合法链接目标
    （如 crosslinks 的 [[factions/钛帝国/index.md|钛帝国]]）。排除集只作用
    在"扫描哪些文件的出链"一侧，见 _iter_source_md_files。
    """
    files: Set[str] = set()
    for md_file in wiki_root.rglob("*.md"):
        rel = str(md_file.relative_to(wiki_root)).replace("\\", "/")
        files.add(rel)
    return files


def _iter_source_md_files(wiki_root: Path):
    """遍历应作为"出链来源"检查的 .md 文件：排除流水线生成产物。

    排除集与 build_outputs.scan_wiki_pages 对齐（models.GENERATED_MD_NAMES），
    否则 lint 会扫描自己生成的 lint-report.md，把报告里的 [[断链示例]]
    当成新断链，假阳性永久自我复现（H15）。
    """
    for md_file in sorted(wiki_root.rglob("*.md")):
        if md_file.name in GENERATED_MD_NAMES:
            continue
        yield md_file


# ── 各 lint 规则 ──────────────────────────────────────────────────────

def check_broken_links(wiki_root: Path) -> List[LintIssue]:
    """检查所有 [[wikilink]] 是否指向存在的文件（生成产物不作为出链来源扫描）。"""
    all_files = _all_md_files(wiki_root)
    # 也允许不带 .md 后缀的链接（Obsidian 风格）
    all_targets = all_files | {f.replace(".md", "") for f in all_files}
    issues: List[LintIssue] = []

    for md_file in _iter_source_md_files(wiki_root):
        rel = str(md_file.relative_to(wiki_root)).replace("\\", "/")
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # 提取所有 [[target|display]] 或 [[target]]。表格内的 wikilink 用 \\| 转义别名
        # 竖线（避免与表格列分隔符冲突），此时 target 会带尾随反斜杠——剥掉再判存在性，
        # 否则会把全部表格内链接误报为断链并被 --fix 反向去转义（破坏 Obsidian 渲染）。
        for m in re.finditer(r"\[\[([^\]|#]+?)(?:\\?\|[^\]]+?)?\]\]", text):
            target = m.group(1).strip().rstrip("\\")
            if target not in all_targets:
                # 找最相似的文件名用于建议修复
                suggestion = None
                close = difflib.get_close_matches(target, list(all_targets), n=1, cutoff=0.6)
                if close:
                    suggestion = close[0]
                issues.append(LintIssue(
                    severity="error",
                    rule="broken-links",
                    page_path=rel,
                    message="断链: [[{}]]".format(target),
                    auto_fixable=suggestion is not None,
                    fix_description="建议替换为 [[{}]]".format(suggestion) if suggestion else None,
                ))
    return issues


def check_raw_backlinks(
    wiki_root: Path,
    refined_root: Path,
) -> List[LintIssue]:
    """检查 frontmatter raw: 回链是否指向实际存在的 data_refined 文件。"""
    issues: List[LintIssue] = []
    pages = scan_wiki_pages(wiki_root)

    for page in pages:
        if not page.fm.raw:
            continue
        for raw_rel in page.fm.raw:
            # raw 格式: data_refined/Book Name/page_NNN.md 或 ../../data_refined/...
            raw_path = Path(raw_rel.replace("\\", "/"))
            if raw_path.is_absolute():
                exists = raw_path.exists()
            else:
                # 尝试相对于 wiki/ 和项目根目录
                candidate = wiki_root / raw_rel
                if not candidate.exists():
                    candidate = refined_root.parent / raw_rel
                exists = candidate.exists()

            if not exists:
                # 找到页面路径用于报告
                from wiki_engine.models import entity_page_path as _entity_page_path
                page_path = _entity_page_path(wiki_root, page.fm)
                rel_page = str(page_path.relative_to(wiki_root)).replace("\\", "/") if page_path else page.fm.id

                issues.append(LintIssue(
                    severity="warning",
                    rule="raw-backlinks",
                    page_path=rel_page,
                    message="raw 回链无效: {}".format(raw_rel),
                    auto_fixable=False,
                ))
    return issues


def check_index_consistency(wiki_root: Path) -> List[LintIssue]:
    """检查 index.md 中每个链接是否指向存在的页面。"""
    issues: List[LintIssue] = []
    index_path = wiki_root / "index.md"
    if not index_path.exists():
        issues.append(LintIssue(
            severity="error",
            rule="index-consistency",
            page_path="index.md",
            message="wiki/index.md 不存在",
            auto_fixable=False,
        ))
        return issues

    all_files = _all_md_files(wiki_root)
    all_targets = all_files | {f.replace(".md", "") for f in all_files}

    text = index_path.read_text(encoding="utf-8")
    # 提取 Markdown 链接 [name](path) 和 [[path]]
    for m in re.finditer(r"\[([^\]]*?)\]\(([^)]+?)\)", text):
        path = m.group(2).strip()
        # 去掉 .md 后缀用于匹配
        if path.endswith(".md"):
            path = path[:-3]
        if path and path not in all_targets:
            issues.append(LintIssue(
                severity="warning",
                rule="index-consistency",
                page_path="index.md",
                message="索引链接无效: [{}]({})".format(m.group(1), m.group(2)),
                auto_fixable=False,
            ))
    return issues


def check_missing_points(wiki_root: Path) -> List[LintIssue]:
    """检查 type=unit 但 points 为空的页面。"""
    issues: List[LintIssue] = []
    pages = scan_wiki_pages(wiki_root)

    for page in pages:
        if page.fm.type != "unit":
            continue
        if not page.fm.points:
            from wiki_engine.models import entity_page_path
            rel = str(entity_page_path(wiki_root, page.fm).relative_to(wiki_root)).replace("\\", "/")
            issues.append(LintIssue(
                severity="info",
                rule="missing-points",
                page_path=rel,
                message="单位页缺少 points 字段",
                auto_fixable=False,
            ))
    return issues


def check_alias_conflicts(wiki_root: Path) -> List[LintIssue]:
    """检查两个实体的 aliases 或名称是否有重叠。"""
    issues: List[LintIssue] = []
    pages = scan_wiki_pages(wiki_root)

    # 收集所有名称 → 页面映射
    name_map: Dict[str, List[str]] = defaultdict(list)
    for page in pages:
        names: List[str] = []
        if page.fm.name_zh:
            names.append(page.fm.name_zh)
        if page.fm.name_en:
            names.append(page.fm.name_en)
        names.extend(page.fm.aliases)
        for name in names:
            name = name.strip().lower()
            if name:
                name_map[name].append(page.fm.id)

    for name, page_ids in name_map.items():
        if len(page_ids) > 1:
            issues.append(LintIssue(
                severity="warning",
                rule="alias-conflicts",
                page_path=None,
                message="名称/别名冲突: '{}' 被 {} 同时使用".format(
                    name, ", ".join(page_ids)),
                auto_fixable=False,
            ))
    return issues


def check_faction_indexes(wiki_root: Path) -> List[LintIssue]:
    """检查有实体页的阵营是否都有 factions/<slug>/index.md。"""
    issues: List[LintIssue] = []
    pages = scan_wiki_pages(wiki_root)

    factions_seen: Set[str] = set()
    for page in pages:
        if page.fm.faction:
            factions_seen.add(page.fm.faction)

    for faction in sorted(factions_seen):
        fs = faction_slug(faction)
        index_path = wiki_root / "factions" / fs / "index.md"
        if not index_path.exists():
            issues.append(LintIssue(
                severity="warning",
                rule="faction-indexes",
                page_path="factions/{}/".format(fs),
                message="缺少阵营索引页 factions/{}/index.md".format(fs),
                auto_fixable=True,
                fix_description="运行 wiki_engine build 自动生成",
            ))
    return issues


def check_frontmatter_parse(wiki_root: Path) -> List[LintIssue]:
    """M7：frontmatter 解析失败的页面会被 scan_wiki_pages 静默丢弃，
    从索引/其余 lint 规则里凭空消失——这里显式报 error，不让页面无声脱队。

    排除生成产物（GENERATED_MD_NAMES）以及 review_needed.md 及其备份
    （wiki_compile terms 产物，本就没有 frontmatter）。
    """
    issues: List[LintIssue] = []
    for md_file in _iter_source_md_files(wiki_root):
        if md_file.name.startswith("review_needed."):
            continue
        if md_file.name == "CLAUDE.md":
            # wiki 宪法按其 §11 设计不带 frontmatter（避免被扫进实体索引），
            # 不是"无声脱队"的实体页——显式跳过
            continue
        rel = str(md_file.relative_to(wiki_root)).replace("\\", "/")
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            issues.append(LintIssue(
                severity="error",
                rule="frontmatter-parse",
                page_path=rel,
                message="文件读取失败（{}），该页已脱离索引体系".format(e),
                auto_fixable=False,
            ))
            continue
        if WikiPage.from_markdown(text) is None:
            issues.append(LintIssue(
                severity="error",
                rule="frontmatter-parse",
                page_path=rel,
                message="frontmatter 解析失败，该页已脱离索引体系",
                auto_fixable=False,
            ))
    return issues


def check_verify_warnings(wiki_root: Path) -> List[LintIssue]:
    """检查 frontmatter verify_warn=True 的页面（LLM 合成时数字校验命中幻觉数字）。"""
    issues: List[LintIssue] = []
    pages = scan_wiki_pages(wiki_root)

    for page in pages:
        if not page.fm.verify_warn:
            continue
        from wiki_engine.models import entity_page_path
        try:
            rel = str(entity_page_path(wiki_root, page.fm).relative_to(wiki_root)).replace("\\", "/")
        except ValueError:
            rel = page.fm.id
        issues.append(LintIssue(
            severity="warning",
            rule="verify-warn",
            page_path=rel,
            message="LLM 合成时数字校验发现原文没有的数字，需人工核对",
            auto_fixable=False,
        ))
    return issues


# ── 规则注册表 ────────────────────────────────────────────────────────

LINT_RULES: List[Callable] = [
    check_broken_links,
    check_alias_conflicts,
    check_index_consistency,
    check_faction_indexes,
    check_missing_points,
    check_verify_warnings,
    check_frontmatter_parse,
    # check_raw_backlinks 需要 refined_root 参数，单独调用
]


# ── 自动修复 ──────────────────────────────────────────────────────────

def auto_fix_broken_links(issues: List[LintIssue], wiki_root: Path) -> int:
    """自动修复确定的断链：用编辑距离匹配替换为最接近的有效路径。"""
    fixed = 0
    # 按文件分组
    by_file: Dict[str, List[LintIssue]] = defaultdict(list)
    for iss in issues:
        if iss.auto_fixable and iss.page_path and iss.rule == "broken-links":
            by_file[iss.page_path].append(iss)

    for file_rel, file_issues in by_file.items():
        file_path = wiki_root / file_rel
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        modified = False
        for iss in file_issues:
            if iss.fix_description:
                # 从 fix_description 提取建议的新链接
                # 格式: "建议替换为 [[new_target]]"
                m = re.search(r"\[\[(.+?)\]\]", iss.fix_description or "")
                if m:
                    new_target = m.group(1)
                    # 在文本中查找并替换断链
                    old_link = iss.message.replace("断链: [[", "").replace("]]", "")
                    # 匹配 [[old_link]] 和 [[old_link|任意显示文本]]
                    old_pattern_wrapped = "[[{}]]".format(old_link)
                    old_pattern_piped = "[[{}|".format(old_link)
                    if old_pattern_wrapped in text:
                        text = text.replace(old_pattern_wrapped, "[[{}]]".format(new_target))
                        modified = True
                        fixed += 1
                    elif old_pattern_piped in text:
                        # 替换 [[old_link|display]] → [[new_target|display]]
                        text = re.sub(
                            r"\[\[" + re.escape(old_link) + r"\|([^\]]+)\]\]",
                            r"[[{}|\1]]".format(new_target),
                            text,
                        )
                        modified = True
                        fixed += 1
        if modified:
            file_path.write_text(text, encoding="utf-8")
    return fixed


# ── 主入口 ────────────────────────────────────────────────────────────

def run_lint(
    wiki_root: Path,
    refined_root: Optional[Path] = None,
    pairing_path: Optional[Path] = None,
    auto_fix: bool = True,
) -> LintResult:
    """运行全部 lint 规则，可选自动修复。"""
    all_issues: List[LintIssue] = []

    # 运行通用规则
    for rule_fn in LINT_RULES:
        try:
            all_issues.extend(rule_fn(wiki_root))
        except Exception as e:  # noqa: BLE001
            all_issues.append(LintIssue(
                severity="error",
                rule="lint-error",
                page_path=None,
                message="规则 {} 执行失败: {}".format(rule_fn.__name__, e),
            ))

    # raw-backlinks 需要 refined_root
    if refined_root and refined_root.is_dir():
        try:
            all_issues.extend(check_raw_backlinks(wiki_root, refined_root))
        except Exception as e:  # noqa: BLE001
            all_issues.append(LintIssue(
                severity="error",
                rule="lint-error",
                page_path=None,
                message="raw-backlinks 规则执行失败: {}".format(e),
            ))

    # 自动修复
    auto_fixed = 0
    if auto_fix:
        auto_fixed = auto_fix_broken_links(all_issues, wiki_root)

    return LintResult(issues=all_issues, auto_fixed=auto_fixed, total=len(all_issues))


def generate_lint_report(result: LintResult, wiki_root: Path) -> Path:
    """生成 wiki/lint-report.md，返回文件路径。"""
    report_path = wiki_root / "lint-report.md"
    report_path.write_text(result.to_report(), encoding="utf-8")
    return report_path
