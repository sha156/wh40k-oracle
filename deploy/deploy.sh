#!/usr/bin/env bash
# deploy/deploy.sh —— 把 wh40k-oracle 轻量站推到服务器（在**本地仓库根目录**执行）
#
#   bash deploy/deploy.sh          # 全量：代码 + 数据 + 前端
#   bash deploy/deploy.sh code     # 只推 .py（改后端逻辑）
#   bash deploy/deploy.sh web      # 只推前端静态产物
#   bash deploy/deploy.sh data     # 只推 db/ 与 wiki/（本地重建库之后）
#   bash deploy/deploy.sh verify   # 只跑验收，不推任何东西
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
  *) echo "用法: bash deploy/deploy.sh [all|code|data|web|verify]" >&2; exit 2 ;;
esac

say "完成"
