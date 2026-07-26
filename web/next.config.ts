import type { NextConfig } from "next";

// 两种部署形态，构建期用 NEXT_OUTPUT 选：
//   standalone（默认）→ 容器化，运行镜像只带 server.js + 追踪到的最小 node_modules
//   export            → 纯静态产物 out/，交给已有的 nginx/openresty 托管，**服务器上
//                       不用起 node 进程**（3.3G 内存的小机器上这一条很值）
// 静态导出成立的前提：四个页签全是 "use client"、无 route handler / middleware /
// next-image / generateStaticParams——加这些东西之前先想想这条路还通不通。
const output = process.env.NEXT_OUTPUT === "export" ? "export" : "standalone";

const nextConfig: NextConfig = {
  output,
};

export default nextConfig;
