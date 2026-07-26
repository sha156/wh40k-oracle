#!/usr/bin/env bash
# deploy/deploy.sh —— 把 wh40k-oracle 轻量站推到服务器（在**本地仓库根目录**执行）
#
#   bash deploy/deploy.sh          # 全量：代码 + 数据 + 前端
#   bash deploy/deploy.sh code     # 只推 .py（改后端逻辑）
#   bash deploy/deploy.sh web      # 只推前端静态产物
#   bash deploy/deploy.sh data     # 只推 db/ 与 wiki/（本地重建库之后）
#   bash deploy/deploy.sh verify   # 只跑验收，不推任何东西
#
# ── 规则问答（检索链）上线，只在换到大机器后用 ──
#   bash deploy/deploy.sh assets   # 推 opt/ 模型(4.5G) + local_vector_store/ 索引(29M)
#   bash deploy/deploy.sh retrieval-on   # 装重依赖 + 打开 WEB_API_RETRIEVAL + 抬内存闸
#   bash deploy/deploy.sh retrieval-off  # 退回轻量模式（不删资产）
# 现役 2 核 3.3G 机器**跑不动**：检索栈实测常驻 3.2G（无 swap），且 opt/ 要 4.5G 磁盘。
# 换机门槛与整套步骤见 docs/superpowers/specs/2026-07-25-retrieval-online-readiness.md
#
# 前提：~/.ssh/config 里有 mygf 别名；服务器已按
# docs/superpowers/specs/2026-07-25-server-deploy.md §3 做过一次性初始化。
#
# 传输用 tar-over-ssh 而不是 rsync：本地是 Windows Git Bash，**没有 rsync**
# （服务器上有，但两端都得有才行）。tar 两端都在，且单次连接传完，比 scp 逐文件快。
#
# 设计原则：**数据只在本地生产**。ingest.py / db_compile / llm_refine 一律不上服务器
# （服务器 3.3G 内存跑不动嵌入），服务器只消费成品 db/wh40k.sqlite + wiki/。
# 所以这里是单向推送，没有回拉。
set -euo pipefail

HOST="mygf"
REMOTE="/home/ubuntu/wh40k"
SITE="/opt/1panel/www/sites/wh40k/index"
BASE="http://127.0.0.1:8100"
MODE="${1:-all}"

say() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

# 代码：只推运行期真正 import 到的包。数据管线（ingest.py / llm_refine.py /
# scripts/）不推——服务器跑不动也不该跑。
push_code() {
  say "推代码 → $REMOTE"
  tar czf - --exclude='__pycache__' --exclude='*.pyc' \
      web_api agent engines wiki_engine db_compile dsl_payloads deploy \
      app.py corpus_manifest.py corpus_manifest.json md_chunker.py \
      hf_embeddings_compat.py requirements-server.txt \
    | ssh "$HOST" "tar xzf - -C $REMOTE"
  echo "  ok"
}

# 数据：本地流水线的成品。db 13M + wiki 8M，够小，每次全量同步不心疼。
# 传完对 sha256——静默截断过一次就够了。
push_data() {
  say "推数据（db + wiki）"
  tar czf - --exclude='.obsidian' --exclude='_from_db_drift.md' \
      wiki db/wh40k.sqlite \
    | ssh "$HOST" "tar xzf - -C $REMOTE"
  local local_sum remote_sum
  local_sum=$(sha256sum db/wh40k.sqlite | cut -d' ' -f1)
  remote_sum=$(ssh "$HOST" "sha256sum $REMOTE/db/wh40k.sqlite | cut -d' ' -f1")
  if [ "$local_sum" != "$remote_sum" ]; then
    echo "  ✗ 结构库 sha256 不一致！本地 ${local_sum:0:16} vs 远端 ${remote_sum:0:16}" >&2
    exit 1
  fi
  echo "  ok（结构库 sha256 一致 ${local_sum:0:16}）"
}

# 前端：本地构建静态产物再推。服务器不装 node、不跑 next build（3.3G 内存跑不动）。
push_web() {
  if [ ! -d web/out ]; then
    cat >&2 <<'TIP'
web/out 不存在。先在 **PowerShell** 里构建（别用 Git Bash——MSYS 会把 /api
当路径转写成 C:/.../Git/api，错值会被内联进 JS 包里，页面所有请求都打错地址）：

  cd web
  $env:NEXT_OUTPUT="export"; $env:NEXT_PUBLIC_API_BASE="/api"; npm run build
TIP
    exit 1
  fi
  say "推前端 → $SITE"
  # 先清空再解包：静态产物带 hash 文件名，不清会越堆越多
  ssh "$HOST" "sudo mkdir -p $SITE && sudo chown -R ubuntu:ubuntu $(dirname "$SITE") && rm -rf $SITE/*"
  (cd web/out && tar czf - .) | ssh "$HOST" "tar xzf - -C $SITE"
  echo "  ok"
}

restart_api() {
  say "重启后端"
  ssh "$HOST" "sudo systemctl restart wh40k-api && sleep 4 && systemctl is-active wh40k-api"
}

# ── 规则问答（检索链）上线：只在换到大机器后用 ─────────────────────────
# 门槛（实测值，别拍脑袋）：内存 ≥8G（检索栈常驻 3.2G，且要留给 mygf 等同机服务）、
# 磁盘 ≥12G 空闲（opt/ 4.5G + 索引 29M + 重依赖 venv ~3G + 余量）。
REQ_MEM_MB=7000
REQ_DISK_GB=12

# 换机门槛核对：不够就明说不够、拒绝往下走，不做"推一半发现塞不下"
check_retrieval_capacity() {
  say "换机门槛核对（内存/磁盘）"
  ssh "$HOST" "
    mem=\$(free -m | awk '/^Mem:/{print \$2}')
    disk=\$(df -BG --output=avail /home | tail -1 | tr -dc '0-9')
    printf '  内存 %s MB（需 ≥%s）\n' \"\$mem\" '$REQ_MEM_MB'
    printf '  /home 可用 %s GB（需 ≥%s）\n' \"\$disk\" '$REQ_DISK_GB'
    fail=0
    [ \"\$mem\"  -ge $REQ_MEM_MB  ] || { echo '  ✗ 内存不足：检索栈实测常驻 3.2G，本机塞不下' >&2; fail=1; }
    [ \"\$disk\" -ge $REQ_DISK_GB ] || { echo '  ✗ 磁盘不足：opt/ 模型就要 4.5G' >&2; fail=1; }
    [ \$fail -eq 0 ] || exit 1
    echo '  ok'
  "
}

# 资产：4.5G 模型 + 索引。走 tar-over-ssh 单连接（本地无 rsync），传完对 sha256。
# 传输约十几分钟，别在不稳定的网络上开始。
push_assets() {
  check_retrieval_capacity
  [ -d opt ] && [ -d local_vector_store ] || {
    echo "本地缺 opt/ 或 local_vector_store/：模型和索引只在本地生产（服务器跑不动嵌入）" >&2
    exit 1
  }
  say "推模型与索引（约 4.5G，十几分钟）"
  tar czf - --exclude='__pycache__' opt local_vector_store \
    | ssh "$HOST" "tar xzf - -C $REMOTE"
  say "校验索引 sha256"
  local l r
  l=$(sha256sum local_vector_store/index.faiss | cut -d' ' -f1)
  r=$(ssh "$HOST" "sha256sum $REMOTE/local_vector_store/index.faiss | cut -d' ' -f1")
  [ "$l" = "$r" ] || { echo "  ✗ 索引 sha256 不一致（${l:0:16} vs ${r:0:16}）" >&2; exit 1; }
  echo "  ok（索引 sha256 一致 ${l:0:16}）"
  say "核对模型快照目录在位"
  ssh "$HOST" "ls -d $REMOTE/opt/models--BAAI--bge-m3/snapshots/*/ | head -1 && du -sh $REMOTE/opt"
}

# 开检索：装重依赖 + 抬内存闸 + 翻 .env 开关。**幂等**，可重复跑。
retrieval_on() {
  check_retrieval_capacity
  say "装检索链依赖（torch CPU 源，否则白背 2G nvidia 依赖）"
  ssh "$HOST" "
    set -e
    cd $REMOTE
    .venv/bin/python -m pip install -q --upgrade pip
    .venv/bin/python -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu
    .venv/bin/python -m pip install -q -r requirements.txt
    .venv/bin/python -c 'import torch, faiss, langchain_huggingface; print(\"  重依赖就位\")'
  "
  say "翻开关：WEB_API_RETRIEVAL=on（缺 DEEPSEEK_API_KEY 只会 Fake 直答降级，不崩）"
  ssh "$HOST" "
    set -e
    cd $REMOTE
    sed -i 's/^WEB_API_RETRIEVAL=.*/WEB_API_RETRIEVAL=on/' .env
    grep -q '^WEB_API_RETRIEVAL=' .env || echo 'WEB_API_RETRIEVAL=on' >> .env
    sed -i 's/^WEB_API_WARMUP=.*/WEB_API_WARMUP=1/' .env
    grep -q '^WEB_API_WARMUP=' .env || echo 'WEB_API_WARMUP=1' >> .env
    grep -E '^WEB_API_(RETRIEVAL|WARMUP)=' .env
  "
  say "抬 systemd 内存闸（600M→5G：检索栈常驻 3.2G）"
  ssh "$HOST" "
    set -e
    sudo mkdir -p /etc/systemd/system/wh40k-api.service.d
    printf '[Service]\nMemoryMax=5G\nMemoryHigh=4G\n' \
      | sudo tee /etc/systemd/system/wh40k-api.service.d/retrieval.conf >/dev/null
    sudo systemctl daemon-reload
  "
  restart_api
  verify_retrieval
}

# 关检索：退回轻量模式（资产留着，随时能再开）
retrieval_off() {
  say "关检索 → 轻量模式（不删 opt/ 与索引）"
  ssh "$HOST" "
    set -e
    cd $REMOTE
    sed -i 's/^WEB_API_RETRIEVAL=.*/WEB_API_RETRIEVAL=off/' .env
    sed -i 's/^WEB_API_WARMUP=.*/WEB_API_WARMUP=0/' .env
    sudo rm -f /etc/systemd/system/wh40k-api.service.d/retrieval.conf
    sudo systemctl daemon-reload
  "
  restart_api
  verify
}

# 检索专项验收：只看 200 不够——必须确认 retrieval=true、资产不缺、真能答出带引用的答案。
# 静默降级（开关开着但模型没挂上 → 检索悄悄关掉）就是靠这一步拦住的。
verify_retrieval() {
  say "检索验收"
  ssh "$HOST" "
    set -e
    echo '就绪状态：'
    curl -fsS '$BASE/api/healthz' | python3 -c '
import json,sys
d=json.load(sys.stdin)
miss=[a[\"name\"] for a in d[\"assets\"] if a[\"required\"] and not a[\"ok\"]]
print(\"  ready=%s retrieval=%s llm=%s 缺失必需资产=%s\" % (
    d[\"ready\"], d[\"retrieval\"], d[\"llm_configured\"], miss or \"无\"))
w=d.get(\"warmup\") or {}
print(\"  预热 requested=%s done=%s error=%s\" % (w.get(\"requested\"), w.get(\"done\"), w.get(\"error\")))
assert d[\"retrieval\"] is True, \"retrieval 仍是 false：开关没生效或资产没挂上（看 journalctl -u wh40k-api）\"
assert not miss, \"必需资产缺失：%s\" % miss
'
    echo '真问一句（零分数题，看能否检索到规则层并给引用）：'
    curl -fsS -X POST '$BASE/api/chat/sync' -H 'Content-Type: application/json' \
      -d '{\"question\":\"冲锋后还能射击吗\"}' \
      | python3 -c '
import json,sys
d=json.load(sys.stdin)
cites=d.get(\"cites\") or []
summ=(d.get(\"summary\") or {}).get(\"text\") or str(d)[:120]
print(\"  引用条数=%d\" % len(cites))
print(\"  摘要=%s\" % summ[:120])
assert cites, \"零引用：检索链没真正参与（LLM 直答）\"
'
    echo '内存占用（检索栈常驻实测 3.2G 上下）：'
    ps -o rss= -p \$(systemctl show -p MainPID --value wh40k-api) | awk '{printf \"  %.0f MB\n\", \$1/1024}'
  "
}

verify() {
  say "验收"
  ssh "$HOST" "
    p(){ printf '  %-22s %s\n' \"\$1\" \"\$(curl -s -o /dev/null -m 10 -w '%{http_code}' \"\$2\")\"; }
    echo '静态页：'
    p '/'          '$BASE/'
    p '/codex'     '$BASE/codex'
    p '/simulator' '$BASE/simulator'
    p '/roster'    '$BASE/roster'
    echo 'API：'
    p 'healthz'    '$BASE/api/healthz'
    p '图鉴阵营'   '$BASE/api/codex/factions'
    p '分队目录'   '$BASE/api/roster/detachments?faction=SM'
    echo '就绪状态：'
    curl -fsS '$BASE/api/healthz' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(\"  ready=%s retrieval=%s 缺失必需资产=%s\" % (d[\"ready\"], d[\"retrieval\"], [a[\"name\"] for a in d[\"assets\"] if a[\"required\"] and not a[\"ok\"]] or \"无\"))'
    echo '内存占用：'
    ps -o rss= -p \$(systemctl show -p MainPID --value wh40k-api) | awk '{printf \"  %.0f MB\n\", \$1/1024}'
    echo '同机其他服务未受影响：'
    for s in mygf; do printf '  %-12s %s\n' \"\$s\" \"\$(systemctl is-active \$s)\"; done
    for port in 8000 3000; do printf '  端口 %-8s %s\n' \"\$port\" \"\$(curl -s -o /dev/null -m 8 -w '%{http_code}' http://127.0.0.1:\$port/)\"; done
  "
}

case "$MODE" in
  code)   push_code; restart_api; verify ;;
  data)   push_data; restart_api; verify ;;
  web)    push_web; verify ;;
  verify) verify ;;
  all)    push_code; push_data; push_web; restart_api; verify ;;
  # 规则问答（换大机器后）
  capacity)      check_retrieval_capacity ;;
  assets)        push_assets ;;
  retrieval-on)  retrieval_on ;;
  retrieval-off) retrieval_off ;;
  verify-retrieval) verify_retrieval ;;
  *) echo "用法: bash deploy/deploy.sh [all|code|data|web|verify]" >&2
     echo "      规则问答: [capacity|assets|retrieval-on|retrieval-off|verify-retrieval]" >&2
     exit 2 ;;
esac

say "完成"
