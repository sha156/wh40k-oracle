import assert from "node:assert/strict";
import test from "node:test";
import { latestRequest } from "../src/lib/latest-request.ts";
import { parseModelCount, visibleSimulation } from "../src/lib/sim.ts";
import { parseRoster, rosterValidationStatus } from "../src/lib/roster.ts";

test("unit/language selection fences an older card response and loading completion", async () => {
  const requests = latestRequest();
  const old = requests.start();
  let releaseOld;
  const oldResponse = new Promise((resolve) => { releaseOld = resolve; });
  let visible = "loading";
  const pendingOld = oldResponse.then(() => { if (old.isCurrent()) visible = "old unit"; });
  const next = requests.start();
  assert.equal(old.signal.aborted, true);
  if (next.isCurrent()) visible = "new unit / new language";
  releaseOld();
  await pendingOld;
  assert.equal(visible, "new unit / new language");
  requests.cancel();
  assert.equal(next.isCurrent(), false);
});

test("editing import text cancels its parse and cannot revive the old preview", async () => {
  const original = globalThis.fetch;
  const requests = latestRequest();
  const first = requests.start();
  let release;
  let receivedSignal;
  globalThis.fetch = async (_url, init) => {
    receivedSignal = init.signal;
    await new Promise((resolve) => { release = resolve; });
    return new Response(JSON.stringify({ complete: true, roster: { units: [{ canonicalId: "old" }] }, issues: [] }));
  };
  let preview = null;
  try {
    const pending = parseRoster("old text", "SM", null, "strike_force", first.signal)
      .then((result) => { if (first.isCurrent()) preview = result; });
    requests.cancel();
    release();
    await pending;
    assert.equal(receivedSignal.aborted, true);
    assert.equal(preview, null);
  } finally { globalThis.fetch = original; }
});

test("damage results cannot follow changed units, phase, models or options", () => {
  const response = { ok: true, report: { expectedDamage: 3 } };
  const saved = { inputKey: "submitted", assemblyKey: "units-and-phase", response };
  assert.equal(visibleSimulation(saved, "submitted", "units-and-phase"), response);
  for (const key of ["new units", "new phase", "new models", "cover enabled", "new loadout"]) {
    assert.equal(visibleSimulation(saved, key, "units-and-phase"), null);
  }
});

test("assembly prompts stay usable across weapon-count edits but not different units", () => {
  const response = { ok: false, reason: "loadout_required", weaponPool: ["Bolt rifle", "Grenade launcher"] };
  const saved = { inputKey: "empty weapons", assemblyKey: "unit A/shooting", response };
  assert.equal(visibleSimulation(saved, "one weapon selected", "unit A/shooting"), response);
  assert.equal(visibleSimulation(saved, "two weapons selected", "unit A/shooting"), response);
  assert.equal(visibleSimulation(saved, "different unit", "unit B/shooting"), null);
  assert.equal(visibleSimulation(saved, "different phase", "unit A/melee"), null);
  const invalid = { ...saved, response: { ok: false, reason: "invalid_options" } };
  assert.equal(visibleSimulation(invalid, "fixed inputs", "unit A/shooting"), null);
});

test("unmodeled roster constraints cannot receive a fully legal badge", () => {
  const report = { totalPoints: 150, limit: 2000, legal: true, issues: [] };
  assert.equal(rosterValidationStatus(report), "valid");
  const unresolved = { code: "compatibility", severity: "warn", surfacedOnly: true, message: "Not modeled", anchor: "" };
  assert.equal(rosterValidationStatus({ ...report, issues: [unresolved] }), "incomplete");
  assert.equal(rosterValidationStatus({ ...report, issues: [{ ...unresolved, surfacedOnly: false }] }), "valid");
  assert.equal(rosterValidationStatus({ ...report, legal: false, issues: [unresolved] }), "invalid");
  assert.equal(rosterValidationStatus({ ...report, issues: [{ ...unresolved, severity: "error" }] }), "invalid");
});

test("model counts preserve scientific notation and reject fractions or out-of-range values", () => {
  assert.equal(parseModelCount(""), undefined);
  assert.equal(parseModelCount(" "), undefined);
  assert.equal(parseModelCount("1"), 1);
  assert.equal(parseModelCount("1e2"), 100);
  assert.equal(parseModelCount("10.0"), 10);
  for (const input of ["1.5", "0", "-1", "101", "1e3", "Infinity", "not a number"]) {
    assert.equal(parseModelCount(input), null, input);
  }
});
