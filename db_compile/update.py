"""update：一键刷新数据管线——把「定期爬取官方源保数据新鲜」的各环节串成一条命令。

用户拍板的数据权威层级（见 mfm.py 抬头）：**官方 GW/MFM 是最高真源**，Wahapedia CSV 是
结构化镜像，BSData 是英文属性第二源做交叉校验。本命令按正确顺序把它们重新对齐：

    1. BSData     git pull        —— 刷新英文属性第二源（交叉校验用，只读，不进库）
    2. MFM        fetch           —— 联网抓官方现行分数到 mfm_points.json（可 --offline 复用缓存）
    3. build      CSV → sqlite    —— 从 Wahapedia CSV 重建整库（会清空覆盖，是真源重置）
    4. MFM        apply           —— 把官方分数写回 units.points_json（必须在 build 之后，否则被覆盖）
    5. aliases    data_refined    —— 重灌中文别名层（build 清库后需重建）
    6. crosscheck BSData ↔ 库     —— 只读：英文属性一致率 + 真·分歧清单
    7. MFM        check           —— 只读：验证 apply 后分数已收敛到官方

顺序不可乱：build 会 `unlink` 重建整库，所以 apply/aliases 必须排在 build 之后；
crosscheck/check 是只读验证收尾。任一网络环节失败降级为「复用缓存 + 显眼告警」，
只有 build 失败才中止（下游全部依赖重建后的库）。
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, Optional

# unit_zh_detail / data_refined 变动后必须重建 FAISS 才能让 L1 检索层同步的提示。
_L1_SYNC_HINT = (
    "提示：库内容有变动后，需跑 `.venv\\Scripts\\python.exe ingest.py --rebuild` 让 FAISS "
    "L1 检索层同步（黑图书馆 chunk 只在 --rebuild 时注入，例行增量不会刷新）"
)


@dataclass
class UpdateConfig:
    bsdata: Path = Path("db_sources/bsdata")
    csv_dir: Path = Path("db_sources/wahapedia")
    db: Path = Path("db/wh40k.sqlite")
    terms: Path = Path("wiki/terms.json")
    mfm_json: Path = Path("db_sources/mfm/mfm_points.json")
    refined: Path = Path("data_refined")
    blacklibrary_cache: Path = Path("db_sources/blacklibrary/units.json")
    blacklibrary_details: Path = Path("db_sources/blacklibrary/details.json")
    manifest: Path = Path("db_sources/downloads/manifest.json")
    categories: tuple = ("warhammer-40000",)
    offline: bool = False        # 跳过全部联网（git pull + mfm fetch + 下载页），复用缓存
    fetch_mfm: bool = True        # 是否联网重抓 MFM（offline 时强制 False）
    check_downloads: bool = True  # 是否监控官方下载页版本（offline 时强制 False）


@dataclass
class StageResult:
    name: str
    ok: bool
    summary: str
    detail: Dict = field(default_factory=dict)
    warning: Optional[str] = None


@dataclass
class UpdateReport:
    stages: List[StageResult] = field(default_factory=list)
    aborted_at: Optional[str] = None

    def add(self, stage: StageResult) -> StageResult:
        self.stages.append(stage)
        return stage

    @property
    def ok(self) -> bool:
        return self.aborted_at is None and all(s.ok for s in self.stages)


def _banner(idx: int, total: int, title: str) -> None:
    print(f"\n[{idx}/{total}] {title}", flush=True)


def _git(bsdata: Path, *args: str) -> subprocess.CompletedProcess:
    """在 BSData 检出目录里跑 git（继承环境代理，git-https 走 Clash）。"""
    return subprocess.run(
        ["git", "-C", str(bsdata), *args],
        capture_output=True, text=True, timeout=180)


def stage_bsdata_pull(cfg: UpdateConfig) -> StageResult:
    """git pull BSData（--ff-only，避免意外 merge）。失败降级：用现有检出继续。"""
    if cfg.offline:
        return StageResult("bsdata_pull", True, "离线：跳过 git pull，用现有检出")
    if not (cfg.bsdata / ".git").exists():
        return StageResult("bsdata_pull", True,
                           f"跳过（{cfg.bsdata} 非 git 检出，用现有文件）",
                           warning="BSData 不是 git 仓库，无法自动刷新")
    try:
        before = _git(cfg.bsdata, "rev-parse", "--short", "HEAD").stdout.strip()
        pull = _git(cfg.bsdata, "pull", "--ff-only")
        after = _git(cfg.bsdata, "rev-parse", "--short", "HEAD").stdout.strip()
        if pull.returncode != 0:
            return StageResult(
                "bsdata_pull", True,
                f"pull 失败，沿用本地 {before}",
                detail={"before": before, "stderr": pull.stderr.strip()[:200]},
                warning=f"git pull 非零退出：{pull.stderr.strip()[:120]}")
        moved = before != after
        return StageResult(
            "bsdata_pull", True,
            f"{before} → {after}" + ("（有更新）" if moved else "（已是最新）"),
            detail={"before": before, "after": after, "updated": moved})
    except (subprocess.TimeoutExpired, OSError) as e:
        return StageResult("bsdata_pull", True, "git pull 超时/异常，沿用本地检出",
                           warning=f"{type(e).__name__}: {e}")


def stage_mfm_fetch(cfg: UpdateConfig) -> StageResult:
    """联网抓官方 MFM → mfm_points.json。offline / --no-fetch-mfm 时复用缓存。"""
    if cfg.offline or not cfg.fetch_mfm:
        if not cfg.mfm_json.exists():
            return StageResult("mfm_fetch", False,
                               f"离线但 {cfg.mfm_json} 不存在——无法 apply",
                               warning="需先联网跑一次 update 生成 MFM 缓存")
        data = json.loads(cfg.mfm_json.read_text(encoding="utf-8"))
        return StageResult("mfm_fetch", True,
                           f"复用缓存（抓取于 {data.get('fetched_at')}）",
                           detail={"fetched_at": data.get("fetched_at"),
                                   "cached": True})
    from db_compile.mfm import fetch_all
    try:
        data = fetch_all(cfg.mfm_json)
        n = sum(len(v) for v in data.values())
        return StageResult("mfm_fetch", True,
                           f"抓取 {len(data)} 阵营 / {n} 条分数",
                           detail={"factions": len(data), "rows": n})
    except Exception as e:  # 网络瞬断：降级复用缓存（若有）
        if cfg.mfm_json.exists():
            data = json.loads(cfg.mfm_json.read_text(encoding="utf-8"))
            return StageResult(
                "mfm_fetch", True,
                f"抓取失败，复用缓存（抓取于 {data.get('fetched_at')}）",
                warning=f"MFM 抓取失败：{type(e).__name__}: {e}")
        return StageResult("mfm_fetch", False,
                           "MFM 抓取失败且无缓存——无法 apply",
                           warning=f"{type(e).__name__}: {e}")


def stage_build(cfg: UpdateConfig) -> StageResult:
    """从 Wahapedia CSV 重建整库（清空覆盖）。失败 → 中止整条管线。"""
    from db_compile.build import build_database
    rep = build_database(cfg.csv_dir, cfg.db, cfg.terms)
    if not rep.row_counts:
        return StageResult("build", False,
                           f"重建 0 行——检查 {cfg.csv_dir} 是否有 CSV",
                           detail={"missing_csv": rep.missing_csv})
    warnings = []
    if rep.missing_csv:
        warnings.append(f"缺 CSV：{', '.join(rep.missing_csv)}")
    if rep.skipped:
        warnings.append("缺 id 跳过行数：" + "，".join(
            f"{k} {v}" for k, v in rep.skipped.items()))
    return StageResult(
        "build", True,
        "重建 " + "，".join(f"{k} {v}" for k, v in rep.row_counts.items()),
        detail={"row_counts": rep.row_counts, "missing_csv": rep.missing_csv,
                "skipped": rep.skipped},
        warning="；".join(warnings) if warnings else None)


def _load_mfm_factions(mfm_json: Path):
    data = json.loads(mfm_json.read_text(encoding="utf-8"))
    factions = {slug: [tuple(r) for r in rows]
                for slug, rows in data["factions"].items()}
    return factions, data.get("fetched_at")


def stage_mfm_apply(cfg: UpdateConfig) -> StageResult:
    """把官方 MFM 分数写回 units.points_json（build 之后，否则被覆盖）。"""
    if not cfg.mfm_json.exists():
        return StageResult("mfm_apply", False, f"{cfg.mfm_json} 不存在，跳过 apply")
    from db_compile.mfm import apply_points
    factions, fetched_at = _load_mfm_factions(cfg.mfm_json)
    rep = apply_points(cfg.db, factions, fetched_at=fetched_at)
    return StageResult(
        "mfm_apply", True,
        f"匹配 {rep['units_matched']} 单位，更新 {rep['units_updated']} 个",
        detail=rep)


def stage_aliases(cfg: UpdateConfig) -> StageResult:
    """从 data_refined 双语标题重灌中文别名层（build 清库后需重建）。"""
    from db_compile.aliases import populate_aliases
    rep = populate_aliases(cfg.db, cfg.refined)
    return StageResult(
        "aliases", True,
        f"提取 {rep['harvested']} 双语对，匹配 {rep['matched']}，"
        f"未匹配 {rep['unmatched']}，碰撞跳过 {rep['collided']}",
        detail=rep,
        warning=(f"{rep['collided']} 个中文别名碰撞（同名映射不同单位，保留首个）"
                 if rep['collided'] else None))


def stage_aliases_blackforum(cfg: UpdateConfig) -> StageResult:
    """从黑图书馆开放 API 补中英别名（build 清库后需重灌）。offline/抓取失败复用缓存。"""
    from db_compile.aliases import populate_blackforum_aliases
    from db_compile.blacklibrary import load_or_fetch_units, units_to_pairs
    units, source = load_or_fetch_units(cfg.blacklibrary_cache, offline=cfg.offline)
    if not units:
        return StageResult("aliases_blackforum", True, f"无单位数据（{source}），跳过",
                           warning="黑图书馆无缓存且离线，本次不补 blackforum 别名")
    rep = populate_blackforum_aliases(cfg.db, units_to_pairs(units))
    return StageResult(
        "aliases_blackforum", True,
        f"{source}：{len(units)} 单位 → 写入 {rep['matched']} 别名"
        f"（无英文跳过 {rep['skipped_no_en']}、未匹配 {rep['unmatched']}、"
        f"碰撞跳过 {rep['collided']}）",
        detail={**rep, "source": source},
        warning=(f"{rep['collided']} 个中文别名碰撞（同名映射不同单位，保留首个）"
                 if rep['collided'] else None))


def stage_aliases_community(cfg: UpdateConfig) -> StageResult:
    """人工策划的社区俗名层（激素虫=刀虫、阿巴顿=大掠夺者阿巴顿），build 清库后重灌。"""
    from db_compile.community_aliases import populate_community_aliases
    rep = populate_community_aliases(cfg.db)
    return StageResult(
        "aliases_community", True,
        f"社区俗名 {rep['total']} 条，匹配 {rep['matched']}，未匹配 {rep['unmatched']}",
        detail=rep)


def stage_zh_details(cfg: UpdateConfig) -> StageResult:
    """黑图书馆中文原生 datasheet 入库（build 清库后重灌）：填 units.name_zh + unit_zh_detail 表。

    从缓存 details.json 灌（detail 抓取慢，不进周更；刷新走 fetch_blacklibrary_details.py）。
    英文=权威真值不动，本表是叠加的中文内容层。
    """
    from db_compile.blacklibrary import (fill_name_zh, load_details,
                                         load_or_fetch_units, populate_zh_details)
    units, _ = load_or_fetch_units(cfg.blacklibrary_cache, offline=cfg.offline)
    name_rep = fill_name_zh(cfg.db, units) if units else {"filled": 0}
    details = load_details(cfg.blacklibrary_details)
    if not details:
        return StageResult("zh_details", True,
                           f"填 name_zh {name_rep['filled']}；无 details 缓存，跳过中文表",
                           warning="details.json 缺失，中文 datasheet 层未灌")
    det_rep = populate_zh_details(cfg.db, details)
    return StageResult(
        "zh_details", True,
        f"填 name_zh {name_rep['filled']}；unit_zh_detail 入库 {det_rep['matched']} "
        f"（无匹配 {det_rep['unmatched']}）",
        detail={**det_rep, "name_zh_filled": name_rep["filled"]})


def stage_crosscheck(cfg: UpdateConfig) -> StageResult:
    """只读：BSData ↔ Wahapedia 英文属性交叉校验。"""
    from db_compile.crosscheck import run
    rep = run(cfg.bsdata, cfg.db)
    return StageResult(
        "crosscheck", True,
        f"同名匹配 {rep.matched} ({rep.match_rate}%)，属性一致 {rep.agreed} "
        f"({rep.agreement_rate}%)，真分歧 {len(rep.discrepancies)}",
        detail={"matched": rep.matched, "agreement_rate": rep.agreement_rate,
                "discrepancies": rep.discrepancies,
                "duplicated_names": rep.duplicated_names,
                "skipped_files": rep.skipped_files},
        warning=(f"{len(rep.skipped_files)} 个 .cat 解析失败，未进比对池："
                 + "; ".join(s["path"] for s in rep.skipped_files))
        if rep.skipped_files else None)


def stage_mfm_check(cfg: UpdateConfig) -> StageResult:
    """只读：验证 apply 后库内分数已收敛到官方 MFM。"""
    if not cfg.mfm_json.exists():
        return StageResult("mfm_check", True, "无 MFM 缓存，跳过校验")
    from db_compile.mfm import check_points
    factions, _ = _load_mfm_factions(cfg.mfm_json)
    rep = check_points(cfg.db, factions)
    pct = round(rep["agree"] / rep["compared"] * 100, 1) if rep["compared"] else 0
    ok = len(rep["diffs"]) == 0
    return StageResult(
        "mfm_check", True,
        f"可比 {rep['compared']}，一致 {rep['agree']} ({pct}%)，过期 {len(rep['diffs'])}"
        + ("（已完全对齐官方）" if ok else "（仍有过期，检查 apply）"),
        detail={"compared": rep["compared"], "agree": rep["agree"],
                "diffs": rep["diffs"]},
        warning=None if ok else f"{len(rep['diffs'])} 条分数未收敛到官方")


def stage_downloads_check(cfg: UpdateConfig) -> StageResult:
    """只读：监控官方下载页 rules PDF 版本变化。缺 3.11/scrapling 优雅降级。"""
    if cfg.offline or not cfg.check_downloads:
        return StageResult("downloads_check", True, "离线/关闭：跳过下载页监控")
    from db_compile.downloads import check, summarize
    try:
        rep = check(cfg.manifest, cfg.categories)
    except RuntimeError as e:  # 无 3.11/scrapling/渲染失败：非关键，告警跳过
        return StageResult("downloads_check", True, "跳过（渲染环境不可用）",
                           warning=f"下载页监控需 3.11+scrapling：{e}")
    if rep.get("no_baseline"):
        return StageResult("downloads_check", True,
                           "无基线，跳过（先跑 `downloads --harvest` 建基线）")
    t = summarize(rep)
    changes = t["added"] + t["changed"] + t["removed"]
    ok_fresh = changes == 0
    return StageResult(
        "downloads_check", True,
        (f"官方下载页全部对齐（{t['unchanged']} 文档）"
         if ok_fresh else
         f"官方有更新：新增 {t['added']} / 改版 {t['changed']} / 下架 {t['removed']}"),
        detail=t,
        warning=None if ok_fresh else
        "官方 PDF 有变化——跑 `downloads --check` 看详情、`--harvest` 刷基线")


# (阶段编号, 标题, 函数, 是否关键——失败即中止)
_PIPELINE = [
    ("BSData git pull", stage_bsdata_pull, False),
    ("MFM 抓取（官方现行分数）", stage_mfm_fetch, False),
    ("重建整库（Wahapedia CSV → sqlite）", stage_build, True),
    ("应用官方 MFM 分数", stage_mfm_apply, False),
    ("重灌中文别名层", stage_aliases, False),
    ("补黑图书馆中英别名", stage_aliases_blackforum, False),
    ("补社区俗名层", stage_aliases_community, False),
    ("灌黑图书馆中文 datasheet 层", stage_zh_details, False),
    ("交叉校验 BSData ↔ 库", stage_crosscheck, False),
    ("校验分数收敛", stage_mfm_check, False),
    ("监控官方下载页版本", stage_downloads_check, False),
]


# build 会 unlink 重建整库，清掉官方 MFM 分数/别名/中文层。这些恢复阶段用本地缓存把它们
# 补回来（离线可跑），是「单独 build 后必须补跑」的那批（_PIPELINE 的 4-8 阶段）。
_RESTORE_STAGES = [
    ("应用官方 MFM 分数", stage_mfm_apply),
    ("重灌中文别名层", stage_aliases),
    ("补黑图书馆中英别名", stage_aliases_blackforum),
    ("补社区俗名层", stage_aliases_community),
    ("灌黑图书馆中文 datasheet 层", stage_zh_details),
]


def restore_authority_layers(cfg: UpdateConfig) -> UpdateReport:
    """build 清库后用本地缓存补回官方分数/别名/中文层，避免留下降级库（防呆）。

    强制离线：只用本地缓存，不联网。供 `db_compile build` CLI 在重建后自动补跑，
    杜绝「单独跑 build 静默把官方分回退成 Wahapedia 旧值并清空别名」这一脚枪。
    """
    cfg = replace(cfg, offline=True)
    report = UpdateReport()
    total = len(_RESTORE_STAGES)
    for idx, (title, fn) in enumerate(_RESTORE_STAGES, 1):
        _banner(idx, total, title)
        try:
            res = fn(cfg)
        except Exception as e:
            res = StageResult(fn.__name__, False, f"未预期异常：{type(e).__name__}: {e}")
        report.add(res)
        mark = "✅" if res.ok else "❌"
        print(f"    {mark} {res.summary}", flush=True)
        if res.warning:
            print(f"    ⚠️  {res.warning}", flush=True)
    print("\n" + _L1_SYNC_HINT, flush=True)
    return report


def run_update(cfg: UpdateConfig) -> UpdateReport:
    """按序执行整条刷新管线，返回结构化报告。关键阶段失败即中止。"""
    report = UpdateReport()
    total = len(_PIPELINE)
    t0 = time.time()
    for idx, (title, fn, critical) in enumerate(_PIPELINE, 1):
        _banner(idx, total, title)
        try:
            res = fn(cfg)
        except Exception as e:  # 阶段内未预期异常
            res = StageResult(fn.__name__, False, f"未预期异常：{type(e).__name__}: {e}")
        report.add(res)
        mark = "✅" if res.ok else "❌"
        print(f"    {mark} {res.summary}", flush=True)
        if res.warning:
            print(f"    ⚠️  {res.warning}", flush=True)
        if critical and not res.ok:
            report.aborted_at = res.name
            print(f"\n关键阶段 [{res.name}] 失败——中止（下游依赖重建后的库）", flush=True)
            break
    print(f"\n耗时 {time.time() - t0:.1f}s"
          + ("  管线全绿 ✅" if report.ok else "  有阶段未通过 ⚠️"), flush=True)
    if report.ok:
        print(_L1_SYNC_HINT, flush=True)
    return report
