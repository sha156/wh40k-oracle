# wiki_compile/pair_llm.py
"""LLM 兜底配对：确定性匹配剩下的残余交给 deepseek，按书批量、内容哈希缓存。
不 import llm_refine（其模块顶部有环境变量副作用），常量在此自定义。"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import List, Optional

from wiki_compile.canonical import CanonicalEntry
from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair, PairingResult

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-pro"
PROMPT_VERSION = "pair-v1"

_PROMPT = """你是战锤40K双语术语专家。以下中文条目名来自规则书《{book}》，候选英文官方名来自同阵营 datasheet 清单。
为每个中文名从候选中选出对应的英文名；不确定、或候选中不存在对应项时填 null。禁止编造候选之外的名字。
只输出 JSON，格式：{{"配对": [{{"zh": "中文名", "en": "英文名或null"}}]}}

中文条目名：
{zh_list}

候选英文名：
{en_list}
"""


def _cache_key(book: str, zh_names: List[str], en_names: List[str]) -> str:
    payload = json.dumps([PROMPT_VERSION, book, sorted(zh_names),
                          sorted(en_names)], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def llm_pair_book(book: str, unmatched: List[EntityCandidate],
                  candidates: List[CanonicalEntry], cache_dir: Path,
                  client=None) -> List[Pair]:
    todo = [e for e in unmatched if e.name_zh]
    if not todo or not candidates:
        return []
    zh_names = [e.name_zh for e in todo]
    en_names = [c.name for c in candidates]
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / (_cache_key(book, zh_names, en_names) + ".json")

    # 缓存读取容错：损坏/非法JSON/非dict 一律当作未命中，触发重新调用
    answer: Optional[dict] = None
    if cache_file.exists():
        try:
            loaded = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = None
        if isinstance(loaded, dict):
            answer = loaded

    if answer is None:
        prompt = _PROMPT.format(book=book, zh_list="\n".join(zh_names),
                                en_list="\n".join(en_names))
        resp = client.chat.completions.create(
            model=MODEL, temperature=0,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"})
        # LLM 响应容错：非法JSON/结构异常 → 本书跳过，且不写坏缓存
        try:
            parsed = json.loads(resp.choices[0].message.content)
        except (ValueError, AttributeError, TypeError):
            print(f"[pair_llm] {book} LLM 响应非合法JSON，跳过")
            return []
        if not isinstance(parsed, dict):
            print(f"[pair_llm] {book} LLM 响应非合法JSON，跳过")
            return []
        answer = parsed
        cache_file.write_text(json.dumps(answer, ensure_ascii=False),
                              encoding="utf-8")

    raw_pairs = answer.get("配对", [])
    if not isinstance(raw_pairs, list):
        return []

    by_name = {c.name: c for c in candidates}
    # 按对象聚合：同名 name_zh 的多个实体各自成对，避免 dict 折叠导致实体丢失
    by_zh: dict = {}
    for e in todo:
        by_zh.setdefault(e.name_zh, []).append(e)
    pairs: List[Pair] = []
    for item in raw_pairs:
        if not isinstance(item, dict):
            continue
        zh = item.get("zh")
        en = item.get("en")
        ents_for_zh = by_zh.get(zh)
        if not en or not ents_for_zh or en not in by_name:
            continue
        c = by_name[en]
        for e in ents_for_zh:  # 同名实体全部配对，共享同一 canonical 英文名
            pairs.append(Pair(zh=e.name_zh, en=c.name, canonical_id=c.id,
                              faction_id=c.faction_id, book=e.book,
                              pages=list(e.pages), confidence="llm"))
        by_zh.pop(zh, None)  # 消费掉，防止答案里重复 zh 导致重复出对
    return pairs


def run_llm_fallback(result: PairingResult, canonical: List[CanonicalEntry],
                     cache_dir: Path) -> PairingResult:
    """对每本已知阵营的书，把残余条目交给 LLM 在该阵营候选内配对。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("未设置 DEEPSEEK_API_KEY，跳过 LLM 兜底；残余留在 review_needed。")
        return result
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    votes: dict = {}
    for p in result.pairs:
        votes.setdefault(p.book, Counter())[p.faction_id] += 1
    book_faction = {b: v.most_common(1)[0][0] for b, v in votes.items()}
    paired_ids = {p.canonical_id for p in result.pairs}

    still_unmatched: List[EntityCandidate] = []
    new_pairs: List[Pair] = []
    by_book: dict = {}
    for e in result.unmatched:
        by_book.setdefault(e.book, []).append(e)
    for book, ents in by_book.items():
        fid = book_faction.get(book)
        if fid is None:
            still_unmatched.extend(ents)   # 无阵营锚（如核心规则书）→ 留人工
            continue
        candidates = [c for c in canonical
                      if c.faction_id == fid and c.id not in paired_ids]
        got = llm_pair_book(book, ents, candidates, cache_dir, client=client)
        new_pairs.extend(got)
        got_zh = {p.zh for p in got}
        still_unmatched.extend(e for e in ents if e.name_zh not in got_zh)
    return PairingResult(pairs=result.pairs + new_pairs,
                         unmatched=still_unmatched)
