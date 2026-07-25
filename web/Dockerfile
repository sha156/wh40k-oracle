# web/Dockerfile —— Next.js 前端镜像（BUILD-PLAN Stage 5）
#
# 三段构建 → 运行镜像只带 standalone 产物（next.config.ts 里 output: "standalone"）。
#
# ⚠ NEXT_PUBLIC_API_BASE 是**构建期**变量：Next 会把它内联进浏览器包，运行期再改
# 环境变量不会生效。而这个 URL 是**浏览器**去访问的，所以填宿主机能通的地址
# （http://localhost:8000），不是 compose 网络内的服务名（http://api:8000）。

FROM node:22-alpine AS deps
# 构建期代理（npm 认标准 HTTP_PROXY/HTTPS_PROXY 环境变量），只在构建期生效
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY="localhost,127.0.0.1"
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY="localhost,127.0.0.1"
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup -S nodejs && adduser -S nextjs -G nodejs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
