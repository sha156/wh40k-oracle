"""agent 包 — L5 Agent 编排层（spec 第七节）。

工具箱 + Agent 循环 + 会话上下文。只读调用 L2/L3/L4 既有能力（wiki_engine/db_compile/
app.py 的检索链），不修改它们；未建模能力诚实打桩，绝不伪造结果。
"""
