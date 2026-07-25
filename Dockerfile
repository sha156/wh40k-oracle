# Dockerfile —— FastAPI 后端镜像（BUILD-PLAN Stage 5）
#
# 设计取舍：镜像**只装代码与依赖**，4.5G 模型 / FAISS 索引 / sqlite 结构库
# 一律从宿主机只读挂载（见 docker-compose.yml）。理由：这些资产本就 gitignore、
# 由宿主机流水线（ingest.py / db_compile）产出，打进镜像会让镜像到 6G+ 且每次
# 重建索引都要重建镜像。
#
# 构建（在仓库根目录）：
#   docker compose build api
# 走代理构建（Clash 在宿主机 7897）：
#   DOCKER_BUILD_PROXY=http://host.docker.internal:7897 docker compose build api

FROM python:3.11-slim-bookworm

# 构建期代理：pip 需要出网；宿主机 Clash 用 host.docker.internal 访问。
# 只在构建期生效，不写进运行期环境（运行期不该出网到代理）。
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY="localhost,127.0.0.1"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 模型走本地快照（挂载的 opt/），HF_ENDPOINT 仅在快照缺失时才用得上。
    # 不设 HF_HUB_OFFLINE=1：该开关有已知崩溃问题，靠传本地绝对路径离线加载。
    HF_ENDPOINT=https://hf-mirror.com \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# ── 依赖层（与源码分层，改代码不重装依赖）────────────────────────
COPY requirements-docker.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
 && python -m pip install --no-cache-dir \
      torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu \
 && python -m pip install --no-cache-dir -r requirements-docker.txt

# ── 源码层（大件资产由 .dockerignore 挡在外面）──────────────────
COPY . .

# 非 root 运行；挂载卷都是 :ro，无需写权限
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 探针只问「进程活着吗」；「资产挂全了吗」看 /healthz 返回体的 ready 字段
# ——缺卷时服务照样该活着（好让人 curl 出来看缺了啥），不该被反复重启。
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

# workers=1 是刻意的：bge-m3 缓存在进程内（app.load_resources 走 st.cache_resource），
# 每多一个 worker 就多一份 GB 级模型常驻内存，而同步端点本就跑在线程池里、
# 单进程已能并发。要横向扩得先把模型服务拆出去。
CMD ["uvicorn", "web_api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--timeout-keep-alive", "75"]
