"""web_api/keywords.py — 武器词条（USR）索引只读查询层（图鉴 · 词条页）。

数据**只**来自离线生成物 `wiki/indexes/keywords.json`（`wiki_engine.keyword_index` 产）。
请求期不查 `db/wh40k.sqlite`、更不碰 `data/*.pdf`：词条的三档分类（通用 / 十版遗留 /
单位特有）判据是 11 版通用技能速查表 PDF，而容器只挂 wiki/、db/、opt/、
local_vector_store/——data/ 根本不在场，想现算也算不出来；就算算得出，也会和离线
渲染的 wiki 词条页各说各话。

载荷 364KB / 46 条，每个请求 json.loads 一遍纯属浪费，故模块级缓存。
失效判据取 (mtime_ns, size) 而非"进程内只读一次"：离线重跑生成器后不必重启 API，
下一个请求自动吃到新数据。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = REPO_ROOT / "wiki" / "indexes" / "keywords.json"

_REBUILD_HINT = "离线跑 python -m wiki_engine.keyword_index 重建后随 wiki/ 一并挂载"


class KeywordPayloadError(RuntimeError):
    """载荷缺失或损坏。

    为什么专门抛异常、而不是像很多只读层那样返回空列表：空列表在前端渲染出来是
    「这一版没有武器词条」——一个看起来毫不心虚的错误答案。资产没挂上要一路冒到
    HTTP 503，让人知道是部署缺件，而不是规则真变了。
    """


def _short(path: Path) -> str:
    """给用户看的路径：仓库相对。绝对路径会把服务器目录结构吐进 HTTP 响应体。"""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


# path → (mtime_ns, size, items)。整个装载都在锁内：命中缓存时只是查个字典，
# 未命中时读一次 364KB 也就几毫秒——比起放锁外让并发请求各读各的、再互相覆盖缓存，
# 这点等待更划算，也更好推理。
_CACHE: Dict[str, Tuple[int, int, List[Dict[str, Any]]]] = {}
_LOCK = threading.Lock()


def _parse(path: Path) -> List[Dict[str, Any]]:
    """读 + 校验载荷骨架。任何一步不对都抛 KeywordPayloadError（不静默降级）。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise KeywordPayloadError("词条索引载荷读不出来（{}）：{}；{}".format(
            _short(path), exc, _REBUILD_HINT))
    items = data.get("items") if isinstance(data, dict) else None
    # 三种坏法分开报：错误信息必须和真实症结说同一件事，否则拿着报错去查也查不到
    # （refine 那边刚踩过——校验器说 A、实际错在 B，人就不再看报错了）
    if not isinstance(items, list):
        raise KeywordPayloadError("词条索引载荷结构不对（{}）：缺 items 数组；{}".format(
            _short(path), _REBUILD_HINT))
    bad = next((i for i, it in enumerate(items) if not isinstance(it, dict)), None)
    if bad is not None:
        raise KeywordPayloadError(
            "词条索引载荷结构不对（{}）：items[{}] 不是对象（{}）；{}".format(
                _short(path), bad, type(items[bad]).__name__, _REBUILD_HINT))
    if not items:
        # 空数组是"生成器跑挂了"的典型残骸（写了个壳），不是"这版真没有词条"。
        raise KeywordPayloadError("词条索引载荷是空的（{}）；{}".format(
            _short(path), _REBUILD_HINT))
    return items


def load_items(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """载荷里的全部条目（每条已是 KeywordDetail 形状，字段名已是 camelCase）。

    返回的是缓存对象本身，调用方**只读**——路由层交给 Pydantic 校验时会复制一份。
    """
    target = path or PAYLOAD_PATH
    try:
        stat = target.stat()
    except OSError:
        raise KeywordPayloadError("词条索引载荷缺失（{}）；{}".format(
            _short(target), _REBUILD_HINT))
    key = str(target)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None and hit[0] == stat.st_mtime_ns and hit[1] == stat.st_size:
            return hit[2]
        items = _parse(target)
        _CACHE[key] = (stat.st_mtime_ns, stat.st_size, items)
        return items


def list_keywords(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """索引页数据：逐条 KeywordSummary（**剥掉** weapons 反查表）。

    反查表占了载荷九成以上体积（RAPID FIRE 一条就挂 148 把武器），而索引页一把也不用。
    带上等于每次打开词条页都白传 300KB+。
    """
    return [{k: v for k, v in item.items() if k != "weapons"}
            for item in load_items(path)]


def get_keyword(slug: str,
                path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """按 slug 取单条 KeywordDetail（含 weapons 反查表）；未知 slug 返回 None。

    46 条线性扫足够快，不建索引字典——多一份派生状态就多一处和缓存失效对不上的机会。
    """
    for item in load_items(path):
        if item.get("slug") == slug:
            return item
    return None


def clear_cache() -> None:
    """丢弃缓存。测试用：同一路径先后写两份不同载荷时，别让上一份糊住。"""
    with _LOCK:
        _CACHE.clear()
