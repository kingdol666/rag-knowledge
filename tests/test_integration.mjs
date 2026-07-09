import http from 'http';

function testApi(name, url, method = 'GET', body = null) {
  return new Promise((resolve) => {
    const urlObj = new URL(url);
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname + urlObj.search,
      method: method,
      headers: { 'Content-Type': 'application/json' }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const status = res.statusCode;
        let parsed;
        try { parsed = JSON.parse(data); } catch (e) { parsed = data.substring(0, 200); }
        resolve({ name, status, ok: status >= 200 && status < 300, data: parsed });
      });
    });

    req.on('error', (e) => {
      resolve({ name, status: 0, ok: false, error: e.message });
    });

    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function run() {
  const results = [];

  // === Backend Direct APIs ===
  results.push(await testApi('Backend Health', 'http://localhost:8765/api/v1/health'));
  results.push(await testApi('Backend MinerU Status', 'http://localhost:8765/api/v1/mineru/status'));

  // === Frontend Proxy APIs ===
  results.push(await testApi('Frontend Health Proxy', 'http://localhost:6789/api/health'));

  // KB APIs
  results.push(await testApi('KB List', 'http://localhost:6789/api/kb/list'));
  results.push(await testApi('KB Catalog', 'http://localhost:6789/api/kb/catalog'));
  results.push(await testApi('KB Tags List', 'http://localhost:6789/api/kb/tags/list'));

  // File System APIs
  results.push(await testApi('FS Tree', 'http://localhost:6789/api/filesystem/tree'));
  results.push(await testApi('FS Count', 'http://localhost:6789/api/filesystem/count'));

  // Search APIs
  results.push(await testApi('KB Search (keyword)', 'http://localhost:6789/api/kb/search?query=RAG'));
  results.push(await testApi('Vector Search', 'http://localhost:6789/api/search/vector', 'POST', { query: 'retrieval augmented generation', kb_id: '', top_k: 5 }));
  results.push(await testApi('Two-Stage Search', 'http://localhost:6789/api/search/two-stage', 'POST', { query: 'attention mechanism', kb_id: '', top_k: 5 }));
  results.push(await testApi('Search Stats', 'http://localhost:6789/api/search/stats'));
  results.push(await testApi('Batch Vector Search', 'http://localhost:6789/api/search/batch-vector', 'POST', { query_doc_paths: [], top_k: 5 }));

  // Graph APIs
  results.push(await testApi('Graph Stats', 'http://localhost:6789/api/graph/stats'));
  results.push(await testApi('Graph Health', 'http://localhost:6789/api/graph/health'));
  results.push(await testApi('Graph Search', 'http://localhost:6789/api/graph/search?q=attention'));

  // Parse APIs
  results.push(await testApi('Parse Status', 'http://localhost:6789/api/parse/status'));

  // === Print Results ===
  console.log('\n========== API Integration Test Results ==========\n');
  let passCount = 0;
  let failCount = 0;

  for (const r of results) {
    const icon = r.ok ? '✅ PASS' : '❌ FAIL';
    if (r.ok) passCount++; else failCount++;
    console.log(`[${icon}] ${r.name} (HTTP ${r.status})`);
    if (!r.ok || r.error) {
      console.log('  Error:', r.error || (typeof r.data === 'string' ? r.data : JSON.stringify(r.data).substring(0, 300)));
    } else if (r.data && typeof r.data === 'object') {
      const keys = Object.keys(r.data);
      console.log('  Response keys:', keys.join(', '));
      if (r.data.data && typeof r.data.data === 'object') {
        const innerKeys = Object.keys(r.data.data);
        console.log('  Inner data keys:', innerKeys.join(', '));
        // Show counts if available
        if (r.data.data.count !== undefined) console.log('  Count:', r.data.data.count);
        if (r.data.data.total !== undefined) console.log('  Total:', r.data.data.total);
        if (Array.isArray(r.data.data.items)) console.log('  Items:', r.data.data.items.length);
        if (Array.isArray(r.data.data.results)) console.log('  Results:', r.data.data.results.length);
        if (Array.isArray(r.data.data.kbs)) console.log('  KBs:', r.data.data.kbs.length);
        if (Array.isArray(r.data.data.tags)) console.log('  Tags:', r.data.data.tags.length);
      }
    }
  }

  console.log('\n==========================================');
  console.log(`Total: ${results.length} | ✅ PASS: ${passCount} | ❌ FAIL: ${failCount}`);
  console.log('==========================================\n');
}

run().catch(console.error);
