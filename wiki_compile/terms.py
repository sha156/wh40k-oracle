"""双语术语表产出（P0 最终交付物）与读取。"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict

from wiki_compile.pair import PairingResult
from wiki_engine._io import atomic_write_text


def write_terms(result: PairingResult, wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    data = {"source": "wahapedia wh40k10ed",
            "pairs": [asdict(p) for p in result.pairs]}
    # 关键产物一律原子写（写 .tmp + os.replace），中途崩溃不留半截文件
    atomic_write_text(wiki_dir / "terms.json",
                      json.dumps(data, ensure_ascii=False, indent=1))

    lines = ["# 双语术语总表", "",
             "| 中文名 | 英文名 | 置信 | 来源书 | 页 |",
             "|--------|--------|------|--------|----|"]
    for p in sorted(result.pairs, key=lambda p: (p.book, p.en)):
        lines.append("| {} | {} | {} | {} | {} |".format(
            p.zh or "—", p.en, p.confidence, p.book,
            ",".join(str(n) for n in p.pages)))
    atomic_write_text(wiki_dir / "terms.md", "\n".join(lines) + "\n")

    rl = ["# 待人工校对（未配对实体）", ""]
    for e in result.unmatched:
        rl.append("- 《{}》 p{}：{}".format(
            e.book, ",".join(str(n) for n in e.pages), e.raw_heading))
    review_text = "\n".join(rl) + "\n"
    review_path = wiki_dir / "review_needed.md"
    # review_needed.md 可能带人工批注：内容将变化时先备份旧文件再覆盖
    if review_path.exists():
        try:
            old_text = review_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            old_text = None
        if old_text is not None and old_text != review_text:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = wiki_dir / "review_needed.backup-{}.md".format(stamp)
            backup_path.write_text(old_text, encoding="utf-8")
            print("[terms] review_needed.md 内容有变化，旧版已备份 → {}".format(
                backup_path))
    atomic_write_text(review_path, review_text)


def load_term_aliases(path: Path) -> Dict[str, str]:
    """terms.json → {中文名: canonical英文名}。缺失/损坏返回空表（检索层可安全降级）。

    zh→en 冲突（同一中文名映射到不同英文名）时保留首个并打警告，
    不再 last-write-wins 静默覆盖（H13）。
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    aliases: Dict[str, str] = {}
    try:
        for p in data.get("pairs", []):
            if not (isinstance(p, dict) and p.get("zh") and p.get("en")):
                continue
            zh, en = p["zh"], p["en"]
            if zh in aliases:
                if aliases[zh] != en:
                    print("[terms] 警告：别名冲突 '{}' → 已有 '{}'，"
                          "忽略后来的 '{}'（保留首个）".format(zh, aliases[zh], en))
                continue
            aliases[zh] = en
    except (AttributeError, TypeError):
        return {}
    return aliases
