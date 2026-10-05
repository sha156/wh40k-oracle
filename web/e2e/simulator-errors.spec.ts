import { expect, test } from "@playwright/test";

import { pickSimUnit, runSim } from "./helpers";

/**
 * 模拟器**错误路径**冒烟（第 3 轮审查 H1/H2/H3）。
 *
 * 既有 4 条 e2e 全是 happy path，本轮两条 HIGH 正好落在它们的盲区里：
 * - H2：数值入参超上限时必须在浏览器边界拒绝，且旧报告立即失效。
 * - H3：后端 note 明文写「见 errors」，而 SimResponse.errors 在整个前端
 *   只出现在 sim.ts 的类型声明里，一次都没进过 JSX。
 * - H1：单位列表的「N 分起」徽章在全库 1715 个单位上恒为空（点数解析读错形状）。
 *
 * 三条都只有真跑浏览器才看得见，故钉在这里。
 */

const TAU = "TAU";
const SM = "SM";
// 克鲁特猎犬队：近战池只有 Ripping fangs 一把 → 自动装配，不必先过装配面板
const KROOT = "克鲁特猎犬队";
const TARGET = "阿加通连长";

test.beforeEach(async ({ page }) => {
  await page.goto("/simulator");
  await expect(page.getByRole("button", { name: "开始模拟" })).toBeVisible();
});

test("H1：单位列表要真的显示「N 分起」点数徽章", async ({ page }) => {
  const panel = page
    .locator("section")
    .filter({ has: page.getByText("攻方", { exact: true }) });
  await expect(panel.locator("select option").first()).toBeAttached({
    timeout: 30_000,
  });
  await panel.locator("select").selectOption(TAU);
  // 徽章曾经在全库范围内恒为空（渲染分支 `{u.pts ? … : null}` 从未走到）
  await expect(panel.getByText(/^\d+ 分起$/).first()).toBeVisible({
    timeout: 30_000,
  });
});

test("H2：模型数超上限时拒绝提交、清除旧结果，修正后可恢复", async ({ page }) => {
  await pickSimUnit(page, "攻方", TAU, "猎犬", KROOT);
  await pickSimUnit(page, "守方", SM, "阿加通", TARGET);
  await page.getByRole("button", { name: "近战" }).click();

  // 先拿一份合法结果当对照：不许有任何丢弃告警
  await runSim(page);
  await expect(page.getByText("期望伤害 / 轮")).toBeVisible();
  await expect(page.getByText(/未生效/)).toHaveCount(0);

  const models = page.getByLabel("攻方模型数");
  await models.fill("200");
  await expect(models).toHaveAttribute("aria-invalid", "true");
  // Input identity changed, so the previous report must disappear before another submit.
  await expect(page.getByText("期望伤害 / 轮")).toHaveCount(0);
  await runSim(page);

  await expect(page.getByText("模型数须为 1–100 的整数；留空使用默认值。")).toBeVisible();
  await expect(page.getByText("期望伤害 / 轮")).toHaveCount(0);

  // Correcting the value clears the invalid state and permits a fresh report.
  await models.fill("10");
  await expect(models).toHaveAttribute("aria-invalid", "false");
  await runSim(page);
  await expect(page.getByText("期望伤害 / 轮")).toBeVisible();
});

test("H3：后端逐条 errors 仍会显示在页面上", async ({ page }) => {
  await pickSimUnit(page, "攻方", TAU, "猎犬", KROOT);
  await pickSimUnit(page, "守方", SM, "阿加通", TARGET);
  await page.getByRole("button", { name: "近战" }).click();
  await page.route("**/simulate", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: false,
        reason: "error",
        note: "模拟输入未生效，见 errors",
        errors: ["fixture_option=200 未生效"],
      }),
    });
  });

  await runSim(page);
  await expect(page.getByText("fixture_option=200 未生效")).toBeVisible();
});
