"""wiki_engine/operations/ingest_op.py — Ingest 操作。

新源料 → 编译入 wiki → 级联更新 → 刷新索引 → 记录日志。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from wiki_engine.build_outputs import build_all_outputs, build_log_entry, write_log
from wiki_engine.crosslinks import inject_all
from wiki_engine.lint import run_lint
from wiki_engine.synthesize import create_client, synthesize_all


def find_affected_pages(
    new_raw_files: List[Path],
    wiki_root: Path,
) -> List[str]:
    """给定新 data_refined 文件，扫描现有 wiki 页面找出受影响实体。

    匹配规则：page.fm.raw 中引用了新文件的实体。

    注意：本函数尚未接入 ingest() 主流程（完整级联更新待实现）。
    """
    from wiki_engine.build_outputs import scan_wiki_pages
    affected: List[str] = []
    new_raw_set = {str(f).replace("\\", "/") for f in new_raw_files}

    for page in scan_wiki_pages(wiki_root):
        for raw_ref in page.fm.raw:
            # raw_ref 可能包含相对于 data_refined/ 的路径
            if any(nr in str(raw_ref) for nr in new_raw_set):
                affected.append(page.fm.id)
                break

    return list(set(affected))


def cascade_updates(
    changed_ids: List[str],
    wiki_root: Path,
) -> List[str]:
    """级联检查：被改实体所在阵营的 index.md、引用实体的其他页面也需标记刷新。

    注意：本函数尚未接入 ingest() 主流程（完整级联更新待实现）。
    """
    # 当前版本返回空列表——级联刷新由 build_all_outputs 全量重建来处理
    return []


def ingest(
    new_sources: List[Path],
    refined_root: Path,
    wiki_root: Path,
    cache_dir: Path,
    pairing_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Ingest 主入口：新 raw 源料 → wiki 增量更新。

    pairing_path：配对文件路径，缺省沿用现行为（wiki_build/pairing.json）。

    返回统计信息和日志条目。
    """
    client = create_client()
    if client is None:
        print("⚠️ LLM 客户端不可用，仅能从缓存加载。")

    # 合成受影响实体页
    if pairing_path is None:
        pairing_path = Path("wiki_build/pairing.json")
    stats = {}
    if pairing_path.exists():
        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined_root,
            wiki_root=wiki_root,
            cache_dir=cache_dir,
            client=client,
            max_workers=1,
        )
        print("合成: {} pairs, {} 新合成, {} 缓存, {} 跳过, {} 失败".format(
            stats.get("pairs", 0), stats.get("synthesized", 0),
            stats.get("cached", 0), stats.get("skipped", 0),
            stats.get("failed", 0)))
    else:
        print("提示：配对文件不存在，跳过合成。实际查找路径: {}".format(
            pairing_path.resolve()))

    # 交叉链接
    terms_path = wiki_root / "terms.json"
    modified = inject_all(wiki_root, terms_path if terms_path.exists() else None)
    print("交叉链接: {} 页已更新".format(len(modified)))

    # 重建索引
    build_all_outputs(wiki_root)

    # lint
    result = run_lint(wiki_root, refined_root, auto_fix=True)
    from wiki_engine.lint import generate_lint_report
    generate_lint_report(result, wiki_root)
    print("Lint: {} issues, {} auto-fixed".format(result.total, result.auto_fixed))

    # 日志：affected_pages = 本次合成实际写入的页面 ∪ 交叉链接改写的页面
    # （不是完整级联——find_affected_pages/cascade_updates 尚未接线）
    affected = sorted(set(stats.get("written", []) or []) | set(modified))
    entry = build_log_entry(
        operation="ingest",
        description="来源文件: {}".format(", ".join(str(s) for s in new_sources)),
        affected_pages=affected,
    )
    write_log(wiki_root / "log.md", entry)

    return {"stats": stats, "lint": result}
