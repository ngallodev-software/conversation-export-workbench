import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import {
  CONVERSATION_SCHEMA,
  buildSearchIndex,
  detectProvider,
  normalizeProviderExport,
} from '../src/providers.js';

async function fixture(name) {
  const url = new URL(`../../sample_data/${name}`, import.meta.url);
  return JSON.parse(await readFile(url, 'utf8'));
}

for (const [filename, expected] of [
  ['chatgpt-convo.json', 'chatgpt'],
  ['claude-convo.json', 'claude'],
  ['deepseek-convo.json', 'deepseek'],
]) {
  test(`normalizes ${expected} raw export on device`, async () => {
    const data = await fixture(filename);
    assert.equal(detectProvider(data), expected);
    const records = normalizeProviderExport(data);
    assert.ok(records.length > 0);
    assert.equal(records[0].schema_version, CONVERSATION_SCHEMA);
    assert.equal(records[0].provider, expected);
    assert.ok(Array.isArray(records[0].messages));
    const search = buildSearchIndex(records);
    assert.equal(search.length, records.length);
  });
}

test('chatgpt cycle guard terminates', () => {
  const data = [{
    id: 'c1',
    title: 'cycle',
    create_time: 1,
    update_time: 2,
    current_node: 'a',
    mapping: {
      a: { parent: 'b', message: null },
      b: { parent: 'a', message: null },
    },
  }];
  const records = normalizeProviderExport(data);
  assert.equal(records.length, 1);
  assert.deepEqual(records[0].messages, []);
});
