const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const model = {};
new Function('exports', ts.transpileModule(fs.readFileSync(`${__dirname}/../src/components/connection-model.ts`, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText)(model);
const node = (id, label) => ({id, label, type: 'entity', evidenceIds: []});
const edge = (id, relationship, extra = {}) => ({id, source: 'a', target: 'b', relationship, confidence: 'low', evidenceIds: ['e1'], ...extra});
const data = edges => ({nodes: [node('a','Power supplier'),node('b','Compute company')], edges, crossShiftLinks: [], personalPaths: []});
test('unresolved endpoints are omitted rather than invented', () => {
  assert.deepEqual(model.connectionEdges(data([edge('missing','SUPPLIES',{target:'unknown'})])), []);
});
test('association and unknown mechanisms do not become causal arrows', () => {
  for (const verb of ['ASSOCIATED_WITH','COMPETES_WITH','connected_through_mechanism','unknown']) assert.equal(model.connectionEdges(data([edge('e',verb)]))[0].directed, false);
  assert.equal(model.connectionEdges(data([edge('e','SUPPLIES')]))[0].directed, true);
});
test('search matches endpoints and explanation without losing provenance', () => {
  const source = data([edge('e','SUPPLIES',{explanation:'Secures electricity'})]);
  for (const query of [' COMPUTE ', 'electricity', 'supplier']) {
    const result = model.connectionEdges(source,query);
    assert.equal(result.length,1);
    assert.deepEqual(result[0].evidenceIds,['e1']);
    assert.equal(result[0].confidence,'low');
  }
  assert.equal(model.connectionEdges(source,'absent').length,0);
});
test('entity view excludes cross-shift duplicates and preserves the snapshot', () => {
  const source = data([edge('cross','associated_with',{category:'cross_shift'}),edge('entity','OPERATES')]);
  const before = JSON.stringify(source);
  assert.deepEqual(model.connectionEdges(source).map(value => value.id),['entity']);
  assert.equal(JSON.stringify(source),before);
});
