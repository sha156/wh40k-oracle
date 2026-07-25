"""web_api/preflight.py — Stage 5 部署前置校验。

容器化之后最常见的事故是**卷没挂上**：模型 / FAISS 索引 / 结构库任一缺失，
FastAPI 照样能起来、端点照样 200，但所有回答静默降级成「知识库未构建」。
本模块在启动时把资产核对一次、在日志里吼出来，并把结果挂到 `/healthz`——
宁可启动时刺眼，也不要运行时静默降级。

资产全部是 gitignore 的大件（`opt/` 4.5G 模型、`local_vector_store/`、`db/`），
compose 里以只读卷从宿主机挂进来，见 `docker-compose.yml`。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AssetStatus:
    """单个运行期资产的核对结果。"""

    name: str
    path: str
    ok: bool
    required: bool          # True=缺了核心功能就废；False=缺了只废某个页签
    detail: str             # 缺失/异常时的人话说明（ok 时为空串）
    hint: str               # 修复办法（宿主机上的命令或挂载键）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "path": self.path, "ok": self.ok,
            "required": self.required, "detail": self.detail, "hint": self.hint,
        }


def _embed_snapshot(root: Path) -> Optional[Path]:
    """返回 bge-m3 的本地完整快照目录（含 modules.json），没有则 None。

    判据与 `app.resolve_embed_model()` 保持一致：只有带 modules.json 的快照才是
    可离线加载的完整 sentence-transformers 模型；只下了一半的快照要算缺失，
    否则容器起来后第一次检索才在 HF 联网重试里超时。
    """
    snapshots = root / "opt" / "models--BAAI--bge-m3" / "snapshots"
    if not snapshots.is_dir():
        return None
    for snap in sorted(snapshots.iterdir()):
        if (snap / "modules.json").exists():
            return snap
    return None


def retrieval_enabled() -> bool:
    """本部署是否启用本地检索（bge-m3 + FAISS）。

    小内存服务器上只跑图鉴/模拟器/军表三个零 LLM 页签时设 `WEB_API_RETRIEVAL=off`：
    实测检索栈常驻 3.2 GB，2 核 3.3 G 的机器塞不下。关掉后模型与索引**按设计**
    就不该在场，前置校验不能再把它们报成缺失——否则天天报缺，人就学会无视 ready，
    真出事那次也照样无视。
    """
    return os.environ.get("WEB_API_RETRIEVAL", "on").strip().lower() != "off"


def check_assets(root: Optional[Path] = None,
                 retrieval: Optional[bool] = None) -> List[AssetStatus]:
    """核对四类运行期资产，按「先必需后可选」返回。

    `retrieval=False` 时模型与索引降为「按设计不需要」（required=False），
    其余两项不受影响。
    """
    root = root or REPO_ROOT
    want_retrieval = retrieval_enabled() if retrieval is None else retrieval
    out: List[AssetStatus] = []

    # 检索关掉时的说明：写清楚"不是坏了，是没开"，并给打开的办法
    off_note = "本部署未启用本地检索（WEB_API_RETRIEVAL=off），按设计不需要"
    off_hint = "要开启检索：确保内存 ≥4G，传模型/索引并去掉 WEB_API_RETRIEVAL=off"

    snap = _embed_snapshot(root)
    out.append(AssetStatus(
        name="embed_model",
        path=str(snap) if snap else str(root / "opt" / "models--BAAI--bge-m3"),
        ok=snap is not None,
        required=want_retrieval,
        detail=("" if snap else
                ("bge-m3 本地快照缺失或不完整（无 modules.json）" if want_retrieval
                 else off_note)),
        hint=("挂载宿主机 ./opt 到 /app/opt（compose 卷 opt:ro）" if want_retrieval
              else off_hint),
    ))

    faiss_index = root / "local_vector_store" / "index.faiss"
    out.append(AssetStatus(
        name="vector_store",
        path=str(faiss_index),
        ok=faiss_index.exists(),
        required=want_retrieval,
        detail=("" if faiss_index.exists() else
                ("FAISS 索引缺失，混合检索会全量落空" if want_retrieval else off_note)),
        hint=("宿主机跑 .\\.venv\\Scripts\\python.exe ingest.py 后挂载 ./local_vector_store"
              if want_retrieval else off_hint),
    ))

    db = root / "db" / "wh40k.sqlite"
    out.append(AssetStatus(
        name="structured_db",
        path=str(db),
        ok=db.exists(),
        required=True,
        detail="" if db.exists() else "结构库缺失，图鉴/模拟器/军表三个页签全部 503",
        hint="宿主机跑 python -m db_compile build 后挂载 ./db",
    ))

    wiki_index = root / "wiki" / "index.md"
    out.append(AssetStatus(
        name="wiki",
        path=str(wiki_index),
        ok=wiki_index.exists(),
        required=False,
        detail="" if wiki_index.exists() else "wiki 未挂载，wiki 检索工具与图鉴条目页降级",
        hint="挂载 ./wiki（仓库内已跟踪，未挂载时用镜像内自带副本）",
    ))

    return out


def format_report(statuses: List[AssetStatus]) -> str:
    """启动日志用的多行报告；缺失项带 [缺] 前缀，方便 docker logs 一眼看到。"""
    lines = ["[preflight] 运行期资产核对（检索{}）：".format(
        "开" if retrieval_enabled() else "关")]
    for s in statuses:
        mark = "ok " if s.ok else ("缺!" if s.required else "略 ")
        lines.append("[preflight]   [{}] {:<15} {}".format(mark, s.name, s.path))
        if not s.ok:
            lines.append("[preflight]        ↳ {}；修复：{}".format(s.detail, s.hint))
    missing_required = [s for s in statuses if not s.ok and s.required]
    if missing_required:
        lines.append(
            "[preflight] ⚠ {} 项必需资产缺失——服务仍会启动（端点可联调），"
            "但相关回答会降级。别把降级结果当正确答案。".format(len(missing_required)))
    else:
        lines.append("[preflight] 必需资产齐全。")
    return "\n".join(lines)


def summary(root: Optional[Path] = None) -> Dict[str, Any]:
    """`/healthz` 用的结构化摘要。ready = 全部必需资产就位。"""
    statuses = check_assets(root)
    return {
        "ready": all(s.ok for s in statuses if s.required),
        "retrieval": retrieval_enabled(),
        "assets": [s.to_dict() for s in statuses],
    }


def run_preflight(root: Optional[Path] = None, echo: bool = True) -> Dict[str, Any]:
    """启动时调用：核对 + 打日志。返回同 `summary()`。

    `WEB_API_PREFLIGHT_STRICT=1` 时必需资产缺失直接抛错拒绝启动——给「宁可起不来
    也不要跑出降级答案」的场景用（比如给别人演示前）。默认不 strict，保持联调可用。
    """
    statuses = check_assets(root)
    if echo:
        print(format_report(statuses), flush=True)
    missing_required = [s.name for s in statuses if not s.ok and s.required]
    if missing_required and os.environ.get("WEB_API_PREFLIGHT_STRICT", "") == "1":
        raise RuntimeError(
            "preflight 严格模式：必需资产缺失 {}，拒绝启动".format(missing_required))
    return {
        "ready": not missing_required,
        "retrieval": retrieval_enabled(),
        "assets": [s.to_dict() for s in statuses],
    }
