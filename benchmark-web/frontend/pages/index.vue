<template>
  <div>
    <header>
      <h1>QDCVR Knowledge Platform — Benchmark Dashboard</h1>
      <p>Upload your own documents, then compare RAG retrieval algorithms with per-algorithm parameters</p>
      <div class="row" style="justify-content:center;margin-top:12px">
        <span class="badge badge-project">Project · QDCVR</span>
        <span class="badge badge-real-code">Real-code · BM25 / FAISS / Cross-Encoder</span>
        <span class="badge badge-real-algo">Real-algo · CRAG / Self-RAG</span>
      </div>
    </header>

    <div class="container">
      <!-- KPI row -->
      <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-value">{{ health.documents ?? '--' }}</div><div class="kpi-label">Documents indexed</div></div>
        <div class="kpi-card"><div class="kpi-value">{{ health.chunks ?? '--' }}</div><div class="kpi-label">Chunks</div></div>
        <div class="kpi-card"><div class="kpi-value">{{ algorithms.length || '--' }}</div><div class="kpi-label">Algorithms</div></div>
        <div class="kpi-card"><div class="kpi-value">{{ avgLatency }}</div><div class="kpi-label">Avg latency (ms)</div></div>
        <div class="kpi-card qdcvr">
          <div class="kpi-value"><span class="status-dot" :class="connected ? 'status-ok' : 'status-err'"></span>{{ connected ? 'Up' : 'Down' }}</div>
          <div class="kpi-label">Backend</div>
        </div>
      </div>

      <div v-if="fatal" class="alert alert-error"><strong>Backend unreachable.</strong> {{ fatal }}</div>

      <!-- Tabs -->
      <div class="tabs">
        <button class="tab" :class="{active: tab === 'benchmark'}" @click="tab = 'benchmark'">🔍 Benchmark</button>
        <button class="tab" :class="{active: tab === 'corpus'}" @click="tab = 'corpus'">📄 Corpus ({{ health.documents ?? 0 }})</button>
        <button class="tab" :class="{active: tab === 'api'}" @click="tab = 'api'">🔌 API</button>
      </div>

      <!-- ══ BENCHMARK ══ -->
      <template v-if="tab === 'benchmark'">
        <div class="section">
          <h2>Query</h2>
          <textarea v-model="query" rows="2" placeholder="Ask something about your documents…" @keydown.enter.exact.prevent="runSearch"></textarea>

          <div class="row" style="margin-top:10px">
            <label class="muted" style="min-width:64px">Top-K</label>
            <input v-model.number="topK" type="number" min="1" max="100" style="width:90px" />
            <label class="muted" style="min-width:64px">Domain</label>
            <select v-model="domainFilter" style="padding:7px 12px;border:1.5px solid var(--border);border-radius:6px;font-size:0.82rem">
              <option value="">All domains</option>
              <option v-for="d in domains.local" :key="d" :value="d">{{ d }}</option>
            </select>
            <div class="spacer"></div>
            <button class="btn btn-primary" :disabled="loading || !query.trim()" @click="runSearch">
              {{ loading ? 'Running…' : 'Run search' }}
            </button>
            <button class="btn btn-outline" :disabled="loading || !query.trim()" @click="runCompare">Compare + metrics</button>
          </div>

          <div class="row" style="margin-top:10px">
            <label class="muted" style="min-width:64px">Ground truth</label>
            <input v-model="groundTruth" placeholder="comma-separated document ids that should be retrieved (optional)" />
          </div>
          <div class="param-help" style="margin-top:4px">
            Supply ground truth to get real P@k / R@k / nDCG@10 / MRR. Without it the API reports only
            latency, score distribution and inter-method overlap — it never invents a precision figure.
          </div>

          <div class="row" style="margin-top:12px">
            <span class="muted">Quick queries:</span>
            <button v-for="q in sampleQueries" :key="q" class="btn btn-outline btn-sm" @click="query = q">{{ q }}</button>
          </div>
        </div>

        <!-- method selection -->
        <div class="section">
          <h2>Algorithms</h2>
          <div v-if="!algorithms.length" class="muted">Loading algorithm registry…</div>
          <div class="method-checkbox">
            <!-- The label carries no click handler: the native checkbox drives the
                 state via @change. Handling clicks on both would toggle twice and
                 leave the selection unchanged. -->
            <label v-for="a in algorithms" :key="a.id" :class="{checked: selected.includes(a.id)}">
              <input type="checkbox" :checked="selected.includes(a.id)" @change="toggleMethod(a.id)" />
              {{ a.label }}
              <span class="badge" :class="'badge-' + a.implementation.toLowerCase().replace('_','-')">{{ a.implementation }}</span>
            </label>
          </div>
          <div class="param-actions">
            <button class="btn btn-outline btn-sm" @click="selectAll">Select all</button>
            <button class="btn btn-outline btn-sm" @click="selected = []">Clear</button>
            <button class="btn btn-outline btn-sm" @click="resetAllParams">Reset all parameters</button>
          </div>
        </div>

        <!-- per-algorithm parameters -->
        <div class="section" v-if="selectedAlgorithms.length">
          <h2>Algorithm parameters <span class="muted">— each algorithm takes its own set</span></h2>
          <div v-if="anyInvalid" class="alert alert-warn">
            One or more parameters are outside the range the algorithm accepts. Leave the field to
            have it clamped, or the API will reject that method with a named error.
          </div>
          <div v-for="a in selectedAlgorithms" :key="a.id" class="param-group">
            <div class="param-group-head">
              <span class="param-group-name">{{ a.label }}</span>
              <span class="badge badge-family">{{ a.family }}</span>
              <span class="badge" :class="'badge-' + a.implementation.toLowerCase().replace('_','-')">{{ a.implementation }}</span>
              <span class="spacer"></span>
              <button v-if="changedCount(a) " class="btn btn-outline btn-sm" @click="resetParams(a.id)">
                reset {{ changedCount(a) }} change(s)
              </button>
            </div>
            <div class="param-group-desc">{{ a.component }} — {{ a.paper }}</div>
            <div class="param-grid">
              <div v-for="p in a.params" :key="p.name" class="param-field"
                   :class="{ 'param-changed': isChanged(a, p), 'param-invalid': isInvalid(a, p) }">
                <label :for="a.id + '-' + p.name">{{ p.name }}</label>

                <select v-if="p.choices" :id="a.id + '-' + p.name"
                        :value="paramValue(a, p)" @change="setParam(a, p, $event.target.value)">
                  <option v-for="c in p.choices" :key="c" :value="c">{{ c }}</option>
                </select>

                <input v-else-if="p.type === 'bool'" type="checkbox" style="width:auto"
                       :id="a.id + '-' + p.name" :checked="!!paramValue(a, p)"
                       @change="setParam(a, p, $event.target.checked)" />

                <input v-else-if="p.type === 'int' || p.type === 'float'" type="number"
                       :id="a.id + '-' + p.name"
                       :min="p.minimum ?? undefined" :max="p.maximum ?? undefined"
                       :step="p.type === 'int' ? 1 : 0.05"
                       :value="paramValue(a, p)"
                       @input="setParam(a, p, $event.target.value)"
                       @change="clampParam(a, p)" />

                <input v-else type="text" :id="a.id + '-' + p.name"
                       :value="paramValue(a, p)" @input="setParam(a, p, $event.target.value)" />

                <div class="param-help">
                  {{ p.description }}
                  <span v-if="p.minimum !== null || p.maximum !== null" class="mono">
                    [{{ p.minimum ?? '−∞' }} … {{ p.maximum ?? '∞' }}]
                  </span>
                  <span class="mono"> default {{ p.default === '' ? '(empty)' : p.default }}</span>
                </div>
                <div v-if="isInvalid(a, p)" class="param-error">
                  out of range {{ rangeText(p) }} — will be clamped on commit
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <!-- comparison -->
        <div v-if="comparison" class="section">
          <h2>Comparison</h2>
          <div class="alert" :class="comparison.metrics_available ? 'alert-ok' : 'alert-info'">
            {{ comparison.metrics_note }}
          </div>
          <table class="comparison-table">
            <thead>
              <tr>
                <th style="text-align:left">Method</th>
                <th>Hits</th><th>Latency (ms)</th><th>Mean score</th><th>Max</th><th>Spread</th>
                <template v-if="comparison.metrics_available">
                  <th>P@5</th><th>R@5</th><th>nDCG@10</th><th>MRR</th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, id) in comparison.per_method" :key="id">
                <td style="text-align:left;font-weight:600">
                  {{ row.label }}
                  <span v-if="row.error" class="badge" style="background:#fef2f2;color:#991b1b">error</span>
                  <span v-else-if="id === comparison.fastest_method" class="badge badge-project">fastest</span>
                </td>
                <td>{{ row.count }}</td>
                <td :class="{best: id === comparison.fastest_method}">{{ row.latency_ms }}</td>
                <td>{{ row.mean_score }}</td>
                <td>{{ row.max_score }}</td>
                <td>{{ row.spread }}</td>
                <template v-if="comparison.metrics_available">
                  <td>{{ row.metrics?.['precision@5'] ?? '—' }}</td>
                  <td>{{ row.metrics?.['recall@5'] ?? '—' }}</td>
                  <td>{{ row.metrics?.['ndcg@10'] ?? '—' }}</td>
                  <td>{{ row.metrics?.['mrr'] ?? '—' }}</td>
                </template>
              </tr>
            </tbody>
          </table>

          <div v-if="Object.keys(comparison.overlap).length" style="margin-top:14px">
            <div class="muted" style="margin-bottom:6px">Inter-method overlap (Jaccard) — how much two methods actually agree</div>
            <div class="metric-strip">
              <span v-for="(v, pair) in comparison.overlap" :key="pair" class="metric-pill">{{ pair }}: {{ v }}</span>
            </div>
          </div>
        </div>

        <!-- chart -->
        <div v-if="comparison" class="section">
          <h2>Latency</h2>
          <div class="chart-container"><canvas ref="chartCanvas"></canvas></div>
        </div>

        <!-- per-method results -->
        <div v-if="lastRun" class="section">
          <h2>Results per algorithm</h2>
          <div v-for="(payload, id) in lastRun" :key="id" class="result-card">
            <div class="result-card-head">
              <span class="badge badge-family">{{ id }}</span>
              <strong>{{ payload.label }}</strong>
              <span class="result-card-stat">{{ payload.count }} hits · {{ payload.latency_ms }} ms</span>
              <span class="spacer"></span>
              <span class="result-card-stat mono">{{ compactParams(payload.params) }}</span>
            </div>
            <div v-if="payload.error" class="alert alert-warn" style="margin:0">{{ payload.error }}</div>
            <div v-for="r in payload.results" :key="r.chunk_id" class="result-row">
              <div class="result-rank" :class="isProject(id) ? 'rank-qdcvr' : 'rank-other'">{{ r.rank }}</div>
              <div class="result-content">
                <div><strong>{{ r.title }}</strong> <span class="doc-meta">{{ r.domain }}</span></div>
                <div class="result-snippet">{{ r.content_preview }}</div>
                <div class="metric-strip">
                  <span class="metric-pill">score {{ r.score }}</span>
                  <span v-if="r.k1 !== undefined" class="metric-pill">k1 {{ r.k1 }}</span>
                  <span v-if="r.b !== undefined" class="metric-pill">b {{ r.b }}</span>
                  <span v-if="r.alpha !== undefined" class="metric-pill">α {{ r.alpha }}</span>
                  <span v-if="r.crag_confidence !== undefined" class="metric-pill">conf {{ r.crag_confidence }}</span>
                  <span v-if="r.reflection_tokens" class="metric-pill">
                    ISREL {{ r.reflection_tokens.ISREL }} · ISSUP {{ r.reflection_tokens.ISSUP }} · ISUSE {{ r.reflection_tokens.ISUSE }}
                  </span>
                  <span class="metric-pill">{{ r.source }}</span>
                </div>
              </div>
            </div>
            <div v-if="!payload.results.length && !payload.error" class="muted">No results.</div>
          </div>
        </div>
      </template>

      <!-- ══ CORPUS ══ -->
      <template v-if="tab === 'corpus'">
        <div class="section">
          <h2>Upload documents</h2>
          <div class="dropzone" :class="{dragging}" @click="fileInput?.click()"
               @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false"
               @drop.prevent="onDrop">
            <div class="dropzone-title">{{ uploading ? 'Uploading…' : 'Drop files here, or click to choose' }}</div>
            <div class="dropzone-hint">
              {{ accepted.join(' · ') }}
            </div>
            <input ref="fileInput" type="file" multiple style="display:none" @change="onPick" />
          </div>

          <div class="row" style="margin-top:10px">
            <label class="muted" style="min-width:64px">Domain</label>
            <input v-model="uploadDomain" placeholder="optional label applied to every uploaded file" style="max-width:380px" />
          </div>

          <div v-if="uploadReport" style="margin-top:14px">
            <div class="alert" :class="uploadReport.failed ? 'alert-warn' : 'alert-ok'">
              {{ uploadReport.uploaded }} file(s) indexed, {{ uploadReport.failed }} failed.
            </div>
            <div v-for="f in uploadReport.files" :key="f.filename" class="doc-row">
              <span :class="f.ok ? 'status-dot status-ok' : 'status-dot status-err'"></span>
              <span class="doc-title">{{ f.filename }}</span>
              <span class="doc-meta" v-if="f.ok">{{ f.kind }} · {{ f.chunks }} chunks · {{ f.characters }} chars</span>
              <span class="doc-meta" v-else style="color:var(--critical)">{{ f.error }}</span>
            </div>
          </div>
        </div>

        <div class="section">
          <h2>Paste text</h2>
          <textarea v-model="newDoc.content" rows="4" placeholder="Paste document content…"></textarea>
          <div class="row" style="margin-top:8px">
            <input v-model="newDoc.title" placeholder="Title" style="flex:1" />
            <input v-model="newDoc.domain" placeholder="Domain" style="flex:1" />
            <button class="btn btn-success" :disabled="!newDoc.content.trim()" @click="addDocument">Add document</button>
          </div>
        </div>

        <div class="section">
          <h2>Corpus ({{ documents.length }} documents, {{ health.chunks ?? 0 }} chunks)</h2>
          <div class="row" style="margin-bottom:10px">
            <button class="btn btn-outline btn-sm" @click="loadDocuments">Refresh</button>
            <button class="btn btn-outline btn-sm" @click="reindex">Rebuild index</button>
            <div class="spacer"></div>
            <button class="btn btn-outline btn-sm" @click="clearCorpus">Clear corpus</button>
          </div>
          <div v-if="!documents.length" class="muted">Corpus is empty — upload files above to get started.</div>
          <div v-for="d in documents" :key="d.id" class="doc-row">
            <span class="doc-title" :title="d.id">{{ d.title }}</span>
            <span class="doc-meta">{{ d.domain || '—' }}</span>
            <span class="doc-meta">{{ d.kind }}</span>
            <span class="doc-meta">{{ d.chunks }} chunks</span>
            <span class="doc-meta">{{ d.characters }} chars</span>
            <button class="icon-btn" title="Delete" @click="deleteDocument(d.id)">✕</button>
          </div>
        </div>
      </template>

      <!-- ══ API ══ -->
      <template v-if="tab === 'api'">
        <div class="section">
          <h2>Service</h2>
          <div class="doc-row"><span class="doc-title">Base URL</span><span class="doc-meta mono">http://127.0.0.1:8800</span></div>
          <div class="doc-row"><span class="doc-title">Interactive docs (OpenAPI)</span>
            <a class="doc-meta" href="http://127.0.0.1:8800/docs" target="_blank" rel="noreferrer">/docs ↗</a></div>
          <div class="doc-row"><span class="doc-title">Platform API used by the QDCVR baselines</span>
            <span class="doc-meta mono">{{ service.platform_api || '—' }}</span></div>
          <div class="doc-row"><span class="doc-title">Embedding model</span>
            <span class="doc-meta mono">{{ service.embedding_model || '—' }}</span></div>
        </div>

        <div class="section">
          <h2>Endpoints</h2>
          <table class="comparison-table">
            <thead><tr><th style="text-align:left">Method</th><th style="text-align:left">Path</th><th style="text-align:left">Purpose</th></tr></thead>
            <tbody>
              <tr v-for="e in endpoints" :key="e.method + e.path">
                <td style="text-align:left"><span class="badge badge-family">{{ e.method }}</span></td>
                <td style="text-align:left" class="mono">{{ e.path }}</td>
                <td style="text-align:left">{{ e.purpose }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section">
          <h2>Run a search with per-algorithm parameters (curl)</h2>
          <div class="result-snippet mono" style="white-space:pre-wrap">{{ curlExample }}</div>
        </div>
      </template>
    </div>

    <footer>
      QDCVR Benchmark Dashboard · CIKM 2027 · FastAPI + sentence-transformers + FAISS + rank_bm25 + ChromaDB
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue';

const API = useRuntimeConfig().public.apiBase || 'http://127.0.0.1:8800';

const tab = ref('benchmark');
const fatal = ref('');
const connected = ref(false);
const health = reactive({ documents: null, chunks: null });
const service = reactive({ platform_api: '', embedding_model: '' });

const algorithms = ref([]);
const accepted = ref([]);
const selected = ref([]);

const query = ref('battery thermal management phase change material');
const groundTruth = ref('');
const topK = ref(5);
const domainFilter = ref('');
const domains = reactive({ local: [] });

const paramOverrides = reactive({});     // { algId: { paramName: value } }
const results = ref(null);
const comparison = ref(null);
const loading = ref(false);
const error = ref('');

const documents = ref([]);
const dragging = ref(false);
const uploading = ref(false);
const uploadReport = ref(null);
const uploadDomain = ref('');
const fileInput = ref(null);
const chartCanvas = ref(null);
const newDoc = reactive({ content: '', title: '', domain: '' });

const sampleQueries = [
  'battery thermal management phase change material',
  'chest x-ray pneumonia detection',
  'graph neural network state of charge',
  'drug delivery hydrogel insulin',
  'cross-encoder reranking passage',
];

const selectedAlgorithms = computed(() =>
  algorithms.value.filter(a => selected.value.includes(a.id)));

const avgLatency = computed(() => {
  if (!results.value) return '--';
  const lats = Object.values(results.value).map(r => r.latency_ms).filter(Boolean);
  return lats.length ? Math.round(lats.reduce((a, b) => a + b, 0) / lats.length) : '--';
});

const lastRun = computed(() => results.value);

const endpoints = [
  { method: 'GET', path: '/', purpose: 'Self-describing API index' },
  { method: 'GET', path: '/api/health', purpose: 'Liveness + corpus and index readiness' },
  { method: 'GET', path: '/api/algorithms', purpose: 'Algorithm registry including every parameter schema' },
  { method: 'GET', path: '/api/domains', purpose: 'Local domains + platform knowledge bases' },
  { method: 'POST', path: '/api/documents', purpose: 'Add or replace one document' },
  { method: 'POST', path: '/api/documents/batch', purpose: 'Add many documents' },
  { method: 'POST', path: '/api/documents/upload', purpose: 'Upload files (multipart) — pdf, docx, md, txt, csv, json, html' },
  { method: 'GET', path: '/api/documents', purpose: 'List the corpus' },
  { method: 'GET', path: '/api/documents/{id}', purpose: 'Read one document and its chunks' },
  { method: 'DELETE', path: '/api/documents/{id}', purpose: 'Delete one document' },
  { method: 'DELETE', path: '/api/documents', purpose: 'Clear the corpus' },
  { method: 'POST', path: '/api/search', purpose: 'Run algorithms with per-algorithm parameters' },
  { method: 'POST', path: '/api/compare', purpose: 'Compare algorithms (+ real IR metrics with ground truth)' },
  { method: 'POST', path: '/api/reindex', purpose: 'Rebuild the dense index' },
];

const curlExample = computed(() => `curl -s -X POST ${API}/api/compare \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "battery thermal management",
    "methods": ["bm25", "dense", "hybrid", "crag"],
    "top_k": 5,
    "params": {
      "bm25":   { "k1": 1.2, "b": 0.6 },
      "hybrid": { "alpha": 0.3, "norm": "minmax" },
      "crag":   { "upper_threshold": 0.7, "expand_trigger": 0.4 }
    },
    "relevant": ["battery-thermal"]
  }'`);

function isProject (id) { return id.startsWith('qdcvr'); }
function compactParams (params) {
  if (!params) return '';
  return Object.entries(params)
    .filter(([k]) => k !== 'kb_id' || params[k])
    .map(([k, v]) => `${k}=${v === '' ? '""' : v}`).join('  ');
}

// ── parameter handling ────────────────────────────────────────────────────
function paramValue (algorithm, param) {
  const override = paramOverrides[algorithm.id]?.[param.name];
  return override === undefined ? param.default : override;
}
function isChanged (algorithm, param) {
  return paramOverrides[algorithm.id]?.[param.name] !== undefined;
}
function changedCount (algorithm) {
  return Object.keys(paramOverrides[algorithm.id] || {}).length;
}
function setParam (algorithm, param, raw) {
  if (!paramOverrides[algorithm.id]) paramOverrides[algorithm.id] = {};
  let value = raw;
  if (param.type === 'int') value = raw === '' ? '' : parseInt(raw, 10);
  else if (param.type === 'float') value = raw === '' ? '' : parseFloat(raw);
  else if (param.type === 'bool') value = !!raw;
  if (value === '' || Number.isNaN(value)) delete paramOverrides[algorithm.id][param.name];
  else paramOverrides[algorithm.id][param.name] = value;
}
function resetParams (id) { delete paramOverrides[id]; }
function resetAllParams () { Object.keys(paramOverrides).forEach(k => delete paramOverrides[k]); }

function rangeText (param) {
  return `within [${param.minimum ?? '−∞'} … ${param.maximum ?? '∞'}]`;
}
function isNum (param) { return param.type === 'int' || param.type === 'float'; }
function isInvalid (algorithm, param) {
  if (!isNum(param)) return false;
  const value = paramValue(algorithm, param);
  if (typeof value !== 'number' || Number.isNaN(value)) return false;
  if (param.minimum != null && value < param.minimum) return true;
  if (param.maximum != null && value > param.maximum) return true;
  return false;
}
/** Snap a committed value into the declared range, so a run is never sent out of bounds. */
function clampParam (algorithm, param) {
  if (!isNum(param)) return;
  const value = paramValue(algorithm, param);
  if (typeof value !== 'number' || Number.isNaN(value)) return;
  let next = value;
  if (param.minimum != null) next = Math.max(next, param.minimum);
  if (param.maximum != null) next = Math.min(next, param.maximum);
  if (param.type === 'int') next = Math.round(next);
  if (next !== value) setParam(algorithm, param, next);
}
const anyInvalid = computed(() =>
  selectedAlgorithms.value.some(a => a.params.some(p => isInvalid(a, p))));

/** Only the deviations from the published defaults are sent; the response echoes the full set. */
function buildParams () {
  const out = {};
  for (const [id, values] of Object.entries(paramOverrides)) {
    if (Object.keys(values).length) out[id] = { ...values };
  }
  return out;
}

function toggleMethod (id) {
  const index = selected.value.indexOf(id);
  if (index >= 0) selected.value.splice(index, 1);
  else selected.value.push(id);
}
function selectAll () { selected.value = algorithms.value.map(a => a.id); }

// ── API calls ─────────────────────────────────────────────────────────────
async function api (path, options = {}) {
  const response = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const text = await response.text();
  let body;
  try { body = JSON.parse(text); } catch { body = text; }
  if (!response.ok) {
    const detail = (body && body.detail) || body;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return body;
}

async function loadHealth () {
  try {
    const data = await api('/api/health');
    connected.value = true;
    health.documents = data.documents;
    health.chunks = data.chunks;
    fatal.value = '';
  } catch (e) {
    connected.value = false;
    fatal.value = e.message;
  }
}

async function loadAlgorithms () {
  const data = await api('/api/algorithms');
  algorithms.value = data.algorithms;
  accepted.value = ['pdf', 'docx', 'md', 'txt', 'csv', 'json', 'html'];
  if (!selected.value.length) {
    selected.value = (data.default_selection || []).filter(
      id => data.algorithms.some(a => a.id === id));
  }
}

async function loadService () {
  const data = await api('/');
  service.platform_api = data.config?.platform_api || '';
  service.embedding_model = data.config?.embedding_model || '';
}

async function loadDomains () {
  try {
    const data = await api('/api/domains');
    domains.local = data.local || [];
  } catch { /* domain list is advisory */ }
}

async function loadDocuments () {
  try {
    const data = await api('/api/documents?limit=500');
    documents.value = data.documents || [];
    health.documents = data.total;
    health.chunks = data.chunks;
  } catch (e) { fatal.value = e.message; }
}

function requestBody () {
  const relevant = groundTruth.value.split(',').map(s => s.trim()).filter(Boolean);
  return {
    query: query.value,
    methods: selected.value,
    top_k: topK.value,
    domain: domainFilter.value || null,
    params: buildParams(),
    ...(relevant.length ? { relevant } : {}),
  };
}

async function runSearch () {
  if (!query.value.trim() || !selected.value.length) return;
  loading.value = true; error.value = ''; comparison.value = null;
  try {
    const data = await api('/api/search', { method: 'POST', body: JSON.stringify(requestBody()) });
    results.value = data.results;
    await loadHealth();
  } catch (e) { error.value = e.message; }
  finally { loading.value = false; }
}

async function runCompare () {
  if (!query.value.trim() || !selected.value.length) return;
  loading.value = true; error.value = '';
  try {
    const data = await api('/api/compare', { method: 'POST', body: JSON.stringify(requestBody()) });
    results.value = data.results;
    comparison.value = data.comparison;
    await nextTick();
    renderChart(data.comparison);
  } catch (e) { error.value = e.message; }
  finally { loading.value = false; }
}

// ── uploads ───────────────────────────────────────────────────────────────
function onPick (event) { uploadFiles(event.target.files); event.target.value = ''; }
function onDrop (event) { dragging.value = false; uploadFiles(event.dataTransfer.files); }

async function uploadFiles (fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  uploading.value = true; error.value = '';
  try {
    const form = new FormData();
    for (const file of files) form.append('files', file, file.name);
    const suffix = uploadDomain.value ? `?domain=${encodeURIComponent(uploadDomain.value)}` : '';
    const response = await fetch(`${API}/api/documents/upload${suffix}`, { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    uploadReport.value = data;
    await Promise.all([loadDocuments(), loadHealth(), loadDomains()]);
  } catch (e) { error.value = `Upload failed: ${e.message}`; }
  finally { uploading.value = false; }
}

async function addDocument () {
  if (!newDoc.content.trim()) return;
  try {
    await api('/api/documents', {
      method: 'POST',
      body: JSON.stringify({ content: newDoc.content, title: newDoc.title || 'Untitled', domain: newDoc.domain }),
    });
    newDoc.content = ''; newDoc.title = ''; newDoc.domain = '';
    await Promise.all([loadDocuments(), loadHealth(), loadDomains()]);
  } catch (e) { error.value = e.message; }
}

async function deleteDocument (id) {
  try {
    await api(`/api/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });
    await Promise.all([loadDocuments(), loadHealth()]);
  } catch (e) { error.value = e.message; }
}

async function clearCorpus () {
  if (!confirm('Delete every document in the corpus?')) return;
  try {
    await api('/api/documents', { method: 'DELETE' });
    uploadReport.value = null;
    await Promise.all([loadDocuments(), loadHealth(), loadDomains()]);
  } catch (e) { error.value = e.message; }
}

async function reindex () {
  try {
    const data = await api('/api/reindex', { method: 'POST' });
    await loadHealth();
    alert(`Index rebuilt in ${data.elapsed_ms} ms — ${data.chunks} chunks.`);
  } catch (e) { error.value = e.message; }
}

// ── chart ─────────────────────────────────────────────────────────────────
let chart = null;
async function renderChart (comp) {
  if (!comp || !chartCanvas.value) return;
  const { Chart, registerables } = await import('chart.js');
  Chart.register(...registerables);
  if (chart) chart.destroy();
  const ids = Object.keys(comp.per_method);
  chart = new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels: ids.map(id => comp.per_method[id].label),
      datasets: [{
        label: 'Latency (ms)',
        data: ids.map(id => comp.per_method[id].latency_ms),
        backgroundColor: ids.map(id => id.startsWith('qdcvr') ? '#10b981' : '#6366f1'),
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { title: { display: true, text: 'ms' }, beginAtZero: true } },
    },
  });
}

onMounted(async () => {
  try {
    await Promise.all([loadHealth(), loadAlgorithms(), loadService(), loadDocuments(), loadDomains()]);
  } catch (e) { fatal.value = e.message; }
});
</script>
