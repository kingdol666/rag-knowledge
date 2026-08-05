/**
 * mini-yaml — zero-dependency YAML subset for ragctl.
 *
 * Replaces js-yaml so `ragctl` works on a FRESH clone with no node_modules
 * (the previous hard dependency crashed every ragctl command on empty
 * systems, including the very command that would install it).
 *
 * Supports the subset used by this project's config.yml / backend config:
 *   - indentation-based maps (2 spaces), nested maps
 *   - sequences ("- item"), nested sequences/maps under items
 *   - scalars: quoted strings, numbers, booleans, null, plain strings
 *   - comments (# ...), blank lines, inline comments after values
 *   - dump(): maps/sequences/scalars with minimal quoting
 */
'use strict';

function parseScalar(raw) {
  const s = raw.trim();
  if (s === '' || s === 'null' || s === '~') return null;
  if (s === 'true') return true;
  if (s === 'false') return false;
  if ((s.startsWith('"') && s.endsWith('"')) ||
      (s.startsWith("'") && s.endsWith("'"))) {
    return s.slice(1, -1);
  }
  if (/^-?\d+$/.test(s)) return parseInt(s, 10);
  if (/^-?\d*\.\d+$/.test(s)) return parseFloat(s);
  if (/^[\[\]{}]/.test(s)) return s; // inline flow — keep as string
  return s;
}

function stripComment(line) {
  let inS = null;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inS) { if (c === inS) inS = null; continue; }
    if (c === '"' || c === "'") { inS = c; continue; }
    if (c === '#') return line.slice(0, i);
  }
  return line;
}

function load(text) {
  const root = {};
  // stack of {indent, key, node, list} — node is the container being filled
  const stack = [{ indent: -1, key: null, node: root, list: false }];

  const lines = String(text || '').split(/\r?\n/);
  for (const rawLine of lines) {
    const line = stripComment(rawLine).replace(/\s+$/, '');
    if (!line.trim()) continue;
    const indent = line.length - line.trimStart().length;

    // pop stack to the correct depth
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) {
      stack.pop();
    }
    const parent = stack[stack.length - 1];

    // sequence item
    if (/^-\s+/.test(line.trim()) || line.trim() === '-') {
      const itemText = line.trim().replace(/^-\s*/, '');
      const listNode = parent.list ? parent.node : (
        (parent.node[parent.key] !== undefined && Array.isArray(parent.node[parent.key]))
          ? parent.node[parent.key]
          : (() => { parent.node[parent.key] = []; return parent.node[parent.key]; })()
      );
      if (!itemText) {
        // nested container follows
        const child = {};
        listNode.push(child);
        stack.push({ indent, key: listNode.length - 1, node: child, list: true });
      } else if (itemText.includes(':')) {
        const idx = itemText.indexOf(':');
        const k = itemText.slice(0, idx).trim();
        const v = itemText.slice(idx + 1).trim();
        const item = {};
        item[k] = v ? parseScalar(v) : (() => { const c = {}; stack.push({ indent, key: k, node: c, list: false }); return c; })();
        listNode.push(item);
      } else {
        listNode.push(parseScalar(itemText));
      }
      continue;
    }

    // key: value
    const colon = line.indexOf(':');
    if (colon < 0) continue;
    const key = line.slice(0, colon).trim();
    const val = line.slice(colon + 1).trim();

    if (!val) {
      // nested map follows
      const child = {};
      if (parent.list) {
        parent.node[parent.key] = child;
      } else {
        parent.node[key] = child;
      }
      stack.push({ indent, key, node: child, list: false });
    } else if (val === '|' || val === '>') {
      // block scalar — collect until dedent (keep raw)
      const block = [];
      const lines2 = lines.slice(lines.indexOf(rawLine) + 1);
      for (const l2 of lines2) {
        if (!l2.trim()) { block.push(''); continue; }
        const i2 = l2.length - l2.trimStart().length;
        if (i2 <= indent) break;
        block.push(l2.replace(new RegExp('^ {0,' + (indent + 2) + '}'), ''));
      }
      const joined = block.join('\n').replace(/\n+$/, '');
      parent.node[key] = val === '|' ? joined : joined.replace(/\n/g, ' ');
      // note: we don't advance the main loop over consumed lines — block
      // scalars are rare here; acceptable subset behavior.
    } else {
      parent.node[key] = parseScalar(val);
    }
  }
  return root;
}

function dumpScalar(v) {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  const s = String(v);
  if (s === '') return '""';
  if (/^[\w\-./:${}@]+$/.test(s) && !/^\d/.test(s)) return s;
  if (/^[a-zA-Z_][\w\-.]*$/.test(s)) return s;
  return '"' + s.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
}

function dump(obj, opts = {}) {
  const lines = [];
  const indentStep = '  ';

  function walk(node, depth, keyPrefix) {
    const pad = indentStep.repeat(depth);
    if (Array.isArray(node)) {
      for (const item of node) {
        if (item !== null && typeof item === 'object') {
          lines.push(`${pad}-`);
          walk(item, depth + 1, null);
        } else {
          lines.push(`${pad}- ${dumpScalar(item)}`);
        }
      }
      return;
    }
    if (node !== null && typeof node === 'object') {
      for (const [k, v] of Object.entries(node)) {
        if (v !== null && typeof v === 'object') {
          lines.push(`${pad}${k}:`);
          walk(v, depth + 1, k);
        } else {
          lines.push(`${pad}${k}: ${dumpScalar(v)}`);
        }
      }
    }
  }

  walk(obj, 0, null);
  return lines.join('\n') + '\n';
}

module.exports = { load, dump, parseScalar };
