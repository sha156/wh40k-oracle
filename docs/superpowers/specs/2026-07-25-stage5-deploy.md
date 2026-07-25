# T5 · Stage 5 部署（本地 docker-compose 自用）

> 2026-07-25。BUILD-PLAN Stage 5 落地：`web/`（Next.js）+ `web_api/`（FastAPI）
> 从"只能手工起两个进程"变成"一条 `docker compose up` 起全栈"，并补上 Stage 5
> 既定的安全条款（key 只在服务端 env、限流、CORS、不提供原文/库整体下载）。

## 1. 形态裁决：镜像装代码，资产挂宿主机

本项目的运行期资产体量悬殊：

| 资产 | 体积 | 产出方 | 处置 |
|---|---|---|---|
| `opt/`（bge-m3 等模型） | 4.5 G | HF 下载 | 只读挂载 |
| `data/`（61 本 PDF） | 1.1 G | 人工放置 | **不挂**（运行期不读） |
| `local_vector_store/` | 29 M | `ingest.py` | 只读挂载 |
| `db/wh40k.sqlite` | 34 M | `db_compile` | 只读挂载 |
| `wiki/` | 8.3 M | `wiki_engine` | 只读挂载（跟仓库走） |

裁决：**镜像只装代码与依赖**，上述资产一律 compose 只读挂载。理由——它们本就
gitignore、由宿主机流水线产出；打进镜像会让镜像到 6 G+，且每次重建索引都要重建镜像。
`data/` 不挂是核对过的：`web_api` 运行期只读 FAISS 索引与 sqlite，PDF 仅
`ingest.py` 和 Streamlit 侧边栏统计用得上。

只读（`:ro`）是硬约束：容器无权写宿主机数据资产，所有写入走宿主机流水线。
测试 `test_compose_mounts_are_readonly_and_bound_to_loopback` 把这条钉死。

## 2. 产物清单

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 后端镜像（python:3.11-slim + CPU 版 torch） |
| `.dockerignore` | 把 4.5 G 资产与 `.env` 挡在构建上下文外 |
| `requirements-docker.txt` | 钉版依赖（取自本地 `.venv` 实测版本） |
| `web/Dockerfile` | 前端三段构建 → standalone 运行镜像 |
| `web/.dockerignore` | |
| `docker-compose.yml` | 两服务 + 四只读卷 + 端口绑 127.0.0.1 |
| `.env.example` | 全部环境变量的唯一说明书 |
| `web_api/preflight.py` | 启动资产前置校验 |
| `web_api/ratelimit.py` | 两档固定窗口限流 |
| `tests/test_web_api_stage5_deploy.py` | 28 条测试 |

## 3. 三个刻意的设计选择

### 3.1 `workers=1`

`app.load_resources()` 走 `st.cache_resource`，模型缓存在**进程内**。每多一个
uvicorn worker 就多一份 GB 级 bge-m3 常驻内存，而同步端点本就跑在线程池里、
单进程已能并发。要横向扩，得先把嵌入模型服务拆出去——那是另一件事。

### 3.2 torch 单独从 CPU 源装

`pip install sentence-transformers` 在 Linux 上会拉 CUDA 版 torch，凭空多 2 G+ 的
`nvidia-*` 依赖，而本项目全程 CPU 推理。故 Dockerfile 里先：

```dockerfile
pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
```

再装其余依赖时 `torch==2.8.0` 已满足，pip 不会覆盖。

### 3.3 镜像 Python 3.11 ≠ 本地 3.9

本地 `.venv` 是 Python 3.9.1；镜像用 3.11（torch 2.8 的 cp39 Linux 轮子不确定存在）。
代码本身按 3.9 语法写（`from __future__ import annotations`），向上兼容 3.11。
**这个版本差必须靠在镜像里另跑一遍 pytest 来兜底**，见 §6 验收。

## 4. 安全条款落地（Stage 5 既定）

- **key 只在服务端 env**：`DEEPSEEK_API_KEY` 由 compose 从 `.env` 注入进程环境，
  不写镜像层、不落盘。`.dockerignore` 排除 `.env`（进了镜像层就洗不掉）。
- **限流**：`web_api/ratelimit.py`，进程内固定窗口，两档配额——
  - `default` 120 次/分：查表类（图鉴、`/roster/validate` 实时重算，前端每次编辑都调）
  - `heavy` 20 次/分：`/chat`（花钱调 LLM）、`/simulate`、`/roster/critique`（蒙特卡洛）
  - `/healthz` 豁免（限流器把健康检查拒了会让编排系统误判服务已死）
  - `X-Forwarded-For` **默认不信**——客户端可随手伪造，信了等于把限流关掉；
    确实架在自己反代后面才设 `WEB_API_TRUST_FORWARDED=1`
  - 与既有并发信号量分工：信号量挡"同时"打满线程池，限流挡"持续"高频灌
- **CORS**：白名单（`WEB_API_CORS`），默认只放 localhost:3000。
  中间件顺序刻意为「先挂限流、后挂 CORS」——Starlette 后加的在外层，CORS 在外才能
  给 429 响应补跨域头、且浏览器 OPTIONS 预检不白占配额（已实测验证，见 §6）。
- **端口只绑 127.0.0.1**：本项目内含规则书衍生内容，不外露到局域网/公网。
- **不提供原文/库整体下载**：沿用现状——没有任何端点返回 PDF 或库整体导出，
  `/wiki/{path}` 有解析后路径必须仍在 `wiki_root` 内的目录穿越防护。
- 容器以非 root（uid 10001 / nextjs）运行。

## 5. 前置校验：不许静默降级

容器化后最阴险的事故是**卷没挂上**：FastAPI 照样起来、端点照样 200，但所有回答
静默降级成"知识库未构建"——正是本项目最忌讳的失败形态。

`web_api/preflight.py` 在启动时核对四类资产，缺失项在 `docker logs` 里带 `[缺!]`
吼出来并给修复命令，同时挂到 `/healthz` 的 `ready` 字段：

```
[preflight] 运行期资产核对：
[preflight]   [ok ] embed_model     /app/opt/models--BAAI--bge-m3/snapshots/5617a9f...
[preflight]   [ok ] vector_store    /app/local_vector_store/index.faiss
[preflight]   [ok ] structured_db   /app/db/wh40k.sqlite
[preflight]   [ok ] wiki            /app/wiki/index.md
[preflight] 必需资产齐全。
```

两个细节：

- **只下了一半的 bge-m3 快照算缺失**（判据与 `app.resolve_embed_model()` 一致：
  必须有 `modules.json`）。否则容器起来后要等第一次检索才在 HF 联网重试里超时，
  错得又晚又难查。
- `WEB_API_PREFLIGHT_STRICT=1` 时缺必需资产直接拒绝启动，给"宁可起不来也不要跑出
  降级答案"的场景用（比如给别人演示前）。默认不 strict，保持联调可用。

另有 `WEB_API_WARMUP=1`（compose 默认开）：启动即后台线程预加载 bge-m3，避免首个
提问干等 GB 级模型冷启动；预热失败**必须吼出来**并记进 `/healthz.warmup.error`，不吞。

## 6. 验收

| 项 | 结果 |
|---|---|
| 新增测试 | `tests/test_web_api_stage5_deploy.py` 28 条全绿 |
| 全库回归 | **1936 passed**（原 1908 + 28） |
| `docker compose config` | 通过，解析出 api / web 两服务 |
| 限流真实行为 | 配额 3 时 `[200,200,200,429,429]`，`Retry-After: 60` |
| `/healthz` 豁免 | 配额 1 下连打 20 次全 200 |
| 中间件顺序 | 429 响应带 `access-control-allow-origin`；配额耗尽后 OPTIONS 预检仍 200；非白名单 Origin 不回跨域头 |
| 前置校验 | 真实仓库四项全 `ok`，空目录四项全缺且每条带原因+修复法 |
| compose 一致性 | 每个必需资产目录都有对应 `:ro` 挂载（测试机械核对，防"挂载键写错→静默降级"） |
| **镜像构建 + 镜像内 pytest** | ⏳ 待办：需 Docker Desktop 守护进程（本机 CLI/compose v2.40.3 在，daemon 未起） |

最后一行是诚实的未完项：**Dockerfile 未经真实构建验证**。守护进程起来后要跑：

```powershell
docker compose build                       # 两镜像都能构出来
docker compose run --rm api python -m pytest tests/test_web_api_stage5_deploy.py tests/test_web_api_stage3.py -q
                                           # 镜像 Python 3.11 与本地 3.9 的版本差兜底
docker compose up -d
docker compose logs api | Select-String preflight   # 四项资产全 ok
curl http://127.0.0.1:8000/healthz          # ready: true
# 真检索一次——不能只看端点 200。opt/ 是 :ro 挂载，若 sentence-transformers
# 意外要往 cache_folder 写锁文件就会在这一步炸，而 /healthz 察觉不到：
curl -X POST http://127.0.0.1:8000/chat/sync -H "Content-Type: application/json" `
     -d '{\"question\":\"掩体给什么惩罚\"}'
# 浏览器开 http://localhost:3000 目检四页签
```

## 7. 已知边界

- 单实例自用：限流是**进程内**计数，横向扩多副本时这层要换成共享存储实现——
  届时别以为它还在生效。
- 前端 `NEXT_PUBLIC_API_BASE` 是**构建期**内联进浏览器包的，运行期改环境变量不生效；
  且它是浏览器去访问的地址，填 `http://localhost:8000`，不是 compose 服务名 `http://api:8000`。
- 没做 HTTPS / 反向代理 / 多租户鉴权——本次目标形态是本地自用。
- Streamlit 的 `app.py` 未容器化（`agent` 只是把它当模块只读调用）；要在容器里用
  classic 界面得另加一个服务。
