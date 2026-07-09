/**
 * Comprehensive API test for all backend and frontend proxy endpoints
 */
import http from 'http'

function testAPI(port, method, path, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null
    const options = {
      hostname: 'localhost',
      port,
      path,
      method,
      headers: { 'Content-Type': 'application/json' }
    }
    if (data) options.headers['Content-Length'] = Buffer.byteLength(data)
    const req = http.request(options, res => {
      let rs = ''
      res.on('data', c => rs += c)
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(rs) })
        } catch (e) {
          resolve({ status: res.statusCode, data: rs.slice(0, 200) })
        }
      })
    })
    req.on('error', reject)
    if (data) req.write(data)
    req.end()
  })
}

async function run() {
  let pass = 0, fail = 0

  function log(name, ok, detail = '') {
    const icon = ok ? '✅' : '❌'
    console.log(`${icon} ${name}${detail ? ' — ' + detail : ''}`)
    if (ok) pass++; else fail++
  }

  const BE = 8765
  const FE = 6789

  console.log('========== 后端 API 测试 ==========')

  // Health
  let r = await testAPI(BE, 'GET', '/api/v1/health')
  log('后端健康检查', r.status === 200 && r.data.status === 'healthy', `[${r.status}]`)

  // MinerU status
  r = await testAPI(BE, 'GET', '/api/v1/mineru/status')
  log('MinerU状态', r.status === 200, `[${r.status}] ${JSON.stringify(r.data).slice(0, 80)}`)

  // Search stats
  r = await testAPI(BE, 'GET', '/api/v1/search/stats')
  log('搜索统计', r.status === 200 && r.data.success, `[${r.status}] docs: ${r.data?.stats?.total_documents || '?'}`)

  // Vector search
  r = await testAPI(BE, 'POST', '/api/v1/search/vector', { query: 'attention mechanism', top_k: 3, kb_id: '', balance_kbs: false })
  log('向量搜索', r.status === 200 && r.data.success, `[${r.status}] results: ${r.data?.results?.length || 0}`)

  // Two-stage search
  r = await testAPI(BE, 'POST', '/api/v1/search/two-stage', { query: 'RAG', stage1_top_k: 10, stage2_top_k: 3, kb_id: '', balance_kbs: false })
  log('两阶段搜索', r.status === 200 && r.data.success, `[${r.status}] stage2: ${r.data?.stage2?.results?.length || 0} results`)

  // Batch vector search
  r = await testAPI(BE, 'POST', '/api/v1/search/batch-vector', { queries: ['RAG', 'transformer'], top_k: 3, kb_id: '' })
  log('批量向量搜索', r.status === 200 && r.data.success, `[${r.status}]`)

  // Reindex
  r = await testAPI(BE, 'POST', '/api/v1/search/reindex', { kb_id: '', force: false })
  log('重建索引', r.status === 200, `[${r.status}] ${JSON.stringify(r.data).slice(0, 80)}`)

  // Graph health
  r = await testAPI(BE, 'GET', '/api/v1/graph/health')
  log('图谱健康检查', r.status === 200 && r.data.success, `[${r.status}] available: ${r.data?.health?.available}`)

  // Graph stats
  r = await testAPI(BE, 'GET', '/api/v1/graph/stats')
  log('图谱统计', r.status === 200 && r.data.success, `[${r.status}] nodes: ${r.data?.stats?.node_count}, edges: ${r.data?.stats?.edge_count}`)

  // Graph search documents
  r = await testAPI(BE, 'GET', '/api/v1/graph/search/documents?keyword=RAG&limit=5')
  log('图谱文档搜索', r.status === 200 && r.data.success, `[${r.status}] count: ${r.data?.count}`)

  // Graph search kbs
  r = await testAPI(BE, 'GET', '/api/v1/graph/search/kbs?keyword=AI&limit=5')
  log('图谱KB搜索', r.status === 200 && r.data.success, `[${r.status}] count: ${r.data?.count}`)

  // Graph search tags
  r = await testAPI(BE, 'GET', '/api/v1/graph/search/tags?keyword=AI&limit=5')
  log('图谱标签搜索', r.status === 200 && r.data.success, `[${r.status}] count: ${r.data?.count}`)

  // Graph cross-kb
  r = await testAPI(BE, 'GET', '/api/v1/graph/cross-kb-documents?limit=5')
  log('跨KB文档', r.status === 200 && r.data.success, `[${r.status}] count: ${r.data?.count}`)

  // Graph neighbors
  r = await testAPI(BE, 'GET', '/api/v1/graph/neighbors?node_id=RAG&node_type=document&depth=1')
  log('图谱邻居', r.status === 200, `[${r.status}]`)

  console.log('\n========== 前端代理 API 测试 ==========')

  // Graph search via proxy
  r = await testAPI(FE, 'GET', '/api/graph/search?keyword=RAG&type=documents&limit=5')
  log('前端代理-图谱搜索', r.status === 200 && r.data.success, `[${r.status}] count: ${r.data?.count}`)

  // Graph health via proxy
  r = await testAPI(FE, 'GET', '/api/graph/health')
  log('前端代理-图谱健康', r.status === 200 && r.data.success, `[${r.status}] available: ${r.data?.health?.available}`)

  // Graph stats via proxy
  r = await testAPI(FE, 'GET', '/api/graph/stats')
  log('前端代理-图谱统计', r.status === 200 && r.data.success, `[${r.status}] nodes: ${r.data?.stats?.node_count}`)

  // Two-stage search via proxy
  r = await testAPI(FE, 'POST', '/api/search/two-stage', { query: 'RAG', stage1_top_k: 10, stage2_top_k: 3, kb_id: '', balance_kbs: false })
  log('前端代理-两阶段搜索', r.status === 200 && r.data.success, `[${r.status}] results: ${r.data?.stage2?.results?.length || 0}`)

  // Vector search via proxy
  r = await testAPI(FE, 'POST', '/api/search/vector', { query: 'attention', top_k: 3, kb_id: '', balance_kbs: false })
  log('前端代理-向量搜索', r.status === 200 && r.data.success, `[${r.status}] results: ${r.data?.results?.length || 0}`)

  // KB catalog
  r = await testAPI(FE, 'GET', '/api/kb/catalog')
  log('前端代理-KB目录', r.status === 200, `[${r.status}] KBs: ${r.data?.knowledgeBases?.length || 0}`)

  // KB tags
  r = await testAPI(FE, 'GET', '/api/kb/tags')
  log('前端代理-KB标签', r.status === 200, `[${r.status}]`)

  console.log('\n========== 测试总结 ==========')
  console.log(`✅ 通过: ${pass}`)
  console.log(`❌ 失败: ${fail}`)
  console.log(`总计: ${pass + fail}`)
  console.log(`通过率: ${((pass / (pass + fail)) * 100).toFixed(1)}%`)

  return fail === 0
}

run().then(success => process.exit(success ? 0 : 1)).catch(err => {
  console.error('Test error:', err)
  process.exit(1)
})
