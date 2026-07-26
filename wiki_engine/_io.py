"""wiki_engine/_io.py — 关键产物 I/O 小工具（wiki_engine 与 wiki_compile 两包共用）。

- atomic_write_text：写同目录 .tmp 临时文件后 os.replace 原子落盘，
  避免写盘中途崩溃留下半截文件（pairing.json / terms.json / wiki 页面与索引）。
- .gen_hashes.json：synthesize 生成内容的哈希登记表（relpath → sha256），
  用于检测 wiki 页面是否被人工编辑过，防止重跑时静默覆盖（见 synthesize.py）。
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional

# 生成内容哈希登记表文件名（放在 wiki_root 下，以点开头不进 Obsidian 视野）
GEN_HASHES_NAME = ".gen_hashes.json"


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8",
                      newline: Optional[str] = None) -> None:
    """原子写文本：先写同目录临时文件，再 os.replace 覆盖目标。

    os.replace 在 Windows / POSIX 上均为原子替换（同一文件系统内）。

    newline 默认 None＝随平台（Windows 上 \\n 会被写成 \\r\\n），这是 wiki 下
    1800+ 个 .md 既有产物的行尾，**不要改**，改了就是一次全库假 diff。
    传 "\\n" 可强制 LF——机器读的产物（如 indexes/keywords.json）需要它：
    这类文件在 Windows 本机和 Linux CI/容器里都会被重新生成，行尾随平台漂移
    会让同样的数据每次都产生整文件 diff。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    # 用 open 而非 Path.write_text：后者的 newline 参数 3.10 才有，本项目跑在 3.9
    with open(str(tmp), "w", encoding=encoding, newline=newline) as fh:
        fh.write(text)
    os.replace(tmp, path)


def text_sha256(text: str) -> str:
    """文本内容的 sha256 十六进制摘要。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_gen_hashes(wiki_root: Path) -> Dict[str, str]:
    """读取生成内容哈希登记表；缺失/损坏/结构异常一律返回空表（安全降级）。"""
    path = Path(wiki_root) / GEN_HASHES_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items()
            if isinstance(k, str) and isinstance(v, str)}


def save_gen_hashes(wiki_root: Path, hashes: Dict[str, str]) -> None:
    """原子写回哈希登记表。"""
    atomic_write_text(
        Path(wiki_root) / GEN_HASHES_NAME,
        json.dumps(hashes, ensure_ascii=False, indent=1, sort_keys=True))
