import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import type { Answer } from "../src/lib/answer";

const question = "Export regression fixture";
const answer: Answer = {
  summary: "Saved fixture", degraded: false, trace: [], followups: [],
  verdict: { label: "Answer", labelEn: "Answer", lede: [
    { t: "text", s: "Export keeps 中文 and a source " }, { t: "cite", n: 1 },
  ] },
  calc: [{ n: 1, text: [{ t: "strong", s: "Historical" }, { t: "text", s: " scope is retained." }] }],
  cites: [{ n: 1, book: "Source fixture", page: 7, wiki: "core-rules/example.md", url: "https://example.com/rules" }],
};

test.beforeEach(async ({ page }) => {
  // Isolate delivery from model variation; the app restores a complete answer.
  await page.addInitScript(({ question, answer }) => {
    localStorage.setItem("wh40k-chat-transcript-v1", JSON.stringify({ version: 1, messages: [
      { id: "export-fixture", question, context: "", status: "complete", answer },
    ] }));
  }, { question, answer });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "下载 Markdown", exact: true })).toBeVisible();
});

test("Markdown download delivers readable citations and a lossless answer snapshot", async ({ page }) => {
  const received = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载 Markdown", exact: true }).click();
  const download = await received;
  expect(download.suggestedFilename()).toMatch(/^40k-answer-.*\.md$/);
  expect(await download.failure()).toBeNull();
  const path = await download.path();
  expect(path).not.toBeNull();
  const markdown = await readFile(path!, "utf8");
  expect(markdown).toContain("authority: ai-generated");
  expect(markdown).toContain("未经人工复核，不是官方规则");
  expect(markdown).toContain("Export keeps 中文 and a source [1]");
  expect(markdown).toContain("[1] Source fixture · p.7");
  expect(markdown).toContain("https://example.com/rules");
  const snapshot = markdown.match(/~~~json\n([\s\S]*?)\n~~~/);
  expect(snapshot).not.toBeNull();
  expect(JSON.parse(snapshot![1])).toEqual({ question, answer });
});

test("Copy writes the actual readable answer and citations to the browser clipboard", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: "http://localhost:3000" });
  await page.getByRole("button", { name: "复制回答", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "已复制" })).toBeVisible();
  const text = await page.evaluate(() => navigator.clipboard.readText());
  expect(text).toContain("Export keeps 中文 and a source [1]");
  expect(text).toContain("**Historical** scope is retained.");
  expect(text).toContain("[1] Source fixture · p.7");
  expect(text).not.toContain("完整回答快照");
});

test("A denied clipboard exposes selectable answer text instead of claiming success", async ({ page }) => {
  await page.evaluate(() => {
    Object.defineProperty(navigator.clipboard, "writeText", { value: async () => {
      throw new DOMException("Clipboard denied for test", "NotAllowedError");
    } });
  });
  await page.getByRole("button", { name: "复制回答", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "请在下方选中并复制" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Markdown 回答" })).toHaveValue(/Export keeps 中文 and a source \[1\]/);
});
