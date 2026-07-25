import { expect, type Page } from "@playwright/test";

/** 模拟器页：在攻/守面板里选定单位（阵营下拉用 faction id，筛选框缩小列表后点条目） */
export async function pickSimUnit(
  page: Page,
  side: "攻方" | "守方",
  factionId: string,
  query: string,
  unitLabel: string,
) {
  // 面板首行的 span 文案恰为「攻方」/「守方」（exact 避免误中「攻方模型数」）
  const panel = page
    .locator("section")
    .filter({ has: page.getByText(side, { exact: true }) });
  // 阵营下拉是异步填的（/codex/factions）——先等到真有选项，否则 selectOption 的
  // 报错是「did not find some options」，掩盖了"后端没连上/数据没到"这个真因
  await expect(panel.locator("select option").first()).toBeAttached({ timeout: 30_000 });
  await panel.locator("select").selectOption(factionId);
  await panel.getByPlaceholder("筛选").fill(query);
  await panel.getByRole("button", { name: unitLabel }).first().click();
  // 面板抬头右侧回显已选单位名——确认选中生效再往下走
  await expect(panel.getByText(unitLabel).first()).toBeVisible();
}

/** 点「开始模拟」并等到解算结束（按钮文案从「解算中…」回到「开始模拟」） */
export async function runSim(page: Page) {
  const btn = page.getByRole("button", { name: "开始模拟" });
  await btn.click();
  await expect(page.getByRole("button", { name: "解算中…" })).toHaveCount(0, {
    timeout: 60_000,
  });
}
