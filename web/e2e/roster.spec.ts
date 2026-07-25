import { expect, test } from "@playwright/test";

/**
 * 军表实验室冒烟：加单位 → 实时算点数与合法性 → 装配面板（与模拟器共用 LoadoutPanel，
 * 今天那处可用性修复在这里也生效）。点评是蒙特卡洛，另起一条并给足超时。
 */

test("军表：加单位实时出点数与合法性，装配面板可填件数", async ({ page }) => {
  await page.goto("/roster");

  // 阵营决定可搜的单位池（Broadside 属钛帝国，默认是星际战士）
  const faction = page.getByLabel("阵营");
  await expect(faction.locator("option").first()).toBeAttached({ timeout: 30_000 });
  await faction.selectOption("TAU");

  const search = page.getByPlaceholder("搜索单位加入军表…");
  await expect(search).toBeVisible();
  await search.fill("Broadside");
  await page.getByRole("button", { name: /炮击战斗服小队|Broadside/ }).first().click();

  // 实时校验面板：总点数与合法性判定都该出来（零 LLM）
  await expect(page.getByText("总点数")).toBeVisible();
  await expect(page.getByText(/合法|不合法/).first()).toBeVisible();

  // 展开装配（点评用）——武器池懒加载
  await page.getByRole("button", { name: /^装配/ }).first().click();
  const qty = page.getByLabel("Heavy rail rifle 件数");
  await expect(qty).toBeVisible();
  await page.getByLabel("Heavy rail rifle 全员装配").click();
  await expect(qty).not.toHaveValue("");
  await expect(qty).not.toHaveValue("0");
});

test("军表：装配后能跑强度点评", async ({ page }) => {
  test.slow(); // 4 个典型目标 × 阶段的蒙特卡洛，比其它冒烟慢

  await page.goto("/roster");
  const faction = page.getByLabel("阵营");
  await expect(faction.locator("option").first()).toBeAttached({ timeout: 30_000 });
  await faction.selectOption("TAU");
  await page.getByPlaceholder("搜索单位加入军表…").fill("Broadside");
  await page.getByRole("button", { name: /炮击战斗服小队|Broadside/ }).first().click();
  await page.getByRole("button", { name: /^装配/ }).first().click();
  await page.getByLabel("Heavy rail rifle 全员装配").click();

  await page.getByRole("button", { name: "强度点评" }).click();
  await expect(page.getByText("逐单位蒙特卡洛解算中…")).toHaveCount(0, {
    timeout: 120_000,
  });
  await expect(page.getByText("强度点评 · 每 100 点期望伤害")).toBeVisible();
  // 光有表头不算产出（P6 教训：装配成功 ≠ 有输出）——该单位那行必须有真实数字，
  // 全是 "—" 说明装配没生效或该阶段 0 攻击
  const row = page.getByRole("row", { name: /Broadside Battlesuits/ });
  await expect(row).toContainText(/\d+\.\d/, { timeout: 120_000 });
});
