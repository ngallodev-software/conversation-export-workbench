import test from 'node:test';
import assert from 'node:assert/strict';
import { strToU8, zipSync } from 'fflate';
import { readSelectedZip } from '../src/zip-stream.js';

test('streaming ZIP reader selects bounded members', async () => {
  const bytes = zipSync({
    'nested/conversations.json': strToU8('[{"title":"hello"}]'),
    'ignored.txt': strToU8('ignore me'),
  });
  const file = new File([bytes], 'export.zip');
  const files = await readSelectedZip(file, {
    accept: name => name.endsWith('conversations.json'),
    maxEntries: 4,
    maxMemberBytes: 1024,
    maxTotalBytes: 2048,
    maxCompressionRatio: 200,
  });
  assert.deepEqual(Object.keys(files), ['nested/conversations.json']);
  assert.equal(new TextDecoder().decode(files['nested/conversations.json']), '[{"title":"hello"}]');
});

test('streaming ZIP reader rejects expanded members beyond the limit', async () => {
  const bytes = zipSync({ 'conversations.json': strToU8('x'.repeat(4096)) });
  const file = new File([bytes], 'large.zip');
  await assert.rejects(
    () => readSelectedZip(file, {
      accept: () => true,
      maxEntries: 2,
      maxMemberBytes: 100,
      maxTotalBytes: 100,
      maxCompressionRatio: 1000,
    }),
    /too large|exceeds limit/
  );
});
