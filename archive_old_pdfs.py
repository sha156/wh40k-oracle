"""归档旧版 PDF → data/archive/，确保 L1 只处理最新版本。

流程：
  1. 扫描 data/*.pdf，按阵营/书名分组
  2. 每组内识别最新版（保留）vs 旧版（归档）
  3. --dry-run 预览，确认后执行移动

选择规则：
  - 英文：Faction Pack 系列优先于社区翻译
  - 中文：文件修改时间最新的优先
  - 同一语言内有多个版本时，保留最新的、归档其余的
  - 中英文各保留一份（如同时存在英文 Faction Pack 和中文汉化版）
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ── 阵营关键词 → 标准化 slug ──────────────────────────────────────────
# 用于将中英文文件名映射到统一的阵营标识
_FACTION_KEYWORDS: Dict[str, str] = {
    # English Faction Pack names
    "Adepta Sororitas": "adepta-sororitas",
    "Adeptus Custodes": "adeptus-custodes",
    "Adeptus Mechanicus": "adeptus-mechanicus",
    "Adeptus Titanicus": "adeptus-titanicus",
    "Aeldari": "aeldari",
    "Astra Militarum": "astra-militarum",
    "Black Templars": "black-templars",
    "Blood Angels": "blood-angels",
    "Chaos Daemons": "chaos-daemons",
    "Chaos Knights": "chaos-knights",
    "Chaos Space Marines": "chaos-space-marines",
    "Dark Angels": "dark-angels",
    "Death Guard": "death-guard",
    "Deathwatch": "deathwatch",
    "Drukhari": "drukhari",
    "Emperor S Children": "emperors-children",
    "Genestealer Cults": "genestealer-cults",
    "Grey Knights": "grey-knights",
    "Imperial Agents": "imperial-agents",
    "Imperial Knights": "imperial-knights",
    "Leagues Of Votann": "leagues-of-votann",
    "Necrons": "necrons",
    "Orks": "orks",
    "Space Wolves": "space-wolves",
    "Space-Marines": "space-marines",
    "Tau Empire": "tau-empire",
    "Thousand Sons": "thousand-sons",
    "Tyranids": "tyranids",
    "World Eaters": "world-eaters",
    # Chinese faction names
    "战斗修女": "adepta-sororitas",
    "禁军": "adeptus-custodes",
    "机械修会": "adeptus-mechanicus",
    "机械教": "adeptus-mechanicus",
    "艾达灵族": "aeldari",
    "星界军": "astra-militarum",
    "黑色圣堂": "black-templars",
    "圣血天使": "blood-angels",
    "混沌恶魔": "chaos-daemons",
    "混沌骑士": "chaos-knights",
    "混沌星际战士": "chaos-space-marines",
    "混沌": "chaos-space-marines",
    "黑暗天使": "dark-angels",
    "死亡守卫": "death-guard",
    "死亡守望": "deathwatch",
    "黑暗灵族": "drukhari",
    "帝皇之子": "emperors-children",
    "基因窃取者": "genestealer-cults",
    "灰骑士": "grey-knights",
    "帝国特勤": "imperial-agents",
    "帝国骑士": "imperial-knights",
    "沃坦联盟": "leagues-of-votann",
    "太空死灵": "necrons",
    "兽人": "orks",
    "太空野狼": "space-wolves",
    "星际战士": "space-marines",
    "钛帝国": "tau-empire",
    "千子军团": "thousand-sons",
    "千子": "thousand-sons",
    "泰伦虫族": "tyranids",
    "吞世者": "world-eaters",
    # Special / non-faction books
    "Core Rules": "core-rules",
    "Event Companion": "event-companion",
    "Terrain": "terrain",
    "核心规则": "core-rules",
    "总规则": "core-rules",
    "总规": "core-rules",
    "规则注解": "core-rules-annotation",
    "通用技能速查表": "usr-quick-ref",
    "分数": "points",
}

# ── 特殊书名（不按阵营分组，单独处理）──────────────────────────────
_SPECIAL_BOOKS = {
    "core-rules", "core-rules-annotation", "event-companion",
    "terrain", "usr-quick-ref", "points",
}


def _detect_faction_key(stem: str) -> Optional[str]:
    """从文件名 stem 推断阵营 key。

    按关键词长度降序匹配，避免短关键词误命中（"千子" 先于 "千"）。
    """
    sorted_kw = sorted(_FACTION_KEYWORDS.keys(), key=len, reverse=True)
    for kw in sorted_kw:
        if kw.lower() in stem.lower():
            return _FACTION_KEYWORDS[kw]
    return None


# ── 版本格式优先级（评审 M#8）──────────────────────────────────────
# 完整 8 位日期 > V 版本号 > 小数版本号 > 4 位数字 > 无版本。
# 4 位数字（0115/1112/0308）语义歧义（MMDD? YYMM?），不再伪造成年份参与
# 跨格式比较（"0308"→(2003,8) > "0115"→(2001,15) 纯属巧合）；仅在同为
# 4 位数字格式时按数值比较，且同组出现多个 4 位数字文件时跳过归档交人工
# 确认——宁可不归档也不误归档（e67a3676 假归档教训）。
_FMT_NONE, _FMT_DIGIT4, _FMT_DECIMAL, _FMT_V, _FMT_DATE8 = 0, 1, 2, 3, 4


def _parse_version_date(stem: str) -> Tuple[int, Tuple[int, ...]]:
    """从文件名中提取版本号或日期，返回 (格式优先级, 数值元组)。

    识别模式（按优先级从高到低）：
      - 纯日期：20251112 → (_FMT_DATE8, (2025, 11, 12))
      - V 前缀：V1.20 → (_FMT_V, (1, 20))
      - 小数版本：1.13, 2.81 → (_FMT_DECIMAL, (major, minor))
      - 4 位数字：0115 → (_FMT_DIGIT4, (115,))——不猜语义，仅同格式内比数值
      - 其他：(_FMT_NONE, (0,))

    元组直接可比：先比格式优先级（高优先级格式视为更可信的"新"判据），
    同格式再比数值，越大越新。
    """
    m = re.search(r"(\d{4})(\d{2})(\d{2})", stem)
    if m:
        return (_FMT_DATE8, (int(m.group(1)), int(m.group(2)), int(m.group(3))))
    # V 前缀版本号
    m = re.search(r"[Vv](\d+)\.(\d+)", stem)
    if m:
        return (_FMT_V, (int(m.group(1)), int(m.group(2))))
    # 小数版本号（在文件名末尾或空格后）
    m = re.search(r"(?<!\d)(\d+)\.(\d+)(?!\d)", stem)
    if m:
        return (_FMT_DECIMAL, (int(m.group(1)), int(m.group(2))))
    # 4 位数字：MMDD 还是 YYMM 无法确定，保留原始数值，仅供同格式比较
    m = re.search(r"(?<!\d)(\d{4})(?!\d)", stem)
    if m:
        return (_FMT_DIGIT4, (int(m.group(1)),))
    return (_FMT_NONE, (0,))


def _four_digit_ambiguous(pdfs: List[Path]) -> bool:
    """同语言子组内，版本判据最高只到 4 位数字格式且有 ≥2 个此格式文件时，
    新旧语义无法确定（MMDD/YYMM 混用可能），返回 True 让调用方跳过归档。"""
    fmts = [_parse_version_date(p.stem)[0] for p in pdfs]
    if not fmts:
        return False
    return max(fmts) == _FMT_DIGIT4 and fmts.count(_FMT_DIGIT4) >= 2


def _has_faction_pack_name(stem: str) -> bool:
    """检查是否为 Faction Pack 系列（英文官方版）。"""
    return stem.startswith("Faction Pack ")


def _has_chinese(stem: str) -> bool:
    """检查文件名是否含中文。"""
    for ch in stem:
        if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿":
            return True
    return False


def detect_version_groups(pdf_dir: Path) -> Dict[str, List[Path]]:
    """扫描 data/*.pdf，按阵营分组。

    返回 {faction_key: [Path, ...]}，每组内可能有多个版本。
    特殊书籍（core-rules 等）也作为独立组。
    """
    groups: Dict[str, List[Path]] = defaultdict(list)
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        key = _detect_faction_key(pdf.stem)
        if key is None:
            key = f"_unknown/{pdf.stem}"  # 孤立文件单独一组
        groups[key].append(pdf)
    return dict(groups)


def select_archive_targets(
    groups: Dict[str, List[Path]]
) -> List[Tuple[Path, Path]]:
    """每组选择归档目标。

    规则：
      1. 中英文各保留一本最新版
      2. 同语言内：Faction Pack > 社区翻译；新版 > 旧版
      3. 特殊书籍（core-rules 等）：每种保留一本最新版

    返回 [(source_path, archive_path), ...]。
    """
    if not groups:
        return []
    data_dir = next(iter(groups.values()))[0].parent  # data/
    # 取所有 group 中第一个路径的公共父目录
    archive_dir = data_dir / "archive"
    moves: List[Tuple[Path, Path]] = []

    for key, pdfs in groups.items():
        if len(pdfs) <= 1:
            continue  # 只有一个版本，不需归档

        # 按语言分组
        en_pdfs = [p for p in pdfs if not _has_chinese(p.stem)]
        zh_pdfs = [p for p in pdfs if _has_chinese(p.stem)]

        # M#8：保留哪本要靠比较多个 4 位数字版本号时，语义歧义无法定新旧，
        # 整组跳过归档并警告——宁可不归档也不误归档。
        if _four_digit_ambiguous(zh_pdfs) or _four_digit_ambiguous(en_pdfs):
            names = "、".join(p.name for p in pdfs)
            print(f"[skip] [{key}] 命名格式歧义（多个 4 位数字版本号，"
                  f"无法确定新旧），请人工确认：{names}")
            continue

        keep: Set[Path] = set()

        # 英文：选最新版
        if en_pdfs:
            en_pdfs.sort(key=lambda p: _parse_version_date(p.stem), reverse=True)
            # Faction Pack 优先（排在前面）
            en_pdfs.sort(key=lambda p: not _has_faction_pack_name(p.stem))
            best_en = en_pdfs[0]
            # 但也要考虑文件大小 — Faction Pack 通常更大更完整
            for p in en_pdfs:
                if _has_faction_pack_name(p.stem) and not _has_faction_pack_name(best_en.stem):
                    best_en = p
                    break
            keep.add(best_en)

        # 中文：选最新版（版本号为主、mtime 为副）
        if zh_pdfs:
            zh_pdfs.sort(
                key=lambda p: (_parse_version_date(p.stem), p.stat().st_mtime),
                reverse=True,
            )
            keep.add(zh_pdfs[0])

        # 对于无语言标记的（如纯英文无 faction 名），选第一个
        other = [p for p in pdfs if p not in en_pdfs and p not in zh_pdfs]
        if other:
            other.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            keep.add(other[0])

        # 其余全部归档
        for p in pdfs:
            if p not in keep:
                moves.append((p, archive_dir / p.name))

    return sorted(moves, key=lambda x: x[0].name)


def archive_old_versions(
    data_dir: Path,
    archive_dir: Path,
    dry_run: bool = True,
) -> List[str]:
    """主入口：分组 → 选择 → 移动。

    返回已移动（或将要移动）的文件名列表。
    """
    groups = detect_version_groups(data_dir)
    targets = select_archive_targets(groups)

    if not targets:
        print("没有需要归档的旧版 PDF。")
        return []

    moved: List[str] = []
    for src, dst in targets:
        if dry_run:
            print(f"[dry-run] {src.name} → archive/{dst.name}")
            moved.append(src.name)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                # Windows 下 rename 到已存在路径抛 FileExistsError → 跳过并警告
                print(f"[skip] 目标已存在，跳过: archive/{dst.name}")
                continue
            src.rename(dst)
            moved.append(src.name)
            print(f"[done] {src.name} → archive/{dst.name}")

    print(f"\n{'将' if dry_run else '已'}归档 {len(moved)} 个旧版 PDF")
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将旧版 PDF 移入 data/archive/，保留每组最新版")
    parser.add_argument("--data-dir", default="data",
                        help="PDF 目录（默认 data/）")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="只预览，不实际移动（默认）")
    parser.add_argument("--execute", action="store_false", dest="dry_run",
                        help="确认执行归档移动")
    parser.add_argument("--list-groups", action="store_true",
                        help="只列出检测到的分组和版本，不执行归档")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"错误：目录不存在 → {data_dir}")
        sys.exit(1)

    if args.list_groups:
        groups = detect_version_groups(data_dir)
        for key, pdfs in sorted(groups.items()):
            print(f"\n[{key}] ({len(pdfs)} 个版本)")
            for p in sorted(pdfs):
                ver = _parse_version_date(p.stem)
                size_mb = p.stat().st_size / 1024 / 1024
                en_flag = "EN" if not _has_chinese(p.stem) else "ZH"
                fp_flag = " [Faction Pack]" if _has_faction_pack_name(p.stem) else ""
                print(f"  {p.name}  v{ver}  {size_mb:.1f}MB  {en_flag}{fp_flag}")
        return

    archive_dir = data_dir / "archive"
    archive_old_versions(data_dir, archive_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
