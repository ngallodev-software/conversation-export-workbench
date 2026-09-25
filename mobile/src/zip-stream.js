import { Unzip, UnzipInflate } from 'fflate';

function joinChunks(chunks, total) {
  const output = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return output;
}

export async function readSelectedZip(file, {
  accept,
  maxEntries = 64,
  maxMemberBytes,
  maxTotalBytes,
  maxCompressionRatio = 200,
} = {}) {
  if (!file || typeof file.stream !== 'function') {
    throw new Error('Streaming ZIP import requires a browser File object');
  }
  if (typeof accept !== 'function') throw new Error('ZIP selector is required');

  return await new Promise(async (resolve, reject) => {
    const selected = {};
    const seen = new Set();
    let selectedCount = 0;
    let totalOutput = 0;
    let pending = 0;
    let inputDone = false;
    let settled = false;

    const fail = error => {
      if (settled) return;
      settled = true;
      reject(error instanceof Error ? error : new Error(String(error)));
    };

    const maybeResolve = () => {
      if (!settled && inputDone && pending === 0) {
        settled = true;
        resolve(selected);
      }
    };

    const unzip = new Unzip(entry => {
      if (settled || !accept(entry.name)) return;
      if (seen.has(entry.name)) {
        fail(new Error('ZIP contains duplicate selected member: ' + entry.name));
        return;
      }
      seen.add(entry.name);
      selectedCount += 1;
      if (selectedCount > maxEntries) {
        fail(new Error('ZIP contains too many selected members'));
        return;
      }
      if (entry.originalSize != null && entry.originalSize > maxMemberBytes) {
        fail(new Error(entry.name + ': member too large'));
        return;
      }
      if (
        entry.originalSize != null &&
        entry.size != null &&
        entry.size > 0 &&
        entry.originalSize / entry.size > maxCompressionRatio
      ) {
        fail(new Error(entry.name + ': suspicious compression ratio'));
        return;
      }

      const chunks = [];
      let memberBytes = 0;
      pending += 1;
      entry.ondata = (error, chunk, final) => {
        if (settled) return;
        if (error) {
          fail(error);
          return;
        }
        if (chunk?.byteLength) {
          memberBytes += chunk.byteLength;
          totalOutput += chunk.byteLength;
          if (memberBytes > maxMemberBytes) {
            fail(new Error(entry.name + ': expanded member exceeds limit'));
            return;
          }
          if (totalOutput > maxTotalBytes) {
            fail(new Error('ZIP selected payloads exceed import limit'));
            return;
          }
          chunks.push(chunk);
        }
        if (final) {
          selected[entry.name] = joinChunks(chunks, memberBytes);
          pending -= 1;
          maybeResolve();
        }
      };
      try {
        entry.start();
      } catch (error) {
        fail(error);
      }
    });
    unzip.register(UnzipInflate);

    try {
      const reader = file.stream().getReader();
      while (true) {
        const { value, done } = await reader.read();
        if (settled) {
          try { await reader.cancel(); } catch {}
          return;
        }
        if (done) {
          inputDone = true;
          unzip.push(new Uint8Array(0), true);
          maybeResolve();
          return;
        }
        unzip.push(value, false);
      }
    } catch (error) {
      fail(error);
    }
  });
}
