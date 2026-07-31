import { expect, test } from "@playwright/test";

import { pickSimUnit, runSim } from "./helpers";

/**
 * 模拟器**错误路径**冒烟（第 3 轮审查 H1/H2/H3）。
 *
 * 既有 4 条 e2e 全是 happy path，本轮两条 HIGH 正好落在它们的盲区里：
 * - H2：数值入参超上限后被边界静默丢弃，页面照常端出一份 ok=true 的报告，
 *   与压根不填时逐位相同——每一层都是成功路径，肉眼看不出问题。
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

test("H2+H3：模型数填超上限时，页面必须说出「这个入参没生效」", async ({ page }) => {
  await pickSimUnit(page, "攻方", TAU, "猎犬", KROOT);
  await pickSimUnit(page, "守方", SM, "阿加通", TARGET);
  await page.getByRole("button", { name: "近战" }).click();

  // 先拿一份合法结果当对照：不许有任何丢弃告警
  await runSim(page);
  await expect(page.getByText("期望伤害 / 轮")).toBeVisible();
  await expect(page.getByText(/未生效/)).toHaveCount(0);

  // 攻方模型数框没有 max，用户可以填 200；后端上限是 100 → 整个入参被丢弃
  await page.getByLabel("攻方模型数").fill("200");
  await runSim(page);

  // 报告照常出（丢弃不改变成败），但必须同时把「你填的 200 没生效」摆在页面上
  await expect(page.getByText("期望伤害 / 轮")).toBeVisible();
  await expect(page.getByText(/attacker_models=200 未生效/).first()).toBeVisible();
});
