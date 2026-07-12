import type { Metadata } from "next";
// 自托管字体（上线红线：不可用 GW 字体资产；Bahnschrift 仅作本机回退）
import "@fontsource/barlow-condensed/400.css";
import "@fontsource/barlow-condensed/500.css";
import "@fontsource/barlow-condensed/600.css";
import "@fontsource/barlow-condensed/700.css";
// 中文不自托管：Noto Sans SC 全量子集 ~1MB 曾把 Lighthouse 移动端压到 44 分且 CLS 0.216。
// 系统字体栈已覆盖全平台（Android 原生即 Noto Sans SC、Windows 雅黑、Apple 苹方），见 globals.css --font-body
import "./globals.css";

export const metadata: Metadata = {
  title: "40K 规则专家 · Warhammer 40K Rules Copilot",
  description:
    "基于本地规则库的战锤40K规则问答：引用页码可溯源，模拟为期望值/蒙特卡洛估算。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
