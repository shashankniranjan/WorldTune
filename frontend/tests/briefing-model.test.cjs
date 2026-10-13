const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
const model = {};
const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/../src/components/briefing-model.ts`, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
new Function("exports", compiled)(model);

const record = (id, title, extra = {}) => ({ id, title, source: "publisher.example", publishedAt: "2026-09-19T00:00:00Z", sourceClass: "secondary", ...extra });

test("invalid titles fall back to a real original headline or an honest empty label", () => {
  assert.equal(model.sourceTitle(record("a", "4061672")), "Title unavailable");
  assert.equal(model.sourceTitle(record("a", "Reporting related to sanctions")), "Title unavailable");
  assert.equal(model.sourceTitle(record("a", "4061672", { originalHeadline: "Sanctions lifted" })), "Sanctions lifted");
});

test("source preview removes image markup and keeps meaningful linked prose", () => {
  assert.equal(model.readableText('[![European Commission logo](https://example.com/logo.svg "Logo")](https://example.com) **Sanctions** [details](https://example.com/details)'), "Sanctions details");
  assert.equal(model.readableText("<p>Energy & defense</p>"), "Energy & defense");
});

test("same syndication headline groups retain every record; distinct subjects remain separate", () => {
  const records = [record("a", "Sanctions approved - ABC11 Raleigh"), record("b", "Sanctions approved - ABC7 Chicago"), record("c", "Rates - India"), record("d", "Rates - US"), record("e", "4061672"), record("f", "4061672")];
  const groups = model.sourceGroups(records);
  assert.equal(groups.length, 5);
  assert.deepEqual(groups.flat().map((item) => item.id).sort(), records.map((item) => item.id).sort());
  assert.equal(groups.find((group) => group.some((item) => item.id === "a")).length, 2);
});

test("primary records lead without changing any corroboration label", () => {
  const olderPrimary = record("p", "Government action", { sourceClass: "primary", corroborationStatus: "single_source" });
  const newerSecondary = record("s", "Commentary", { publishedAt: "2026-10-06T00:00:00Z" });
  const groups = model.sourceGroups([newerSecondary, olderPrimary]);
  assert.equal(groups[0][0].id, "p");
  assert.equal(groups[0][0].corroborationStatus, "single_source");
});

test("IST dates cross midnight correctly and invalid dates are explicit", () => {
  assert.match(model.briefingDate("2026-10-06T20:00:00Z", true), /7 Oct 2026/);
  assert.match(model.briefingDate("2026-10-06T20:00:00Z", true), /IST$/);
  assert.equal(model.briefingDate("invalid"), "Date unavailable");
});

test("shared reporting does not assign an unrelated event date", () => {
  const data = { evidence: [record("a", "Report"), record("b", "Report two")], shift: { overview: { timeline: [{ title: "Event one", date: "2026-09-19", evidenceIds: ["a", "b"] }] } } };
  assert.equal(model.developmentContext(data, { evidenceIds: ["a"] }).event, undefined);
  assert.equal(model.developmentContext(data, { evidenceIds: ["b", "a"] }).event.title, "Event one");
});


test("publisher logos are excluded from explanatory image placement", () => {
  assert.equal(model.hasEditorialImage(record("a", "Report", { imageUrl: "https://example.com/Logo-BusinessWire-800x600.jpg" })), false);
  assert.equal(model.hasEditorialImage(record("b", "Report", { imageUrl: "https://example.com/news/datacenter.jpg" })), true);
  assert.equal(model.hasEditorialImage(record("c", "Report", { imageUrl: null })), false);
});

test("ambiguous events sharing identical source sets do not acquire a guessed date", () => {
  const data = { evidence: [], shift: { overview: { timeline: [
    { title: "Event one", date: "2026-09-19", evidenceIds: ["a"] },
    { title: "Event two", date: "2026-10-06", evidenceIds: ["a"] }
  ] } } };
  assert.equal(model.developmentContext(data, { evidenceIds: ["a"] }).event, undefined);
});

test("wholeSentences never cuts mid-sentence or adds an ellipsis", () => {
  const long = "SK Hynix is exploring a potential agreement with Intel to manufacture memory chips in the United States for the first time. Second sentence. Third sentence.";
  assert.equal(model.wholeSentences(long, 60), "SK Hynix is exploring a potential agreement with Intel to manufacture memory chips in the United States for the first time.");
  assert.equal(model.wholeSentences("One. Two. Three. Four.", 260, 3), "One. Two. Three.");
  assert.ok(!model.wholeSentences(long, 10).includes("…"));
  assert.equal(model.wholeSentences("", 50), "");
});
