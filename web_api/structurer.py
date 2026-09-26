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
    "lede": "直接回答问题的开篇段落，用轻标记；后续完整解释放在 calc"
  },
  "calc": ["规则效果/解释/计算步骤1", "步骤2", ...],   // 承载完整正文，不限于计算
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
- 缺少字段不是否定性证据。散文/工具证据没有明确证明时，不得写「无历史缓存点数」「不存在历史记录」
  等断言。不得引入用户问题、散文和工具证据中都没有出现的单位、装备版本或变体名称；followups 也受此限制。
- 保留全部独立信息，不必保留重复措辞：原文回答问题的规则列表、表格必须逐项保留，包含每项名称、效果、数值与限制。
  不能用「规则如下」「见命令表」替代实际内容；没有数学计算也必须保留规则效果。可拆成多条，不限制条数。
- 前端会把 lede、calc、sensitivity 连成同一条聊天回复。calc 是正文段落，不要强写成算式或重复结论。
  lede 一两句直答，calc 按相关主题合并成自然段。不要把每一个条件都拆成单独一条，导致一屏全是碎片。
  版本比较通常三组：**改了什么**、**没变什么**、**对使用的影响**；只用原文实际需要的组，不套固定清单。
  不先再抄一遍「现行规则全文」；相关效果合并到变化/不变/影响里。只把重复文字合并，不能删独立条件。
  同一个事实或警告只出现一次；合并「版本比较」「逐项拆解」「重要限制」中重复的内容。
  保留比较基准和真正影响结论的限制，但把密集日期/书名放在末尾一小段，不要抢在直接答案前。
  sensitivity 仅用于正文尚未讲过的重要补充；已经解释的限制不能再复制一遍，优先 null。
  简单点数题把数值、模型数和引用合并在 lede，calc 可空，不附无关属性或机械追问。
  轻标记应克制：只强调主题或关键结论，不把普通名词、每个条件都包成关键词。
  用玩家能懂的说法：例如「官方点数表中的阵营分类」，不要重复「MFM 分节排除口径」之类术语。
  原文没有核实旧版本时，保留该限制，不能把现行规定排版成已证实的新旧差异。
- 引用必须按事实来源分开：标为「结构库兵牌」的次数、距离、属性等用「L3 结构库」角标；
  规则正文效果才用实际取回的书页。兵牌关联的补丁页、通用规则页不能替兵牌特有字段背书。
  散文写明的来源边界必须保留；没有对应引用时保留文字来源说明，不得硬配另一条页码。
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
        model: str = "deepseek-flash",
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
            max_tokens=3200,
            stream=False,
        )
        if self.model == "deepseek-flash":
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        try:
            resp = self.client.chat.completions.create(
                response_format={"type": "json_object"}, **kwargs)
        except Exception:
            resp = self.client.chat.completions.create(**kwargs)
        return _extract_json(resp.choices[0].message.content)
