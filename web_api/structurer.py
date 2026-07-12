"""web_api/structurer.py — 结构化 LLM（散文答案 → 槽位轻标记文本）。

复用 deepseek/glm 的 OpenAI 兼容接口，走一次「重排」调用：输入是主循环已经查证好的
散文答案 + 工具证据，输出严格 JSON 的 verdict/calc/sensitivity/followups。

铁律（承接 llm_client fail-closed）：只重排已有内容、不新增未经查证的数字或引用；
解析失败抛异常，交给 formatter 退化为散文 lede，绝不伪造槽位。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

_SYSTEM = """你是战锤40K规则参谋回答的「排版器」。上游参谋已用工具查证并写好散文答案，
你的唯一任务是把它**重排**成前端槽位，不新增任何未在散文/证据中出现的数字或引用。

只输出一个 JSON 对象（不要 markdown 代码块），结构：
{
  "verdict": {
    "label": "2-4字结论（如 值得带 / 不建议 / 需注意 / 规则如下）",
    "labelEn": "结论英文（如 Sanctioned / Censured / Caution / Ruling）",
    "lede": "结论段落（1-3句概述），用轻标记"
  },
  "calc": ["计算/推理步骤1", "步骤2", ...],   // 无计算则空数组
  "sensitivity": {"title": "◭ 敏感性 · ...", "text": "边界条件说明"} 或 null,
  "followups": ["追问1", "追问2", "追问3"]     // 最多3条，可空数组
}

轻标记规则（前端据此渲染，请正确使用）：
- 规则关键词用【】包裹：如【重型】【毁灭伤害】
- 引用角标用方括号数字：如 [1] [2]，数字对应下方「可用引用」的序号
- 需要强调的最终结论用 **双星号**：如 **值得带**
- 数字/属性（2.3、67%、3+、D6+1、S12、AP-4）直接写，前端自动加粗，不要额外标记

约束：
- lede/calc/sensitivity 的内容必须能在散文答案里找到依据，不得杜撰新数字。
- 若散文答案本身是「档案缺失/未建模」类，verdict.label 用「暂无法判定」，calc 空数组。
- 全部用中文，简洁口语，不用「综上所述」式八股。"""


def _extract_json(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("结构化 LLM 返回空")
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        if start == -1:
            raise ValueError("未找到 JSON 对象")
        depth, end = 0, -1
        for i in range(start, len(stripped)):
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            raise ValueError("JSON 不完整")
        obj = json.loads(stripped[start:end])
    if not isinstance(obj, dict):
        raise ValueError("结构化输出非对象")
    return obj


class OpenAIStructuringLLM:
    """deepseek/glm 兼容接口的结构化器。可注入 client 供单测。"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        temperature: float = 0.2,
        client: Optional[Any] = None,
    ):
        self.model = model
        self.temperature = temperature
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=base_url)

    def structure(
        self, question: str, prose: str, evidence: str, cites: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        cite_lines = "\n".join(
            "[{}] {}{}".format(
                c.get("n"), c.get("book", ""),
                (" 第{}页".format(c["page"]) if c.get("page") else
                 (" · " + c["term"] if c.get("term") else "")),
            )
            for c in cites
        ) or "（无）"
        user = (
            "用户问题：{q}\n\n"
            "参谋散文答案：\n{prose}\n\n"
            "可用引用（角标序号 → 出处）：\n{cites}\n\n"
            "工具证据摘要：\n{evidence}\n\n"
            "请按系统指令输出 JSON。"
        ).format(q=question, prose=prose, cites=cite_lines, evidence=evidence)

        kwargs: Dict[str, Any] = dict(
            model=self.model,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": user}],
            temperature=self.temperature,
            max_tokens=1600,
            stream=False,
        )
        try:
            resp = self.client.chat.completions.create(
                response_format={"type": "json_object"}, **kwargs)
        except Exception:
            resp = self.client.chat.completions.create(**kwargs)
        return _extract_json(resp.choices[0].message.content)
