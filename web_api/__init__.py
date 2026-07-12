"""web_api — L6 网站化后端（BUILD-PLAN Stage 3）。

在 agent/loop.py 之上加一层 response_formatter，把自由文本回答 + 工具结果
转成前端零解析的结构化回答契约（镜像 web/src/lib/answer.ts），经 FastAPI SSE 下发。
"""
