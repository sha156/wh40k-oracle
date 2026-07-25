# 规则问答上线就绪（换服务器后一条命令开检索）

> 2026-07-25。裁决：**不接远程嵌入 API**，等换到更大的服务器后在本机同一套代码上开
> 本地检索链。本文把"开检索"从一次探险变成一份清单：门槛是多少、推什么、翻哪个开关、
> 怎么确认它真的在跑（而不是静默降级）、怎么退回去。
>
> 现状（2026-07-25）：`http://49.232.104.101:8100` 跑轻量模式——图鉴 / 模拟器 / 军表
> 三个零 LLM 页签实跑，常驻 52 MB；规则问答页签 `WEB_API_RETRIEVAL=off` 诚实降级。

## 一、为什么现役机器不能开

| 项 | 现役机器 | 检索链需要 | 结论 |
|---|---|---|---|
| 内存 | 3399 MB，**无 swap**，还要养 mygf / elina-bot / SpeakingLab | 检索栈实测常驻 **3.2 GB**（bge-m3 CPU + FAISS + langchain） | 塞不下；硬塞会 OOM 连累同机服务 |
| /home 可用磁盘 | 13 GB | `opt/` 模型 **4.5 GB** + 索引 29 MB + 重依赖 venv 约 3 GB | 勉强够，但和内存一起看没意义 |

所以脚本里把门槛写成硬闸：**内存 ≥7000 MB、/home 可用 ≥12 GB**，不够就拒绝往下走
（`REQ_MEM_MB` / `REQ_DISK_GB` 在 `deploy/deploy.sh` 顶部，换机后按实际调）。

现役机器上实跑一次门槛核对，输出就是这样——这是**预期行为**，不是故障：

```
$ bash deploy/deploy.sh capacity
== 换机门槛核对（内存/磁盘）
  内存 3399 MB（需 ≥7000）
  /home 可用 13 GB（需 ≥12）
  ✗ 内存不足：检索栈实测常驻 3.2G，本机塞不下
```

## 二、新服务器选型建议

- **内存 ≥8 GB**：检索栈 3.2 G + 系统与其它服务 + 余量。4 G 机器不要试（无 swap 时
  首个 `/chat` 加载 bge-m3 就会被 OOM killer 干掉，表现为"问一句服务就重启"）。
- **磁盘 ≥30 GB**：模型 4.5 G + 重依赖 venv 3 G + 系统 + 日志。
- CPU 2 核够用（嵌入是 CPU 推理，慢但可接受；首次加载约 30–60 s，靠 `WEB_API_WARMUP=1`
  在启动时后台预热，避免第一个用户等超时）。
- 不需要 GPU。装 torch 必须走 CPU 源（`--index-url https://download.pytorch.org/whl/cpu`），
  否则白背 2 GB nvidia 依赖——`retrieval-on` 已经这么写了。

## 三、迁移与开启（新机器上按顺序跑）

一次性初始化（建 venv、装 systemd 单元、配 openresty 反代、开安全组）照
`docs/superpowers/specs/2026-07-25-server-deploy.md` §3 做，与本文无关。之后：

```bash
# 0) 门槛核对——不过就别往下走（省得传一半发现塞不下）
bash deploy/deploy.sh capacity

# 1) 代码 + 结构库 + 前端（和现在完全一样）
bash deploy/deploy.sh all

# 2) 推模型与索引：opt/ 4.5G + local_vector_store/ 29M，十几分钟，传完对 sha256
bash deploy/deploy.sh assets

# 3) 装重依赖 + 翻开关 + 抬 systemd 内存闸（600M→5G）+ 重启 + 验收，幂等可重跑
bash deploy/deploy.sh retrieval-on
```

`retrieval-on` 做的四件事（都在 `deploy/deploy.sh`，不需要手工上机操作）：

1. `pip install torch --index-url .../cpu` 再 `pip install -r requirements.txt`，
   然后**裸调一次** `import torch, faiss, langchain_huggingface` 确认真装上了；
2. `.env` 里 `WEB_API_RETRIEVAL=on`、`WEB_API_WARMUP=1`（幂等 sed，键不存在则追加）；
3. 写 systemd drop-in `retrieval.conf`：`MemoryMax=5G` / `MemoryHigh=4G`
   （轻量模式的 600M 闸会让检索栈刚加载就被杀）；
4. 重启并跑 `verify-retrieval`。

**LLM key**：`.env` 的 `DEEPSEEK_API_KEY` 留空也不会崩——后端会以 Fake 直答降级，
但那时 `/chat` 的答案没有检索引用，`verify-retrieval` 的"引用条数"断言会红。
要真正可用就把 key 填进服务器 `.env`（key 只在服务端，永不进版本库）。

## 四、验收：怎么确认它真的在跑

`bash deploy/deploy.sh verify-retrieval`。只看 HTTP 200 是不够的——检索关着的时候
三个零 LLM 页签照样全 200。所以这一步断言三件事：

| 断言 | 拦住的失败 |
|---|---|
| `/api/healthz` 的 `retrieval is True` | 开关没生效（`.env` 没改到 / 服务没重启） |
| `assets` 里没有 `required && !ok` | 卷没挂上 / 模型路径不对 → 会静默降级成"检索关闭" |
| `POST /api/chat/sync` 返回的 `cites` 非空 | 检索链没真参与（LLM 凭记忆直答），这正是最难发现的那种"能用但是假的" |

外加打印常驻内存（实测应在 3.2 GB 上下）和预热状态。

**本文写作时已在本机（有完整检索栈）跑过 healthz 那段断言逻辑**，输出
`ready=True retrieval=True llm=True 缺失必需资产=无`、断言通过；`chat/sync` 那段的
断言逻辑与之同源，但**整条 `retrieval-on` / `verify-retrieval` 在真机上尚未跑过**
——没有大机器，跑不了。换机后第一次跑请对着上表逐条核对，别只看退出码。

## 五、退回去

```bash
bash deploy/deploy.sh retrieval-off   # .env 关开关 + 删内存闸 drop-in + 重启 + 常规验收
```

资产（`opt/`、`local_vector_store/`）留在盘上不删，随时能再 `retrieval-on`。

## 六、不在服务器上做的事（永远）

`ingest.py`、`llm_refine.py`、`db_compile`、`wiki_compile`、`scripts/` 一律不上服务器：
**数据只在本地生产**，服务器只消费成品（`db/wh40k.sqlite`、`wiki/`、`local_vector_store/`）。
换嵌入模型或改分块必须在本地 `--rebuild` 后重新 `deploy.sh assets`——索引与模型是一对，
分开更新会得到一份"能查但查不准"的库。

## 七、遗留

- 真机执行（等大机器）：`assets` / `retrieval-on` / `verify-retrieval` 三步。
- HTTPS / 域名 / 鉴权仍未做（现在是裸 IP + http），换机时一并规划。
- 聊天页签的浏览器冒烟（`web/e2e/`）等检索链上线后补。
