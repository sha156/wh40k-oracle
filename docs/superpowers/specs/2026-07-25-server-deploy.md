# 上线：轻量部署到 49.232.104.101（图鉴 / 模拟器 / 军表三页签）

> 2026-07-25。接 `2026-07-25-stage5-deploy.md`（容器化）之后的**真实上线**记录。
> 目标机是一台跑着三个其他服务的 2 核 3.3 G 小机器，所以这次上的是**轻量模式**：
> 三个零 LLM 页签全量可用，规则问答页签诚实降级。

## 1. 为什么不是全量上线：一个实测数字

规则问答链需要把用户的问题向量化才能在 FAISS 里检索——这是**运行期**动作，
不是数据准备，索引做好了也免不掉。本地实测这条链的常驻内存：

| 阶段 | RSS |
|---|---|
| 起点 | 13 MB |
| `import app` | 351 MB |
| 加载 bge-m3 + FAISS | 1883 MB |
| **跑完一次查询嵌入** | **3107 MB** |
| 再建 BM25 | 3207 MB |

目标机：**3.3 G 总内存 / 2.3 G 可用 / 无 swap**，且已经驮着 mygf(systemd)、
elina-bot(pm2)、auction-backend(pm2)、SpeakingLab(openresty 静态)、1Panel。
3.2 G 塞进 2.3 G 只有一个结果：OOM——而 OOM killer 未必只杀我们。

裁决：**上 `WEB_API_RETRIEVAL=off` 的轻量模式**。图鉴 / 模拟器 / 军表是纯
sqlite + 引擎计算，实测常驻 **51–79 MB**。聊天页签走诚实降级，明说原因。

将来要补齐问答，走**远程嵌入 API**（同为 bge-m3 即可复用现有索引），
而不是往这台机器上塞模型。

## 2. 架构

```
浏览器
  └─ http://49.232.104.101:8100/          openresty（NetworkMode=host）
       ├─ /            → 静态文件 /opt/1panel/www/sites/wh40k/index
       │                 （Next 静态导出产物，服务器上不跑 node 进程）
       └─ /api/*       → proxy_pass 127.0.0.1:8210
                          systemd wh40k-api（uvicorn，venv 127 M，常驻 ~80 M）
                            └─ /home/ubuntu/wh40k/db/wh40k.sqlite（本地流水线产出）
```

同源部署，前端不发跨域请求，CORS 白名单可留空。

**数据只在本地生产**：`ingest.py` / `db_compile` / `llm_refine` 一律不上服务器，
服务器只消费成品。部署脚本因此是单向推送。

### 前端为什么用静态导出而不是 standalone

四个页签全是 `"use client"`，没有 route handler / middleware / next-image /
generateStaticParams——静态导出成立。导出后 openresty 直接托管，**服务器上连
node 进程都不用起**，在这台机器上省下的是 100–200 M 常驻内存。

`next.config.ts` 用 `NEXT_OUTPUT` 在两种形态间切：`export`（本次）/
`standalone`（容器化，默认）。加上述任一特性之前，先想清楚这条路还通不通。

## 3. 一次性初始化（已执行）

```bash
# 服务器
mkdir -p /home/ubuntu/wh40k/{db,logs}
cd /home/ubuntu/wh40k && python3 -m venv .venv            # 系统 3.10.12
.venv/bin/python -m pip install -r requirements-server.txt \
    -i https://mirrors.cloud.tencent.com/pypi/simple/     # 装完 127 M
sudo cp deploy/wh40k-api.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now wh40k-api
sudo cp deploy/openresty-site.conf /opt/1panel/www/conf.d/wh40k.conf
sudo docker exec 1Panel-openresty-CMak nginx -t           # 先验语法
sudo docker exec 1Panel-openresty-CMak nginx -s reload    # 热重载，别 restart
```

`/home/ubuntu/wh40k/.env`（权限 600）：`WEB_API_RETRIEVAL=off`、`WEB_API_WARMUP=0`、
`WEB_API_TRUST_FORWARDED=1`（反代在前）、`DEEPSEEK_API_KEY=` 空（三个页签零 LLM）。

日常更新一律走 `bash deploy/deploy.sh [all|code|data|web|verify]`。

## 4. 为轻量模式补的两处代码

### `WEB_API_RETRIEVAL=off` 是一等公民，不是"坏掉的状态"

- **前置校验**：模型与索引降为 `required=False`，日志标 `[略]` 而非 `[缺!]`，
  detail 写明"按设计不需要"。否则 `ready` 天天 false，人就学会无视它——
  真出事那次也照样无视。
- **`/chat` 提前降级**：不拦的话 agent 会一路跑到 `rag_search` 才因缺 torch 抛错，
  被 `except` 吞成"未检索到相关段落"——**看起来像"库里没有这条规则"，
  而真相是"这台机器没装检索"**。这种错误比崩溃更坏。
- **降级措辞指向真因**：`_degraded_answer` 原本硬编码"未配置 LLM（key 缺失）"前缀。
  这台机器主因是没开检索，先甩 key 缺失等于把人往错方向引。改成传完整说明。

## 5. 验收（全部实测，非纸面）

| 项 | 结果 |
|---|---|
| 结构库传输完整性 | sha256 `143e9d8078b03754`、13,275,136 字节，两端一致 |
| 后端导入 | 服务器上 `import web_api.main` 成功，重依赖（torch/faiss/langchain/streamlit）**零** |
| 启动前置校验 | `[略] embed_model` `[略] vector_store` `[ok] structured_db` `[ok] wiki` → 必需资产齐全 |
| `/api/healthz` | `ready=true, retrieval=false, 缺失必需资产=无` |
| 静态四页 | `/` `/codex` `/simulator` `/roster` 均 200 |
| 图鉴真数据 | 25 阵营；SM 298 单位，首个"阿加通连长" |
| 军表真数据 | SM 分队 56 个 |
| **模拟器真跑** | 阿斯托拉斯（近战，loadout 显式指定）3000 次蒙特卡洛 → 期望伤害 **3.526**、期望击杀 **0.35** |
| 聊天降级 | `degraded=true`，正文明说"轻量部署、检索未启用、三个页签可用" |
| 内存占用 | **79 MB**（对比完整检索栈 3207 MB） |
| 同机服务未受影响 | mygf active；pm2 auction-backend / elina-bot online；端口 8000 / 3000 仍 200 |
| 本地测试 | 新增 8 条（共 36 条 Stage 5 测试）全绿 |

模拟器那条是关键：**装配成功 ≠ 有输出**。引擎不猜默认装配，必须显式传
`loadout`；纯近战武器点射击阶段会得到 0 攻击且 `ok=true`。所以验收要看真数字。

## 6. ⚠ 待办：外网还进不去

`http://49.232.104.101:8100/` 从外部访问超时。已排除主机侧：ufw inactive，
iptables 的 `YJ-FIREWALL-INPUT` 链是 IP 黑名单、不按端口拦；服务器访问自己的
**内网回环** 8100 一切正常。

结论：**腾讯云安全组没放行 8100**，需要在控制台加一条入站规则
（TCP 8100，来源 0.0.0.0/0）。放行后 `bash deploy/deploy.sh verify` 会全绿，
外网即可访问。

## 7. 已知边界

- 规则问答页签线上不可用（原因如 §1），补齐方案是远程嵌入 API，非本次范围。
- 无 HTTPS：8100 是纯 HTTP。要 HTTPS 得走域名 + 1Panel 申请证书。
- 限流是**进程内**计数，单实例有效；`WEB_API_TRUST_FORWARDED=1` 是因为
  openresty 在前，直接对外时必须改回 0（XFF 可伪造）。
- systemd 挂了 `MemoryMax=600M`：本服务失控时先杀自己，别连累同机四个服务。
  轻量模式实测 51–79 M，余量充足。
