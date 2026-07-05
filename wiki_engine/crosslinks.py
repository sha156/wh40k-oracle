"""wiki_engine/crosslinks.py — 自动 [[wikilink]] 注入（wiki 编译器步骤④）。

扫描 wiki/ 所有实体页，建立名→路径索引，在正文中关键词首次出现处注入 Obsidian [[链接]]。
纯代码实现，零 LLM 调用。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from wiki_engine.models import WikiPage, WikiPageFrontmatter


def _parse_frontmatter_yaml(text: str) -> Optional[Dict]:
    """从 .md 文件中解析 YAML frontmatter（标准 PyYAML 解析）。"""
    import yaml
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        result = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(result, dict):
        return None
    return result


def load_link_targets(pages_dir: Path) -> Dict[str, str]:
    """扫描 wiki/ 下所有 .md 文件，构建 {名称: 相对路径} 索引。

    索引键包含：中文名、英文名、所有别名。
    值为 wiki/ 根目录下的相对路径（用于 [[path|name]] 语法）。
    """
    targets: Dict[str, str] = {}
    for md_file in sorted(pages_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = _parse_frontmatter_yaml(text)
        if fm is None:
            continue
        rel_path = str(md_file.relative_to(pages_dir)).replace("\\", "/")

        # 注册各种名称
        names_found: List[str] = []
        for key in ("name_zh", "name_en"):
            val = fm.get(key)
            if val and isinstance(val, str):
                names_found.append(val)
        # 别名
        aliases_val = fm.get("aliases")
        if isinstance(aliases_val, list):
            for a in aliases_val:
                if isinstance(a, str):
                    names_found.append(a)

        for name in names_found:
            name = name.strip()
            if name and name not in targets:
                targets[name] = rel_path

    return targets


def inject_wikilinks(
    page: WikiPage,
    link_targets: Dict[str, str],
    term_aliases: Optional[Dict[str, str]] = None,
) -> WikiPage:
    """在 page.body 中扫描已知实体名，首次出现处注入 [[path|name]]。

    规则：
      - 每个实体名在正文中首次出现时加链接
      - 不链接自身（page.fm 中已有的名称）
      - 用 (?:^|\\s|[(（]) 前缀边界避免子串误匹配

    返回新的 WikiPage（不可变模式——创建新对象）。
    """
    body = page.body
    # 构建"不链接自己"的名称集合
    self_names: Set[str] = set()
    if page.fm.name_zh:
        self_names.add(page.fm.name_zh)
    if page.fm.name_en:
        self_names.add(page.fm.name_en)
    for alias in page.fm.aliases:
        self_names.add(alias)

    # 将别名映射也加入候选（社区译名 → wiki 页名）
    if term_aliases:
        for alias, target_en in term_aliases.items():
            if target_en in link_targets and alias not in link_targets:
                link_targets[alias] = link_targets[target_en]

    # 按名称长度降序排列，优先匹配长的（避免"火战士"在"火战士队"前面误匹配）
    candidates = sorted(
        [(n, p) for n, p in link_targets.items() if n not in self_names],
        key=lambda x: -len(x[0]),
    )

    # 记录每个名称是否已经链接过
    linked: Set[str] = set()
    modified = False

    for name, path in candidates:
        if name in linked or len(name) < 2:
            continue
        # 用正则查找 name 在正文中的第一次出现（不在已有 [[...]] 内）
        # 不使用 \w 边界（Python 3 中 \w 匹配 CJK 字符，会导致中文匹配失败）
        pattern = re.compile(
            r"({})".format(re.escape(name)),
        )
        match = pattern.search(body)
        if match:
            start, end = match.start(1), match.end(1)
            # 检查是否已在 wikilink 内（前后 3 字符内有 [[ 或 ]]）
            before = body[max(0, start - 3):start]
            after = body[end:end + 3]
            if "[[" in before or "]]" in after:
                continue
            # 注入链接
            link = "[[{}|{}]]".format(path, name)
            body = body[:start] + link + body[end:]
            linked.add(name)
            modified = True

    if modified:
        return WikiPage(fm=page.fm, body=body)
    return page


def inject_all(
    pages_dir: Path,
    terms_path: Optional[Path] = None,
) -> List[str]:
    """遍历 wiki/ 所有实体页，注入交叉链接后写回。

    返回修改的文件相对路径列表。
    """
    targets = load_link_targets(pages_dir)
    if not targets:
        print("未找到可链接的 wiki 页面。")
        return []

    term_aliases: Optional[Dict[str, str]] = None
    if terms_path and terms_path.exists():
        import json
        try:
            data = json.loads(terms_path.read_text(encoding="utf-8"))
            term_aliases = {p["zh"]: p["en"] for p in data.get("pairs", [])
                            if p.get("zh") and p.get("en")}
        except (json.JSONDecodeError, KeyError):
            pass

    modified: List[str] = []
    for md_file in sorted(pages_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        parsed = WikiPage.from_markdown(text)
        if parsed is None:
            continue

        result = inject_wikilinks(parsed, dict(targets), term_aliases)
        new_text = result.to_markdown()
        if new_text != text:
            md_file.write_text(new_text, encoding="utf-8")
            rel = str(md_file.relative_to(pages_dir)).replace("\\", "/")
            modified.append(rel)

    print("交叉链接: {} 页已更新".format(len(modified)))
    return modified


# ── re-export for test convenience ──
__all__ = ["load_link_targets", "inject_wikilinks", "inject_all"]
