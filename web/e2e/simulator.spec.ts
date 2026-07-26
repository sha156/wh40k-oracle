import { expect, test } from "@playwright/test";

import { pickSimUnit, runSim } from "./helpers";

/**
 * 模拟器装配链路冒烟。
 *
 * 这两条正是 2026-07-25 用户实测「选不了武器」暴露的缺陷（fix 0eb09a6c）：
 * 纯浏览器行为，Python 侧 1900+ 测试一条都逮不到，所以钉在这里当回归门。
 */

const TAU = "TAU";
const SM = "SM";
const KROOT = "克鲁特猎犬队";      // 全池只有近战 Ripping fangs
const BROADSIDE = "炮击战斗服小队"; // 射击 5 把 + 近战 1 把
const TARGET = "阿加通连长";

test.beforeEach(async ({ page }) => {
  await page.goto("/simulator");
  await expect(page.getByRole("button", { name: "开始模拟" })).toBeVisible();
});

test("无远程武器的单位在射击阶段：指路换阶段，一键切过去即可出报告", async ({ page }) => {
  await pickSimUnit(page, "攻方", TAU, "猎犬", KROOT);
  await pickSimUnit(page, "守方", SM, "阿加通", TARGET);
  await runSim(page);

  // 不该发一个填不满的装配面板，而该说清楚"这个阶段没有能开火的武器"
  await expect(page.getByText(/射击阶段没有可开火武器/)).toBeVisible();
  await expect(page.getByText("需先装配攻方武器")).toHaveCount(0);

  const fixBtn = page.getByRole("button", { name: "切到近战阶段" });
  await expect(fixBtn).toBeVisible();
  await fixBtn.click();
  await runSim(page);

  // 该阶段唯一武器 → 自动装配，并把件数假设披露出来
  await expect(page.getByText(/自动装配/)).toBeVisible();
  await expect(page.getByText("期望伤害 / 轮")).toBeVisible();
  await expect(page.getByText("攻击次数")).toBeVisible();
});

test("多武器单位：装配面板按阶段过滤、可填件数、「全员」一键满编后出报告", async ({ page }) => {
  await pickSimUnit(page, "攻方", TAU, "Broadside", BROADSIDE);
  await pickSimUnit(page, "守方", SM, "阿加通", TARGET);
  await runSim(page);

  await expect(page.getByText("需先装配攻方武器")).toBeVisible();
  // 射击阶段的池里不该混进近战武器（混了就是诱导用户选出全 0 报告）
  await expect(page.getByLabel("Heavy rail rifle 件数")).toBeVisible();
  await expect(page.getByLabel("Crushing bulk 件数")).toHaveCount(0);

  // 件数输入框必须真能改（旧版渲染成 "0 ×武器名"，看着像静态文字）
  const qty = page.getByLabel("Heavy rail rifle 件数");
  await qty.fill("2");
  await expect(qty).toHaveValue("2");

  // 「全员」= 每个模型各 1 件（宽肩最小档 1 模型 → 1 件）
  await page.getByLabel("Heavy rail rifle 全员装配").click();
  await expect(qty).toHaveValue("1");

  await runSim(page);
  await expect(page.getByText("期望伤害 / 轮")).toBeVisible();
  await expect(page.getByText("需先装配攻方武器")).toHaveCount(0);
});

test("切阶段清空已填装配（跨阶段沿用会被引擎滤成空手 0 伤）", async ({ page }) => {
  await pickSimUnit(page, "攻方", TAU, "Broadside", BROADSIDE);
  await pickSimUnit(page, "守方", SM, "阿加通", TARGET);
  await runSim(page);

  await page.getByLabel("Heavy rail rifle 全员装配").click();
  await expect(page.getByLabel("Heavy rail rifle 件数")).toHaveValue("1");

  // 切到近战：装配面板与结果一起作废（近战池只有 Crushing bulk，自动装配后直接出报告）
  await page.getByRole("button", { name: "近战" }).click();
  await expect(page.getByText("需先装配攻方武器")).toHaveCount(0);
  await runSim(page);
  await expect(page.getByText(/自动装配.*Crushing bulk|Crushing bulk.*自动装配/)).toBeVisible();
});
