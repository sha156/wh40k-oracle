"""agent/llm_client.py — 真实 LLMClient 实现（接线 app.py 前的最后一块）。

实现 agent.loop.LLMClient Protocol（classify_intent + next_step），后端走
deepseek-flash / glm-4-flash 的 OpenAI 兼容接口（openai SDK，非流式）。

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
    "DeepSeek": ("https://api.deepseek.com", "deepseek-flash"),
    "ZhipuAI (GLM-4)": ("https://open.bigmodel.cn/api/paas/v4/", "glm-4-flash"),
}

# TOOL_SPECS 只有 name+description，缺参数名。补一张 arg 提示表（只读，不改 tools.py）
# 让模型知道每个工具怎么传参。未列出的工具默认无参数 {}。
_TOOL_ARG_HINTS: Dict[str, str] = {
    "list_faction_units": '{"faction": "阵营英文名/中文名/ID", "offset": 0, "limit": 20}（总数不受分页限制；不要从 search_wiki 的前十条搜索结果推断总数）',
    "search_wiki": '{"query": "中文关键词"}',
    "get_entity": '{"name_or_id": "用户原文里的中文单位名（工具内部自动解析俗名/译名）"}',
    "get_keyword_definition": '{"keyword": "USR 或核心概念名"}',
    "get_datasheet": ('{"name_or_id": "用户原文里的中文单位名（内部解析别名到 L3 结构库）。'
                      '单位称谓必须整串原样传入、禁止截短或改写——「机械教游侠」「死亡连无畏机兵」'
                      '这类连写限定名是名字的一部分（截成「游侠」会精确命中另一阵营的同名单位并'
                      ' confident 错答，别名层认识全名）；仅「XX的YY」所属格才拆开传 YY'
                      '（「吞世者的地狱兽」→ 传「地狱兽」）；'
                      '若返回 ambiguous，再按阵营用候选串重查（如 \\"Helbrute (WE)\\"）"}'),
    "entity_resolver": '{"name": "中文/英文/俗名"}',
    "calc_points": ('{"unit_list": ["单位名", ...]}：中文名/英文名/canonical id 都可以，'
                    '请保留普通/装备版本等完整限定名。historical_points是已删除资料的旧点数，'
                    '必须标注历史，不能当当前点数或替换成另一个同名版本；'
                    '一次问多个单位就把它们全部放进同一个 unit_list（返回值逐个对应，'
                    '答题时四个问了几个就要给几个）'),
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
    "validate_roster": '{"roster_text": "Faction: Space Marines\nDetachment: Gladius Task Force\n5x Intercessor Squad\nApothecary Biologis | models=1 | warlord"}（每行一个单位、明确模型数；保留用户所有行，不编装配）',
    "critique_roster": '{"roster_text": "与 validate_roster 相同格式，含 Faction/Detachment 和明确模型数"}',
    "archive_answer": '{"title": "标题", "content": "正文"}',
}

_INTENT_SYSTEM = (
    "你是战锤40K规则问答系统的意图分类器。把用户输入分到且仅分到以下之一：\n"
    "查 = 查规则/单位/数据/关键词定义；\n"
    "判 = 判定某具体情形下规则如何裁定（先后顺序、能否触发等）；\n"
    "算 = 计算点数/军表分值；\n"
    "谋 = 战术推演/模拟对战/谁能打赢；\n"
    "闲聊 = 寒暄、记录用户偏好、回忆本次对话中用户说过什么（例如：我刚才说用哪个阵营）。\n"
    "回忆用户自己的选择不需要查规则，归闲聊；但追问该单位现在的点数、规则或能力仍归查/算。\n"
    "只输出上述一个分类，不要任何解释、标点或引号。"
)

_NEXT_STEP_CONTRACT = """你是「铁幕」，战锤40K规则参谋（现行第11版：11版核心规则/Faction Pack 补丁 + 官方仍合法的十版 codex 兵牌基底），正在一个工具调用循环中工作。
每一步你必须**只输出一个 JSON 对象**（不要 markdown 代码块外的任何多余文字），二选一：

1) 调用工具（需要查证时）：
{{"type": "tool_call", "tool": "<工具名>", "args": {{<参数>}}}}

2) 给出最终答案（信息足够时）：
{{"type": "final", "content": "<中文回答，含数字与引用>", "sources": [{{"book": "书名", "page": 页码}}]}}

可用工具：
{catalog}

工具使用策略：
- 用户先问陌生名称「是什么单位/属于哪个阵营」，即使同时问点数，也先用 entity_resolver
  核对身份，再对已确认的单位查属性/点数。名字仅有 suggestions 时须明确「库里查不到这个名字」，
  不能把猜测当成身份；若它可能是术语或俗名，仍可用 rag_search 查原文，不据此断言现实中不存在。
- 问某阵营有多少单位/兵牌、完整清单时先用 list_faction_units。区分结构库兵牌数量与
  官方 MFM 点数条目；有点数不代表已有完整兵牌。共享兵牌/关键词替换等规则另用 rag_search 查证。
- 本轮消息之前的 user/assistant 消息是同一会话的历史。回忆用户说过的阵营、偏好或选择时，
  直接依据这些消息回答；历史中没有就如实说没有。历史答案不是当前官方规则/点数的证据，
  用户问「它现在多少分」之类的问题仍必须用工具重新查证。
- **问属性/数值**（M/T/Sv/W/OC/Ld、武器 A/BS/WS/S/AP/D、单位点数）时，**先用 get_datasheet**，
  直接传用户原文里的中文单位名——它直查 L3 结构库（英文权威真值 + 中文别名层），是数值题的
  **首选**，避免 PDF 检索被译名/拍扁坑。get_datasheet 查空再退到 get_entity / rag_search。
- **问技能效果/单位背景/军表构成**时，直接用用户原文里的中文单位名调 get_entity，
  它内部会自动解析社区俗名与规则书译名；候选中的阵营限定名和 canonical id 也可以重查。
  兵牌只写出某项阵营能力的名称、次数或距离时，还没有回答该能力的具体效果：必须用
  rag_search 检索该阵营与能力名称，结合 codex 基底和最新 Faction Pack 补丁说明效果。
  用户的俗称不必等于正式技能名；若卡片有相关能力，先查其规则正文，不能只因标题不同就
  断言没有该能力或宣布档案缺失。引用必须对应实际取回的正文，不要把改关键词的补丁页当整张兵牌出处。
- 问 USR / 核心概念定义时用 get_keyword_definition。
- **问「相比以前/更新了什么/改了哪些」是版本比较，不能只查现行文本就结束。**
  已知规则名时先用 get_keyword_definition 或 search_wiki 定位规则及已记录的版本边界，再查证需要的原文。
  先找出现行规则与至少一份有出处的旧版/修订说明；必要时分开用 rag_search 检索当前版本和旧版本。
  明确比较基准（书名、日期/版号，以取回的资料为准），但不要把所有版本信息堆在开头。用户未指定「以前」时，可用库内能验证的
  最近旧基准并明说，不必先反问；没有旧原文则给出已查证的现行规则，明确无法确认哪些是新增。
  分清「确实改动」「保持不变」「本次证据不能确认」；“Change to”表示替换文本，不证明每句话都是新加。
  旧版与新版事实分别标来源，不能拿同一张现行页为想象的旧规则背书。
  排除名单少了某阵营，不等于该阵营一定获得能力：还要核对其 codex/Faction Pack 是否替换该军队规则。
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
- **工具查不到 ≠ 该事物不存在**。工具返回 "found": false / "unresolved" / 「未找到」时，
  只说明这条查询路径没命中，必须换工具或换名字再查一次（get_datasheet / entity_resolver /
  rag_search 兜底）。**绝不允许**据此凭记忆输出「这个单位/阵营不存在」「不属于战锤40K」
  「没有官方点数」之类的**否定性事实断言**——查不到就说查不到。
- **近似匹配的结果必须当场标明是近似匹配**。工具返回 "suggestions"（库里长得像但并不
  相同的名字）或 "confidence": "fuzzy" 时：先说清用户给的名字库里有没有，再把近似名
  **明确标注为猜测**。绝不允许把一个长得像的单位当成用户问的那个来介绍数值/技能/点数——
  用户看不出这张兵牌是换来的，这比直接说「查不到」危险得多。
- 若档案中确无相关信息，直接回复「档案缺失，建议查阅原始规则书」，绝不编造。
- 属性/攻击数据尽量用表格或粗体呈现。
- 先直接回答所问效果；不主动扩写无关型号、点数或分队特例。候选名仅表示名称近似或歧义，
  未核实的候选不能被描述为用户所问的单位类别。

回答深度与组织：
- 写给正在玩游戏的人，不写成资料审计报告。开头一两句直接说答案，先让用户明白到底变了什么。
- 简单点数/单个数值问题通常一两句加来源即可：不追加未被问到的整套属性，不换个标题再重复点数。
- 开放问题在一次回复里讲清用户需要的内容；完整不等于冗长。通常按两到四个相关主题组织，
  同一事实只解释一次。不要同时输出「版本比较」「逐项拆解」「重要限制」来重复同一批内容。
  主题数不是硬上限：用户问完整列表时，实际条目、效果、条件必须齐全；不要为了短而省略关键规则。
- 版本比较优先写「改了什么」「没变什么」「对你有什么影响」，每组只写与问题有关的信息。
  用户问改动时，别先整段抄现行规则再逐项重复；把当前效果和适用条件放进对应的变化/不变说明。
  多个比较基准要明确区分：最近一次没改与相对更早版本有改动可以同时成立，不能混成自相矛盾的结论。
  书名/版本/日期可以合并为末尾一句比较说明，详细页码交给引用。不要反复解释检索过程、证据边界或
  “Change to”的编辑含义，除非用户问的就是这些，或它直接改变答案。
- 首次出现陌生缩写时用日常语言解释，例如点数表中的阵营分类，而不是只写「MFM 分节排除口径」。
  不要使用「口径」「判定：确实改动」「证据边界」等审计套话。先说谁能获得什么效果，再给出处。
  必要的适用条件随相关结论一起说明；不把同一警告复制到开头、正文、结尾各一次。
  不用「想了解的话再问我」把本该回答的主体内容推给追问，也不扩写无关的禁用单位长名单。
- 事实必须来自本轮工具证据；解释或战术推论需标明推论，不能为了凑长答案补造细节。
- 工具没有返回某字段，只能说「本次未检索到」，不能据此断言该资料不存在。尤其不得把某单位
  未返回 historical_points 改写成「无历史缓存点数」。不要引入用户问题和本轮工具证据中都未出现的
  单位、装备版本或变体名称，也不要用这些未查证名称生成追问。
- 工具返回 historical_record.identity_scope 时，它是从保留原文验证出的历史兵牌身份、编成与版本边界；
  回答必须采用该边界，不得反称缓存没有区分其中明确排除的版本。字段缺失时仍只说明本次未检索到。
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
        # SessionContext stores display prose, but this provider conversation
        # uses JSON steps. Plain assistant history triggered blank JSON-mode
        # responses in live multi-turn recall (2026-09-18). Restore the envelope
        # only on the wire; history is still context, never fresh rule evidence.
        return {"role": "assistant", "content": json.dumps(
            {"type": "final", "content": str(content), "sources": []},
            ensure_ascii=False,
        )}
    if role == "tool":
        name = msg.get("name", "?")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, default=_json_default)
        # Inventory is explicitly paginated (<=50 units, <=10 names/page).
        # Splitting its JSON would lose rows while still claiming returned=N.
        if len(content) > 4000 and name != "list_faction_units":
            # 保**头尾**而不是只保头（审查 R1-L1）：get_datasheet 叠加中文层后整包常超限，
            # 而数值多在尾部（武器表、点数、同名消歧披露）——只留前 4000 字等于把答案本身
            # 切掉，模型却只看到一句「已截断」。
            head, tail = content[:2600], content[-1200:]
            content = (f"{head}\n…（中间省略 {len(content) - 3800} 字；"
                       f"如需被省略的部分，请缩小查询范围后重查）…\n{tail}")
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
            max_tokens=3200,
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
                max_tokens=3200,
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
        if self.model == "deepseek-flash":
            # V4 defaults to thinking. Preserve the old chat mode: classification
            # has an eight-token budget, too small for hidden reasoning first.
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
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
