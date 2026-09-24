import { performance } from 'node:perf_hooks';
import { buildSearchIndex } from '../src/providers.js';

const count = Number(process.argv[2] || 10000);
const conversations = [];
for (let index = 0; index < count; index += 1) {
  conversations.push({
    schema_version: 'cew.conversation/v1',
    provider: index % 3 === 0 ? 'chatgpt' : (index % 3 === 1 ? 'claude' : 'deepseek'),
    id: String(index),
    title: 'Synthetic conversation ' + index,
    started_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:01Z',
    messages: [
      {
        role: 'user',
        timestamp: '2026-01-01T00:00:00Z',
        parts: [{ type: 'text', content: 'question '.repeat(20) + index }],
      },
      {
        role: 'assistant',
        timestamp: '2026-01-01T00:00:01Z',
        parts: [{ type: 'text', content: 'answer '.repeat(80) + index }],
      },
    ],
  });
}

const before = process.memoryUsage().heapUsed;
const started = performance.now();
const index = buildSearchIndex(conversations);
const elapsed = performance.now() - started;
const after = process.memoryUsage().heapUsed;

console.log(JSON.stringify({
  conversations: count,
  search_records: index.length,
  elapsed_ms: Math.round(elapsed),
  heap_delta_mb: Math.round(((after - before) / 1024 / 1024) * 10) / 10,
}, null, 2));
