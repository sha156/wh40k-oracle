import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Stage 5 部署：standalone 产物让运行镜像只带 server.js + 追踪到的最小
  // node_modules，不必整包塞进最终层（public/ 与 .next/static 需手动拷，
  // 见 web/Dockerfile）。本地 `npm run dev` 不受影响。
  output: "standalone",
};

export default nextConfig;
