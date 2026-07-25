import { expect, test } from "@playwright/test";

/** 图鉴页冒烟：阵营→单位→兵牌装配，以及中英切换只换文案不换数值。 */

test("图鉴：选单位出兵牌，中英切换保留数值", async ({ page }) => {
  await page.goto("/codex");

  // 先选阵营再筛选：筛选只在当前阵营的单位里过（Broadside 属钛帝国，默认阵营是星际战士）
  const tau = page.getByRole("button", { name: /^钛帝国/ });
  await expect(tau).toBeVisible({ timeout: 30_000 });
  await tau.click();

  const search = page.getByPlaceholder("筛选单位（中/英名）");
  await expect(search).toBeVisible();
  await search.fill("Broadside");

  await page.getByRole("button", { name: /炮击战斗服小队|Broadside/ }).first().click();

  // 兵牌出来了：英文权威名（中文模式下作副标题）+ 武器表表头
  await expect(page.getByText("Broadside Battlesuits").first()).toBeVisible();
  await expect(page.getByText("武器", { exact: true }).first()).toBeVisible();
  // 中文模式下武器名是中文（不是英文原名）
  await expect(page.getByText("Heavy rail rifle")).toHaveCount(0);

  // 切到英文原文：武器名换成英文权威名，单位英文名仍在（只换文案不换数值）
  const toggle = page.getByRole("button", { name: "中 → EN" });
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.getByText("Heavy rail rifle").first()).toBeVisible();
  await expect(page.getByText("Broadside Battlesuits").first()).toBeVisible();
});
