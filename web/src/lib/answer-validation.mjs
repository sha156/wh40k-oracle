/** Shared runtime validation for SSE events and saved transcripts. */
const record = (value) => typeof value === "object" && value !== null && !Array.isArray(value);
const string = (value) => typeof value === "string";
const strings = (value) => Array.isArray(value) && value.every(string);
const integer = (value) => typeof value === "number" && Number.isSafeInteger(value);
const optionalString = (value) => value === undefined || string(value);

function rich(value) {
  return Array.isArray(value) && value.every((span) => record(span) && (
    span.t === "cite" ? integer(span.n) && span.n > 0
      : ["text", "num", "kw", "strong", "em"].includes(String(span.t)) && string(span.s)
  ));
}

function keyword(value) {
  return record(value) && string(value.text) && ["slug", "base", "nameZh", "brief", "section", "ruleSlug", "group"].every((key) => optionalString(value[key]));
}

function entityCard(value) {
  if (!record(value)) return false;
  if (!["nameZh", "nameEn", "pts", "keywords", "faction", "src", "wiki"].every((key) => string(value[key]))) return false;
  if (!["role", "invuln", "loadout", "leads", "factionKeywords", "legend"].every((key) => optionalString(value[key]))) return false;
  if (!Array.isArray(value.stats) || !value.stats.every((stat) => record(stat) && string(stat.lab) && string(stat.val))) return false;
  for (const name of ["ranged", "melee"]) {
    const rows = value[name];
    if (!Array.isArray(rows) || !rows.every((row) => record(row)
      && ["name", "range", "a", "skill", "s", "ap", "d"].every((key) => string(row[key]))
      && (row.kw === undefined || Array.isArray(row.kw) && row.kw.every(keyword))
      && (row.hot === undefined || typeof row.hot === "boolean"))) return false;
  }
  if (!Array.isArray(value.abilities) || !value.abilities.every((ability) => record(ability) && string(ability.name)
    && optionalString(ability.tag) && optionalString(ability.text)
    && (ability.rich === undefined || Array.isArray(ability.rich) && ability.rich.every((span) => record(span)
      && (span.t === "text" && string(span.s) || span.t === "kw" && keyword(span.kw)))))) return false;
  return Array.isArray(value.composition) && value.composition.every(rich)
    && (value.damaged === undefined || record(value.damaged) && string(value.damaged.w) && string(value.damaged.text));
}

export function validAnswer(value) {
  if (!record(value) || !string(value.summary) || typeof value.degraded !== "boolean") return false;
  if (!record(value.verdict) || !string(value.verdict.label) || !string(value.verdict.labelEn) || !rich(value.verdict.lede)) return false;
  if (!Array.isArray(value.calc) || !value.calc.every((step) => record(step) && integer(step.n) && rich(step.text))) return false;
  if (!Array.isArray(value.trace) || !value.trace.every((step) => record(step) && string(step.fn) && string(step.args)
    && ["ok", "degraded"].includes(String(step.status)) && optionalString(step.result) && optionalString(step.note))) return false;
  if (!Array.isArray(value.cites) || !value.cites.every((cite) => record(cite) && integer(cite.n) && string(cite.book) && string(cite.wiki)
    && (cite.page === undefined || integer(cite.page)) && optionalString(cite.section) && optionalString(cite.term)
    && (cite.url === null || optionalString(cite.url)))) return false;
  if (!strings(value.followups) || !optionalString(value.traceWarn)) return false;
  if (value.sensitivity !== undefined && (!record(value.sensitivity) || !string(value.sensitivity.title) || !rich(value.sensitivity.text))) return false;
  if (value.cta !== undefined && (!record(value.cta) || !["simulator", "roster", "wiki"].includes(String(value.cta.kind))
    || typeof value.cta.ready !== "boolean" || !string(value.cta.label) || !optionalString(value.cta.mini))) return false;
  return value.entityCard === undefined || entityCard(value.entityCard);
}
