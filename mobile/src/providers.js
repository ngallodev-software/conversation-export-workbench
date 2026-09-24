export const CONVERSATION_SCHEMA = 'cew.conversation/v1';

function canonicalMessage(role, timestamp = '', parts = [], extra = {}) {
  return {
    role: ['user', 'assistant', 'system', 'tool'].includes(role) ? role : 'assistant',
    timestamp: String(timestamp || ''),
    parts,
    ...extra,
  };
}

function canonicalConversation(provider, id, title, startedAt, updatedAt, messages) {
  return {
    schema_version: CONVERSATION_SCHEMA,
    provider,
    id: String(id || ''),
    title: String(title || ''),
    started_at: String(startedAt || ''),
    updated_at: String(updatedAt || ''),
    messages,
  };
}

function epochToIso(value) {
  const number = Number(value);
  if (!number) return '';
  const date = new Date(number * 1000);
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().replace('.000Z', 'Z');
}

function walkChatGpt(mapping, currentNode) {
  const path = [];
  const visited = new Set();
  let nodeId = currentNode;
  const maxNodes = Object.keys(mapping || {}).length + 1;
  while (nodeId && !visited.has(nodeId) && visited.size < maxNodes) {
    visited.add(nodeId);
    const node = mapping?.[nodeId];
    if (!node) break;
    path.push(nodeId);
    nodeId = node.parent;
  }
  path.reverse();
  return path
    .map(id => mapping?.[id]?.message)
    .filter(message => {
      if (!message) return false;
      const role = message.author?.role || '';
      return role !== 'system' && message.weight !== 0;
    });
}

function normalizeChatGpt(conv) {
  const messages = [];
  for (const message of walkChatGpt(conv.mapping || {}, conv.current_node)) {
    const role = message.author?.role || '';
    if (!['user', 'assistant'].includes(role)) continue;
    const content = message.content || {};
    if (!['text', 'multimodal_text'].includes(content.content_type || '')) continue;
    const text = (Array.isArray(content.parts) ? content.parts : [])
      .filter(part => typeof part === 'string')
      .join('\n')
      .trim();
    if (!text) continue;
    messages.push(canonicalMessage(
      role,
      epochToIso(message.create_time),
      [{ type: 'text', content: text }],
      message.id ? { source_id: String(message.id) } : {},
    ));
  }
  return canonicalConversation(
    'chatgpt',
    conv.id,
    conv.title,
    epochToIso(conv.create_time),
    epochToIso(conv.update_time),
    messages,
  );
}

function claudeBlocks(message) {
  const blocks = Array.isArray(message.content) ? message.content : [];
  if (blocks.length) return blocks;
  return message.text ? [{ type: 'text', text: message.text }] : [];
}

function normalizeClaude(conv) {
  const messages = (Array.isArray(conv.chat_messages) ? conv.chat_messages : []).map(message => {
    const parts = [];
    for (const block of claudeBlocks(message)) {
      if (!block || typeof block !== 'object') continue;
      if (block.type === 'text') parts.push({ type: 'text', content: block.text || '' });
      else if (block.type === 'thinking') parts.push({ type: 'thinking', content: block.thinking || '' });
      else if (block.type === 'tool_use') {
        parts.push({
          type: 'tool_use',
          id: block.id || '',
          name: block.name || '',
          input: block.input || {},
        });
      } else if (block.type === 'tool_result') {
        parts.push({
          type: 'tool_result',
          tool_use_id: block.tool_use_id || '',
          content: block.content ?? '',
        });
      }
    }
    return canonicalMessage(
      message.sender === 'human' ? 'user' : 'assistant',
      message.created_at || '',
      parts,
      message.uuid ? { source_id: String(message.uuid) } : {},
    );
  });
  return canonicalConversation(
    'claude',
    conv.uuid,
    conv.name,
    conv.created_at,
    conv.updated_at,
    messages,
  );
}

function walkDeepSeek(mapping) {
  const messages = [];
  const visited = new Set();
  let nodeId = 'root';
  const maxNodes = Object.keys(mapping || {}).length + 1;
  while (nodeId && !visited.has(nodeId) && visited.size < maxNodes) {
    visited.add(nodeId);
    const node = mapping?.[nodeId];
    if (!node) break;
    if (node.message) messages.push(node.message);
    const children = Array.isArray(node.children) ? node.children : [];
    nodeId = children[0] || null;
  }
  return messages;
}

function normalizeDeepSeek(conv) {
  const messages = [];
  for (const message of walkDeepSeek(conv.mapping || {})) {
    const fragments = Array.isArray(message.fragments) ? message.fragments : [];
    if (!fragments.length) continue;
    const role = fragments[0]?.type === 'REQUEST' ? 'user' : 'assistant';
    const parts = [];
    for (const fragment of fragments) {
      if (!fragment || typeof fragment !== 'object') continue;
      if (fragment.type === 'REQUEST' || fragment.type === 'RESPONSE') {
        parts.push({ type: 'text', content: fragment.content || '' });
      } else if (fragment.type === 'THINK') {
        parts.push({ type: 'thinking', content: fragment.content || '' });
      } else if (fragment.type === 'SEARCH') {
        parts.push({ type: 'search', results: Array.isArray(fragment.results) ? fragment.results : [] });
      } else if (fragment.type === 'READ_LINK') {
        parts.push({ type: 'read_link', url: fragment.url || '' });
      }
    }
    const extra = message.model ? { model: String(message.model) } : {};
    messages.push(canonicalMessage(role, message.inserted_at || '', parts, extra));
  }
  return canonicalConversation(
    'deepseek',
    conv.id,
    conv.title,
    conv.inserted_at,
    conv.updated_at,
    messages,
  );
}

export function detectProvider(data) {
  if (!Array.isArray(data) || !data.length || typeof data[0] !== 'object' || data[0] === null) {
    return null;
  }
  const first = data[0];
  if ('mapping' in first && 'current_node' in first) return 'chatgpt';
  if ('chat_messages' in first && 'uuid' in first) return 'claude';
  if ('mapping' in first) return 'deepseek';
  return null;
}

export function normalizeProviderExport(data, forcedProvider = null) {
  if (!Array.isArray(data)) throw new Error('Provider export must be a JSON array');
  const provider = forcedProvider || detectProvider(data);
  const normalizer = {
    chatgpt: normalizeChatGpt,
    claude: normalizeClaude,
    deepseek: normalizeDeepSeek,
  }[provider];
  if (!normalizer) throw new Error('Could not detect ChatGPT, Claude, or DeepSeek export');
  return data.map(normalizer);
}

export function searchableText(record) {
  const chunks = [String(record.title || '')];
  for (const message of Array.isArray(record.messages) ? record.messages : []) {
    for (const part of Array.isArray(message.parts) ? message.parts : []) {
      if (part.type === 'text' || part.type === 'thinking') chunks.push(String(part.content || ''));
      else if (part.type === 'search') {
        for (const result of Array.isArray(part.results) ? part.results : []) {
          chunks.push(String(result.title || ''), String(result.snippet || ''), String(result.url || ''));
        }
      } else if (part.type === 'read_link') chunks.push(String(part.url || ''));
      else if (part.type === 'tool_use') chunks.push(String(part.name || ''), JSON.stringify(part.input || {}));
      else if (part.type === 'tool_result') chunks.push(JSON.stringify(part.content ?? ''));
      else if (part.type === 'attachment') chunks.push(String(part.name || ''));
    }
  }
  return chunks.filter(Boolean).join('\n');
}

export function buildSearchIndex(conversations) {
  return conversations.map(record => ({
    id: record.id,
    provider: record.provider,
    title: record.title,
    text: searchableText(record),
  }));
}
