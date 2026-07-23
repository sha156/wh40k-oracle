"""wiki_engine/synthesize.py — LLM 合成实体页（wiki 编译器步骤③）。

从 wiki_build/pairing.json 配对结果 + data_refined 源片段 → LLM 合成完整实体页。
按内容哈希缓存（复用 llm_refine 模式），增量重跑。
无 DEEPSEEK_API_KEY 时优雅跳过。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

from wiki_compile.extract import EntityCandidate, extract_entities
from wiki_compile.pair import Pair, PairingResult, normalize_name
from wiki_engine._io import (
    atomic_write_text,
    load_gen_hashes,
    save_gen_hashes,
    text_sha256,
)
from wiki_engine.models import (
    FACTION_NAMES,
    WikiPage,
    WikiPageFrontmatter,
    entity_page_path,
    faction_slug,
    slugify,
)

MODEL = "deepseek-v4-pro"
BASE_URL = "https://api.deepseek.com"
SYNTH_PROMPT_VERSION = "synth-v1"
MAX_RETRIES = 3
MAX_BODY_CHARS = 8000  # target max for body text (avoid oversized pages)


# ── 系统提示词 ────────────────────────────────────────────────────────

_SYNTH_UNIT_PROMPT = """你是战锤40K规则编译器。根据提供的源文本片段，为以下单位合成一份结构化的 Markdown 实体页。

要求：
1. **仅使用源文本中的信息**，不要编造任何数值、技能名称或规则描述
2. 如有中文和英文两个版本的数据，以中文版为主干、英文版补正数字
3. 按以下结构输出（缺失的章节可省略）：

## 属性表
| 模型 | M | T | SV | W | LD | OC |
| ... |

## 远程武器
| 武器 | 射程 | A | BS | S | AP | D | 技能 |
| ... |

## 近战武器
| 武器 | 射程 | A | WS | S | AP | D | 技能 |
| ... |

## 技能
- **技能名（英文名）**：技能描述
（核心/阵营/普通技能分别列出）

## 单位构成
- 模型数量与装备选项

## 关键词
- 阵营关键词：...
- 普通关键词：...

4. 技能描述中使用 `[[规则名]]` 标记引用核心规则（如 `[[致命爆退]]`、`[[冲锋阶段]]` 等）
5. 输出纯 Markdown（不要代码块包裹）"""

_SYNTH_STRATAGEM_PROMPT = """你是战锤40K规则编译器。根据提供的源文本片段，为以下策略技能合成结构化的 Markdown 实体页。

要求：
1. **仅使用源文本中的信息**
2. 按以下结构输出：

## 效果
| 来源 | 类型 | 时机 | 目标 | 消耗 | 效果 |
| ... |

## 技能描述
（如有额外说明文本）

3. 输出纯 Markdown"""

_SYNTH_DETACHMENT_PROMPT = """你是战锤40K规则编译器。根据提供的源文本片段，为以下分队合成结构化的 Markdown 实体页。

要求：
1. **仅使用源文本中的信息**
2. 按以下结构输出：

## 分队规则
- **规则名**：规则描述

## 强化
| 强化 | 费用 | 效果 |
| ... |

## 策略技能
（列出该分队专属的 CP 技能名称和简要效果）

3. 输出纯 Markdown"""

_SYNTH_CORE_RULE_PROMPT = """你是战锤40K规则编译器。根据提供的源文本片段，为核心规则概念合成结构化的 Markdown 实体页。

要求：
1. **仅使用源文本中的信息**
2. 清晰解释规则含义和判定流程
3. 引用相关的其他核心规则概念时使用 `[[概念名]]` 标记
4. 输出纯 Markdown"""

_SYNTH_ENHANCEMENT_PROMPT = """你是战锤40K规则编译器。根据提供的源文本片段，为以下强化（Enhancement）合成结构化的 Markdown 实体页。

要求：
1. **仅使用源文本中的信息**
2. 按以下结构输出：

## 效果
| 费用 | 效果 | 限制 |
| ... |

## 描述
（如有额外说明文本）

3. 输出纯 Markdown"""

_PROMPTS_BY_TYPE = {
    "unit": _SYNTH_UNIT_PROMPT,
    "stratagem": _SYNTH_STRATAGEM_PROMPT,
    "detachment": _SYNTH_DETACHMENT_PROMPT,
    "core-rule": _SYNTH_CORE_RULE_PROMPT,
    "enhancement": _SYNTH_ENHANCEMENT_PROMPT,
}


# ── 片段收集 ──────────────────────────────────────────────────────────

def collect_source_fragments(
    entity: EntityCandidate,
    refined_root: Path,
) -> List[Tuple[Path, str]]:
    """从 data_refined 收集该实体的全部源文本片段。

    返回 [(source_path, fragment_text), ...]。
    """
    fragments: List[Tuple[Path, str]] = []
    book_dir = refined_root / entity.book
    if not book_dir.is_dir():
        return fragments
    for page_no in sorted(entity.pages):
        md_path = book_dir / "page_{:03d}.md".format(page_no)
        if md_path.exists():
            text = md_path.read_text(encoding="utf-8")
            fragments.append((md_path, text))
    return fragments


def _infer_entity_type(entity: EntityCandidate) -> str:
    """从实体名和上下文推断实体类型。

    启发式：
      - 标题含"分队"/"分遣" → detachment
      - 标题含"强化" → enhancement
      - 英文名存在且在 Wahapedia 中有对应 → 来自 pair 信息
      - 默认 → unit
    """
    heading = entity.raw_heading or ""
    zh = entity.name_zh or ""
    if any(kw in heading for kw in ("分队", "分遣", "Detachment")):
        return "detachment"
    if any(kw in heading for kw in ("强化", "Enhancement")):
        return "enhancement"
    if any(kw in heading for kw in ("战略", "计谋", "Stratagem")):
        return "stratagem"
    # 中文规则书常见：含"规则"而非单位名
    if "规则" in zh and entity.name_en is None:
        return "core-rule"
    return "unit"


def _infer_faction_id(book_name: str) -> str:
    """从书名推断 faction_id（slug 形式）。"""
    # 去掉常见后缀
    clean = book_name
    for suffix in ("10版中文", "10版", "CODEX", "Codex", "Faction Pack",
                   "中文", "英文", "老湿腐版", "DavidZ版", "双子星版", "kasa"):
        clean = clean.replace(suffix, "")
    # 去掉版本号
    clean = re.sub(r"\d+\.\d+", "", clean)
    clean = clean.strip().strip("-_. ")
    return slugify(clean)


def _resolve_faction(entity: EntityCandidate, pair: Optional[Pair]) -> str:
    """fm.faction：优先按 pair.faction_id 映射为中文阵营名。

    faction_id 缺失时才退回书名推断；faction_id 存在但不在
    FACTION_NAMES 中时保留原 id（不误落到书名 slug）。
    """
    if pair is not None and pair.faction_id:
        return FACTION_NAMES.get(pair.faction_id, pair.faction_id)
    return _infer_faction_id(entity.book)


# ── 缓存 ──────────────────────────────────────────────────────────────

def _cache_key(prompt_version: str, canonical_id: str,
               fragments: List[Tuple[Path, str]]) -> str:
    """内容哈希 = SHA256(prompt_version + canonical_id + 拼接 fragment sha256s)。"""
    h = hashlib.sha256()
    h.update(prompt_version.encode())
    h.update(canonical_id.encode())
    for path, text in sorted(fragments, key=lambda x: str(x[0])):
        h.update(hashlib.sha256(text.encode()).digest())
    return h.hexdigest()


def _load_cache(cache_dir: Path, key: str) -> Optional[WikiPage]:
    """读取缓存。"""
    cache_file = cache_dir / "{}.json".format(key[:16])
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        fm = WikiPageFrontmatter.from_dict(data["fm"])
        return WikiPage(fm=fm, body=data["body"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _save_cache(cache_dir: Path, key: str, page: WikiPage) -> None:
    """写缓存。"""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "{}.json".format(key[:16])
    data = {
        "fm": asdict(page.fm),
        "body": page.body,
        "prompt_version": SYNTH_PROMPT_VERSION,
    }
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding="utf-8")


# ── 数字校验 ──────────────────────────────────────────────────────────

def _verify_numbers(sources: List[str], output: str) -> List[str]:
    """校验生成文本中的数字是否都来源于输入。"""
    src_counts: Counter = Counter()
    for s in sources:
        src_counts.update(re.findall(r"\d+", s))
    bad = []
    for tok, cnt in Counter(re.findall(r"\d+", output)).items():
        if cnt > src_counts.get(tok, 0):
            bad.append(tok)
    return sorted(bad)


# ── LLM 合成 ──────────────────────────────────────────────────────────

def _build_synthesis_user_prompt(
    entity: EntityCandidate,
    pair: Optional[Pair],
    fragments: List[Tuple[Path, str]],
    facts: Dict[str, Any],
) -> str:
    """构建发给 LLM 的用户提示。"""
    lines = [
        "## 实体信息",
    ]
    if entity.name_zh:
        lines.append("中文名: {}".format(entity.name_zh))
    if entity.name_en:
        lines.append("英文名: {}".format(entity.name_en))
    elif pair and pair.en:
        lines.append("英文名: {}".format(pair.en))

    faction_name = facts.get("faction_name_zh", "")
    if faction_name:
        lines.append("阵营: {}".format(faction_name))

    etype = _infer_entity_type(entity)
    lines.append("类型: {}".format(etype))
    lines.append("")
    lines.append("## 源文本片段")

    for i, (path, text) in enumerate(fragments):
        # 截断过长的片段
        if len(text) > 4000:
            text = text[:2000] + "\n\n...(中略)...\n\n" + text[-2000:]
        lines.append("### 片段 {} (来源: {})".format(i + 1, path.name))
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def _strip_code_fence(content: str) -> str:
    """去除 LLM 响应外围的 ``` 代码块标记。"""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*\n", "", content)
        content = re.sub(r"\n```\s*$", "", content)
    return content.strip()


def synthesize_page(
    client,
    entity: EntityCandidate,
    pair: Optional[Pair],
    fragments: List[Tuple[Path, str]],
    facts: Dict[str, Any],
) -> Optional[WikiPage]:
    """LLM 调用：根据 fragments 合成实体页。

    无 API key 时返回 None；LLM 出错重试 MAX_RETRIES 次。
    """
    if client is None:
        return None

    etype = _infer_entity_type(entity)
    system_prompt = _PROMPTS_BY_TYPE.get(etype, _SYNTH_UNIT_PROMPT)
    user_prompt = _build_synthesis_user_prompt(entity, pair, fragments, facts)

    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=4096,
            )
            body = _strip_code_fence(resp.choices[0].message.content or "")
            if not body:
                raise ValueError("LLM 返回空内容")

            # 数字校验
            source_texts = [t for _, t in fragments]
            bad = _verify_numbers(source_texts, body)
            if bad:
                tqdm.write("  数字校验警告 [{}]: 出现原文没有的数字 {}".format(
                    entity.name_zh or entity.name_en or "?", bad))

            # 构建 frontmatter
            fm = WikiPageFrontmatter(
                id="",  # 由调用方填充
                name_zh=entity.name_zh,
                name_en=pair.en if pair else entity.name_en,
                faction=_resolve_faction(entity, pair),
                type=etype,
                points=None,  # 后续 lint 标记缺失
                keywords=[],
                sources=[{"book": entity.book, "pages": list(entity.pages)}],
                raw=[str(frag[0].relative_to(frag[0].parent.parent.parent))
                     for frag in fragments],
                verify_warn=bool(bad),  # 校验结果落进 frontmatter，供 lint 报 warning
            )
            fm.generate_tags()

            # 限制 body 长度
            if len(body) > MAX_BODY_CHARS * 2:
                body = body[:MAX_BODY_CHARS] + "\n\n...(截断)..."

            return WikiPage(fm=fm, body=body)

        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 ** attempt)

    tqdm.write("  LLM 合成失败 [{}]: {}".format(
        entity.name_zh or entity.name_en or "?", last_err))
    return None


def load_or_synthesize(
    client,
    entity: EntityCandidate,
    pair: Optional[Pair],
    fragments: List[Tuple[Path, str]],
    facts: Dict[str, Any],
    cache_dir: Path,
) -> Optional[WikiPage]:
    """缓存优先：命中→直接读取；未命中→LLM 合成→缓存落盘。"""
    if not fragments:
        return None

    canonical_id = pair.canonical_id if pair else "unknown/{}".format(
        slugify(entity.name_zh or entity.name_en or "entity"))
    key = _cache_key(SYNTH_PROMPT_VERSION, canonical_id, fragments)

    cached = _load_cache(cache_dir, key)
    if cached is not None:
        # 用最新的 entity/pair 信息更新 frontmatter（缓存可能来自旧 prompt/旧配对）：
        # name/id/faction 都以当前配对为准，faction 变了 tags 也要跟着重算，
        # 否则缓存命中的页面会带着旧书名 slug 落到错误目录。
        cached.fm.name_zh = entity.name_zh
        cached.fm.name_en = pair.en if pair else entity.name_en
        cached.fm.id = canonical_id
        cached.fm.faction = _resolve_faction(entity, pair)
        cached.fm.generate_tags()
        return cached

    if client is None:
        return None

    page = synthesize_page(client, entity, pair, fragments, facts)
    if page is not None:
        page.fm.id = canonical_id
        _save_cache(cache_dir, key, page)
    return page


# ── 批量合成 ──────────────────────────────────────────────────────────

def build_faction_facts(pairs: List[Pair]) -> Dict[str, Dict[str, Any]]:
    """从配对结果提取阵营级基础事实。

    返回 {faction_id: {name_zh, name_en, ...}}。
    """
    facts: Dict[str, Dict[str, Any]] = {}
    faction_books: Dict[str, set] = {}
    for pair in pairs:
        fid = pair.faction_id or "_unknown"
        if fid not in facts:
            facts[fid] = {"name_zh": None, "name_en": None, "books": []}
            faction_books[fid] = set()
        if pair.book not in faction_books[fid]:
            faction_books[fid].add(pair.book)
            facts[fid]["books"] = list(faction_books[fid])
        if pair.zh and not facts[fid]["name_zh"]:
            facts[fid]["name_zh"] = pair.zh
    for fid in facts:
        facts[fid]["faction_slug"] = faction_slug(fid)
    return facts


# frontmatter 里 version.source: official-db ⇒ 官方结构库（from_db）渲染页
_OFFICIAL_DB_SRC_RE = re.compile(
    r"^\s*source:\s*['\"]?official-db['\"]?\s*$", re.MULTILINE)


def _is_official_db_page(text: str) -> bool:
    """页面是否来自官方结构库渲染（只查 frontmatter 区，不扫全文防正文误中）。"""
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    head = text[:end] if end != -1 else text[:2000]
    return bool(_OFFICIAL_DB_SRC_RE.search(head))


def synthesize_all(
    pairing_path: Path,
    refined_root: Path,
    wiki_root: Path,
    cache_dir: Path,
    client=None,
    faction_filter: Optional[str] = None,
    max_workers: int = 1,
) -> Dict[str, Any]:
    """全量（或按阵营）合成实体页。

    返回统计：{pairs: int, synthesized: int, cached: int, skipped: int, failed: int}。
    """
    if not pairing_path.exists():
        print("错误：配对文件不存在 → {}".format(pairing_path))
        return {"pairs": 0, "synthesized": 0, "cached": 0, "skipped": 0, "failed": 0}

    raw = json.loads(pairing_path.read_text(encoding="utf-8"))
    pairs = [Pair(**p) for p in raw.get("pairs", [])]
    unmatched = [EntityCandidate(**e) for e in raw.get("unmatched", [])]

    if faction_filter:
        pairs = [p for p in pairs
                 if faction_filter.lower() in (p.faction_id or "").lower()
                 or faction_filter.lower() in faction_slug(p.faction_id or "")]

    faction_facts = build_faction_facts(pairs)

    # entities: 从 extract 重新获取以拿到完整的 EntityCandidate（含 pages）。
    # 主键 = (book, pages)：pair.pages 在配对时直接从实体复制，天然对齐；
    # 不能用名字精确匹配——pair.en 是 Wahapedia 规范名（如 "Vespid Stingwings"），
    # 而 extract 出的 name_en 是 refined 页原文（全大写），精确匹配必然落空。
    # 兜底 = (book, normalize_name(name_en))：extract 重跑后 pages 漂移时按
    # 归一化名字在同书内匹配。
    from wiki_compile.extract import extract_book
    entities_map: Dict[Tuple, EntityCandidate] = {}
    entities_by_name: Dict[Tuple, EntityCandidate] = {}
    for book_dir in sorted(p for p in refined_root.iterdir() if p.is_dir()):
        for ent in extract_book(book_dir):
            entities_map.setdefault((ent.book, tuple(ent.pages)), ent)
            if ent.name_en:
                entities_by_name.setdefault(
                    (ent.book, normalize_name(ent.name_en)), ent)

    stats: Dict[str, Any] = {
        "pairs": len(pairs), "synthesized": 0, "cached": 0,
        "skipped": 0, "failed": 0, "path_conflicts": 0,
        # H16：被人工编辑保护跳过的页面相对路径列表
        "conflicts": [],
        # 目标页来自官方结构库（source: official-db）而被拒绝覆盖的列表——
        # 官方数据页权威高于 LLM 合成，无论 gen_hashes 登记与否一律不覆盖
        "official_protected": [],
        # 本次实际写入/更新的页面相对路径列表（供 ingest 日志用）
        "written": [],
    }

    jobs = []
    for pair in pairs:
        entity = entities_map.get((pair.book, tuple(pair.pages)))
        if entity is None and pair.en:
            entity = entities_by_name.get((pair.book, normalize_name(pair.en)))
        if entity is None:
            stats["skipped"] += 1
            continue
        fid = pair.faction_id or _infer_faction_id(pair.book)
        facts = faction_facts.get(fid, {})
        fragments = collect_source_fragments(entity, refined_root)
        if not fragments:
            stats["skipped"] += 1
            continue
        jobs.append((entity, pair, fragments, facts))

    if not jobs:
        print("没有可合成的配对。")
        return stats

    if client is None:
        print("LLM 客户端不可用（缺少 DEEPSEEK_API_KEY），仅从缓存加载。")
    else:
        print("可能调用 LLM 合成 {} 个实体页...".format(len(jobs)))

    def _work(job):
        """统一走 load_or_synthesize：缓存命中时同样刷新配对元数据（name/id）。"""
        entity, pair, fragments, facts = job
        key = _cache_key(SYNTH_PROMPT_VERSION, pair.canonical_id, fragments)
        was_cached = _load_cache(cache_dir, key) is not None
        page = load_or_synthesize(client, entity, pair, fragments, facts, cache_dir)
        if page is not None:
            return ("cached" if was_cached else "synthesized", pair, page)
        if client is None:
            return ("skipped_no_client", pair, None)
        return ("failed", pair, None)

    # 并发写保护：多个 job 可能解析到同一目标路径（同名/同 slug 实体），
    # 检测到重复路径时跳过并计入 stats，绝不静默覆盖。
    write_lock = threading.Lock()
    written_paths: set = set()

    # H16：生成内容哈希登记表——目标文件存在且当前内容 ≠ 上次生成登记值，
    # 说明被人工改过，跳过覆盖并计入冲突列表，绝不静默丢弃人工编辑。
    gen_hashes = load_gen_hashes(wiki_root)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_work, j): j for j in jobs}
        for fut in tqdm(as_completed(futures), total=len(futures),
                        desc="合成", unit="个"):
            try:
                status, pair, page = fut.result()
                if status == "cached":
                    stats["cached"] += 1
                elif status == "synthesized":
                    stats["synthesized"] += 1
                elif status == "failed":
                    stats["failed"] += 1
                else:
                    stats["skipped"] += 1

                if page is not None:
                    # 写 wiki 文件
                    file_path = entity_page_path(wiki_root, page.fm)
                    with write_lock:
                        if file_path in written_paths:
                            stats["path_conflicts"] += 1
                            tqdm.write("  ⚠️ 路径冲突，跳过写入: {} ({})".format(
                                file_path, pair.canonical_id))
                            continue
                        written_paths.add(file_path)
                    rel = str(file_path.relative_to(wiki_root)).replace("\\", "/")
                    # H16 冲突检测：仅当该路径有登记值时才可判定"人工改过"
                    # （无登记值 = 登记表启用前的旧文件，保持覆盖旧行为）
                    if file_path.exists():
                        try:
                            existing = file_path.read_text(encoding="utf-8")
                        except (OSError, UnicodeDecodeError):
                            existing = None
                        # 官方结构库页硬规则：source: official-db 的页面无条件拒绝
                        # 被 LLM 合成覆盖——不依赖 gen_hashes 是否存在（权威方向：
                        # 官方数值 > LLM 合成；gnhf 审查模块 6 F1 的反向失守通道）
                        if existing is not None and _is_official_db_page(existing):
                            stats["official_protected"].append(rel)
                            tqdm.write(
                                "  ⚠️ 目标页来自官方结构库（source: official-db），"
                                "LLM 合成不覆盖: {}".format(rel))
                            continue
                        registered = gen_hashes.get(rel)
                        cur_hash = (text_sha256(existing)
                                    if existing is not None else None)
                        if (registered is not None and cur_hash is not None
                                and cur_hash != registered):
                            stats["conflicts"].append(rel)
                            tqdm.write(
                                "  ⚠️ 人工编辑冲突，跳过覆盖: {}（该页在上次生成后"
                                "被手动修改；如需重新生成请先删除该页或还原修改）"
                                .format(rel))
                            continue
                    new_text = page.to_markdown()
                    atomic_write_text(file_path, new_text)
                    gen_hashes[rel] = text_sha256(new_text)
                    stats["written"].append(rel)

            except Exception as e:  # noqa: BLE001
                stats["failed"] += 1
                tqdm.write("  合成异常: {}".format(e))

    # 登记表原子落盘（写临时文件 + os.replace）
    save_gen_hashes(wiki_root, gen_hashes)
    return stats


def create_client() -> Any:
    """创建 OpenAI 客户端（带代理）。

    无 API key 时返回 None。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        # 明确区分两种根因（M：不再让"缺依赖包"被误报成"缺 API key"）
        print("[synthesize] 未设置 DEEPSEEK_API_KEY，无法创建 LLM 客户端。")
        return None
    try:
        from openai import OpenAI
        import httpx
        proxy = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7897")
        http_client = httpx.Client(proxy=proxy)
        return OpenAI(api_key=api_key, base_url=BASE_URL, http_client=http_client)
    except ImportError as e:
        print("[synthesize] 缺依赖包，无法创建 LLM 客户端: {}".format(e))
        return None
