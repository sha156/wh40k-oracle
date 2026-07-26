import { defineConfig } from "@playwright/test";

/**
 * 浏览器冒烟（本地门禁，不进 CI —— CI 没有 db/wh40k.sqlite 与模型卷）。
 *
 * 为什么要有这层：全库 1900+ 测试全是 Python，纯浏览器行为的缺陷（面板列出用不了的
 * 武器、输入框看不出能填、切页签状态没清）一条都逮不到 —— 2026-07-25 用户实测
 * 「选不了武器」就是这么漏出去的。
 *
 * 用系统 Chrome（channel）而不是 Playwright 自带 Chromium：省 130MB 下载，且跑的是
 * 用户真正在用的浏览器。首次准备只需 `npm i -D @playwright/test`，无需 `playwright install`。
 *
 * webServer 两个进程都带 reuseExistingServer：本地已经开着 dev/uvicorn 时直接复用。
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,           // 蒙特卡洛解算 + 冷启动装载 sqlite，给足
  expect: { timeout: 20_000 },
  fullyParallel: false,      // 同一后端进程，串行跑避免解算并发闸（web_api 有信号量）
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    // 必须用 localhost 而不是 127.0.0.1：应用默认 API base 是 http://localhost:8000，
    // 从 127.0.0.1:3000 这个 origin 发往 localhost:8000 的跨端口请求会被 Chrome 直接
    // 掐掉（实测：网络面板里连请求都不发、无 console 报错），页面因此空列表。
    baseURL: "http://localhost:3000",
    channel: "chrome",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      // 后端：零 LLM 的三个页签只需 sqlite，不加载 bge-m3
      // 路径相对 cwd（cwd 本身相对本配置文件所在的 web/），所以这里不带 ../
      command: ".venv\\Scripts\\python.exe -m uvicorn web_api.main:app --port 8000",
      cwd: "..",
      url: "http://localhost:8000/healthz",
      reuseExistingServer: true,
      timeout: 120_000,
      env: { WEB_API_RETRIEVAL: "off" },
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000/simulator",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
