"""agent/llm_client.py — 真实 LLMClient 实现（接线 app.py 前的最后一块）。

实现 agent.loop.LLMClient Protocol（classify_intent + next_step），后端走
deepseek-chat / glm-4-flash 的 OpenAI 兼容接口（openai SDK，非流式）。

协议采用「prompt 约束 JSON」而非各家原生 function-calling：
- 供应商可移植（deepseek / glm 同一套代码，只换 base_url/model）
- 与 agent/loop.py 既有的 dict 步骤契约一一对应：
  {"type":"tool_call","tool":...,"args":{...}} / {"type":"final","content":...,"sources":[...]}
- 解析失败或 API 异常一律 **抛异常**，交给 loop.run() 的 try/except 降级到 rag_search，
  绝不伪造工具调用或数字（fail-closed）。
"""
from __future__ import annotations

import dataclasses
import json
import re
from typing import Any, Dict, List, Optional

from agent.loop import DEFAULT_INTENT, INTENTS

# openai SDK 的 400 参数错误——供应商不支持 response_format 时的典型表现。
# SDK 未安装（纯单测环境）时退化为占位类，isinstance 恒 False。
try:
    from openai import BadRequestError as _BadRequestError
except Exception:  # pragma: no cover
    class _BadRequestError(Exception):
        pass

# provider 展示名 → (base_url, model)。与 app.get_llm 保持一致。
_PROVIDERS: Dict[str, Any] = {
    "DeepSeek": ("https://api.deepseek.com", "deepseek-chat"),
    "ZhipuAI (GLM-4)": ("https://open.bigmodel.cn/api/paas/v4/", "glm-4-flash"),
}

# TOOL_SPECS 只有 name+description，缺参数名。补一张 arg 提示表（只读，不改 tools.py）
# 让模型知道每个工具怎么传参。未列出的工具默认无参数 {}。
_TOOL_ARG_HINTS: Dict[str, str] = {
    "search_wiki": '{"query": "中文关键词"}',
    "get_entity": '{"name_or_id": "用户原文里的中文单位名（工具内部自动解析俗名/译名）"}',
    "get_keyword_definition": '{"keyword": "USR 或核心概念名"}',
    "get_datasheet": ('{"name_or_id": "用户原文里的中文单位名（内部解析别名到 L3 结构库）。'
                      '只传单位名本身，不要带阵营/所属前缀（「吞世者的地狱兽」→ 传「地狱兽」）；'
                      '若返回 ambiguous，再按阵营用候选串重查（如 \\"Helbrute (WE)\\"）"}'),
    "entity_resolver": '{"name": "中文/英文/俗名"}',
    "calc_points": '{"unit_list": ["单位名", ...]}',
    "rag_search": '{"query": "自然语言问题"}',
    # 对照 agent/tools.py judge_fight_order 真实读取的 ctx 键，全可选
    "judge_fight_order": (
        '{"ctx": {"attacker": "攻方单位名", "defender": "守方单位名", '
        '"attacker_charged": true, "attacker_fights_first": false, '
        '"attacker_fights_last": false, "defender_fights_first": false, '
        '"defender_fights_last": false, "counter_offensive_by": "attacker|defender"}}'
    ),
    # 对照 agent/tools.py simulate_combat 真实读取的 options 键，options 内全可选
    "simulate_combat": (
        '{"attacker": "攻方单位名", "defender": "守方单位名", '
        '"options": {"phase": "shooting|melee", "charge": false, '
        '"half_range": false, "cover": false, "stationary": false, '
        '"stealth": false, "loadout": [["武器名", 数量], ...], '
        '"defender_loadout": [["武器名", 数量], ...], "fnp": 5, '
        '"damage_reduction": 1, "attacker_models": 5, "defender_models": 5, '
        '"n": 8000, "seed": 1234}}'
    ),
    "validate_roster": '{"roster_text": "军表文本"}',
    "critique_roster": '{"roster_text": "军表文本"}',
    "archive_answer": '{"title": "标题", "content": "正文"}',
}

_INTENT_SYSTEM = (
    "你是战锤40K规则问答系统的意图分类器。把用户输入分到且仅分到以下之一：\n"
    "查 = 查规则/单位/数据/关键词定义；\n"
    "判 = 判定某具体情形下规则如何裁定（先后顺序、能否触发等）；\n"
    "算 = 计算点数/军表分值；\n"
    "谋 = 战术推演/模拟对战/谁能打赢；\n"
    "闲聊 = 与规则无关的寒暄。\n"
    "只输出这一个汉字，不要任何解释、标点或引号。"
)

_NEXT_STEP_CONTRACT = """你是「铁幕」，战锤40K第十版规则参谋，正在一个工具调用循环中工作。
每一步你必须**只输出一个 JSON 对象**（不要 markdown 代码块外的任何多余文字），二选一：

1) 调用工具（需要查证时）：
{{"type": "tool_call", "tool": "<工具名>", "args": {{<参数>}}}}

2) 给出最终答案（信息足够时）：
{{"type": "final", "content": "<中文回答，含数字与引用>", "sources": [{{"book": "书名", "page": 页码}}]}}

可用工具：
{catalog}

工具使用策略：
- **问属性/数值**（M/T/Sv/W/OC/Ld、武器 A/BS/WS/S/AP/D、单位点数）时，**先用 get_datasheet**，
  直接传用户原文里的中文单位名——它直查 L3 结构库（英文权威真值 + 中文别名层），是数值题的
  **首选**，避免 PDF 检索被译名/拍扁坑。get_datasheet 查空再退到 get_entity / rag_search。
- **问技能效果/单位背景/军表构成**时，直接用用户原文里的中文单位名调 get_entity，
  它内部会自动解析社区俗名与规则书译名。不要先把名字转成英文或 id 再传给 get_entity
  （wiki 索引只认中文名，传英文/id 会查空）。
- 问 USR / 核心概念定义时用 get_keyword_definition。
- **judge_fight_order / simulate_combat**：用户描述里能提取出的场景要素——冲锋/是否先攻后攻
  （Fights First/Fights Last）/半程/掩体/静止/武器配置(loadout)/双方人数/无痛(fnp)等——
  **必须传入对应字段，不得省略**；省略等于按默认场景判定/模拟，结果会答非所问。
  用户没提到的要素保持缺省即可，不要编造。
- entity_resolver 只在你需要英文 canonical 名、或名称有歧义要向用户反问时才用。
- get_datasheet/get_entity/search_wiki 查空时，再退而用 rag_search 做自然语言兜底检索。

铁律：
- 能用工具查证的先查证，不要凭记忆编造数字或规则。
- 工具返回 "reason": "ambiguous"（同名单位存在于多个阵营）时，**必须**再调一次工具：
  优先改用用户原文里的中文单位名重查；仍歧义则按问题上下文的阵营从 candidates 里
  选一个候选名（如 "Helbrute (WE)"）原样重查。绝不允许在歧义未消除时凭记忆填数值；
  上下文也无法确定阵营时，逐一列出各阵营候选的数值并说明差异。
- 工具返回 "modeled": false 或提示「未建模」时，如实告诉用户该能力尚未实现，
  绝不编造模拟/判定/算分结果。
- content 里每条关键信息后标注 [《书名》第X页]。
- 若档案中确无相关信息，直接回复「档案缺失，建议查阅原始规则书」，绝不编造。
- 属性/攻击数据尽量用表格或粗体呈现。
"""


def _render_catalog(tool_specs: List[Dict[str, str]]) -> str:
    lines = []
    for spec in tool_specs:
        name = spec.get("name", "")
        desc = spec.get("description", "")
        args = _TOOL_ARG_HINTS.get(name, "{}")
        lines.append(f"- {name} 参数{args}：{desc}")
    return "\n".join(lines)


def _json_default(o: Any) -> Any:
    """让 json.dumps 能吃下工具返回里的非原生对象（如 WikiPage 数据类）。

    优先用对象自带的 to_markdown()（WikiPage 会给出整页 markdown，正是 LLM 要读的内容），
    其次退回 dataclasses.asdict，最后退回 str。绝不因序列化失败而让整步崩溃。
    """
    to_md = getattr(o, "to_markdown", None)
    if callable(to_md):
        try:
            return to_md()
        except Exception:
            pass
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        try:
            return dataclasses.asdict(o)
        except Exception:
            pass
    return str(o)


def _render_loop_message(msg: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """把 loop 内部 message 转成 OpenAI chat message。

    tool 结果是 dict（可能内嵌 WikiPage 等对象），用 _json_default 安全序列化成
    JSON 文本塞进 user 轮（本协议不用原生 tool 角色）。过长返回（如整页 wiki）截断。
    """
    role = msg.get("role")
    content = msg.get("content")
    if role == "user":
        return {"role": "user", "content": str(content)}
    if role == "assistant":
        return {"role": "assistant", "content": str(content)}
    if role == "tool":
        name = msg.get("name", "?")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, default=_json_default)
        if len(content) > 4000:
            content = content[:4000] + "…（已截断）"
        return {"role": "user", "content": f"[工具 {name} 返回]\n{content}"}
    return None


def _extract_json_object(text: str) -> Dict[str, Any]:
    """从模型输出里抠出第一个 JSON 对象；容忍 ```json 代码块包裹与前后噪声。

    解析失败抛 ValueError（交给 loop.run 降级），绝不返回半成品。
    """
    if not text or not text.strip():
        raise ValueError("LLM 返回空内容")
    stripped = text.strip()
    # 去 markdown 代码块围栏
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        # 退一步：抓第一个平衡的 {...}
        start = stripped.find("{")
        if start == -1:
            raise ValueError(f"未找到 JSON 对象：{stripped[:120]}")
        depth = 0
        end = -1
        for i in range(start, len(stripped)):
            c = stripped[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            raise ValueError(f"JSON 对象不完整：{stripped[:120]}")
        obj = json.loads(stripped[start:end])
    if not isinstance(obj, dict) or "type" not in obj:
        raise ValueError(f"JSON 缺少 type 字段：{str(obj)[:120]}")
    return obj


class OpenAICompatLLMClient:
    """deepseek / glm 兼容 OpenAI 接口的真实 LLMClient。

    构造时可注入 client（实现 .chat.completions.create），供单测替换掉真实 API。
    """

    def __init__(
        self,
        api_key: str = "",
        provider: str = "DeepSeek",
        temperature: float = 0.1,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        base_default, model_default = _PROVIDERS.get(provider, (None, None))
        self.base_url = base_url or base_default
        self.model = model or model_default
        if self.base_url is None or self.model is None:
            raise ValueError(
                f"未知 provider={provider!r} 且未显式给出 base_url/model"
            )
        self.temperature = temperature
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key, base_url=self.base_url)

    # ── LLMClient Protocol ────────────────────────────────────────
    def classify_intent(self, user_input: str) -> str:
        try:
            text = self._chat(
                [
                    {"role": "system", "content": _INTENT_SYSTEM},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=8,
                temperature=0.0,
            )
        except Exception:
            return DEFAULT_INTENT
        text = (text or "").strip()
        for intent in INTENTS:
            if intent in text:
                return intent
        return DEFAULT_INTENT

    def next_step(
        self,
        messages: List[Dict[str, Any]],
        tool_specs: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        system = _NEXT_STEP_CONTRACT.format(catalog=_render_catalog(tool_specs))
        chat_messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
        for msg in messages:
            rendered = _render_loop_message(msg)
            if rendered is not None:
                chat_messages.append(rendered)

        text = self._chat(
            chat_messages,
            max_tokens=1600,
            temperature=self.temperature,
            want_json=True,
        )
        try:
            return _extract_json_object(text)
        except ValueError:
            # 只对「响应内容 JSON 解析失败」重试一次（模型偶发输出噪声/供应商静默
            # 忽略 response_format）；API/网络异常不在此重试（直接抛给 loop 降级），
            # 避免批量并发场景放大瞬时故障调用量（评审 L 项）。
            text = self._chat(
                chat_messages,
                max_tokens=1600,
                temperature=self.temperature,
                want_json=True,
            )
            return _extract_json_object(text)

    # ── 底层调用 ──────────────────────────────────────────────────
    def _chat(
        self,
        messages: List[Dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
        want_json: bool = False,
    ) -> str:
        kwargs: Dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        if want_json:
            try:
                resp = self.client.chat.completions.create(
                    response_format={"type": "json_object"}, **kwargs
                )
            except (TypeError, _BadRequestError):
                # 仅当 response_format **参数本身被拒**（SDK 签名不认 → TypeError，
                # 服务端 400 参数错误 → BadRequestError）时退回普通模式重试一次；
                # 网络/限流等其他异常直接抛给上层，不再无差别重打（评审 L 项：
                # 盲重试会在批量并发场景把瞬时故障的调用量放大一倍）。
                resp = self.client.chat.completions.create(**kwargs)
        else:
            resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content
