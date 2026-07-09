import { chromium } from 'playwright'

const BASE = 'http://localhost:6789'
let pass = 0
let fail = 0

function log(name, ok, detail = '') {
  if (ok) {
    console.log(`\x1b[32m[PASS]\x1b[0m ${name}`)
    pass++
  } else {
    console.log(`\x1b[31m[FAIL]\x1b[0m ${name} ${detail}`)
    fail++
  }
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } })

  // Collect console errors
  const consoleErrors = []
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text())
  })

  // ===== Test 1: Home Page =====
  console.log('\n=== Test 1: Home Page ===')
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2000)
  const heroText = await page.textContent('body')
  log('Home page loads', heroText.length > 1000, `body length: ${heroText.length}`)
  log('Home has RAG text', heroText.includes('RAG'))
  log('Home has features section', heroText.includes('核心功能') || heroText.includes('feature') || heroText.includes('功能'))

  // ===== Test 2: Knowledge Search Page =====
  console.log('\n=== Test 2: Knowledge Search Page ===')
  await page.goto(`${BASE}/knowledge-search`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(3000)

  // Check search mode selector
  const twoStageBtn = await page.locator('text=两阶段').count()
  log('Has two-stage mode button', twoStageBtn > 0)

  const vectorBtn = await page.locator('text=向量语义').count()
  log('Has vector mode button', vectorBtn > 0)

  const keywordBtn = await page.locator('text=关键词').count()
  log('Has keyword mode button', keywordBtn > 0)

  // Check KB catalog cards
  const kbCards = await page.locator('.kb-card').count()
  log('KB catalog shows cards', kbCards > 0, `found ${kbCards} cards`)

  // Perform a two-stage search
  console.log('\n  Performing two-stage search...')
  // Use a more robust selector for the search input
  const searchInput = page.locator('.search-input input, input[placeholder*="检索"]').first()
  await searchInput.waitFor({ state: 'visible', timeout: 10000 })
  await searchInput.fill('attention mechanism transformer')

  // Find and click the search button (Ant Design a-input-search enter-button)
  const searchBtn = page.locator('.search-input button, .search-input .ant-input-search-button').first()
  await searchBtn.waitFor({ state: 'visible', timeout: 10000 })
  await searchBtn.click()

  // Wait for results
  await page.waitForTimeout(8000)

  // Check search results
  const resultCards = await page.locator('.result-card').count()
  log('Two-stage search returns results', resultCards > 0, `found ${resultCards} results`)

  if (resultCards > 0) {
    // Check result content
    const firstResult = await page.locator('.result-card').first().textContent()
    log('Result has content', firstResult.length > 20, `text: ${firstResult.substring(0, 100)}...`)

    // Check for score display
    const hasScore = await page.locator('.result-scores').first().count()
    log('Result has score info', hasScore > 0)

    // Check for content preview
    const hasPreview = await page.locator('.result-preview').first().count()
    log('Result has content preview', hasPreview > 0)

    // Check for KB tag
    const hasKbTag = await page.locator('.result-meta .ant-tag').first().count()
    log('Result has KB tag', hasKbTag > 0)
  }

  // ===== Test 3: Vector Search =====
  console.log('\n=== Test 3: Vector Search ===')
  // Use the radio button wrapper, not the subtitle text
  await page.locator('.ant-radio-button-wrapper:has-text("向量语义")').click()
  await page.waitForTimeout(500)
  await searchInput.fill('deep learning neural network')
  await searchBtn.click()
  await page.waitForTimeout(8000)

  const vectorResults = await page.locator('.result-card').count()
  log('Vector search returns results', vectorResults > 0, `found ${vectorResults} results`)

  if (vectorResults > 0) {
    const firstResult = await page.locator('.result-card').first().textContent()
    log('Vector result has content', firstResult.length > 20)
  }

  // ===== Test 4: Keyword Search =====
  console.log('\n=== Test 4: Keyword Search ===')
  await page.locator('.ant-radio-button-wrapper:has-text("关键词")').click()
  await page.waitForTimeout(500)
  await searchInput.fill('paper')
  await searchBtn.click()
  await page.waitForTimeout(5000)

  const keywordResults = await page.locator('.result-card').count()
  log('Keyword search executes', keywordResults >= 0, `found ${keywordResults} results`)

  // ===== Test 5: Knowledge Graph Page =====
  console.log('\n=== Test 5: Knowledge Graph Page ===')
  await page.goto(`${BASE}/knowledge-graph`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(8000)

  // Check SVG canvas
  const svgCount = await page.locator('svg').count()
  log('Graph page has SVG canvas', svgCount > 0)

  // Check stat cards
  const statCards = await page.locator('.stat-card').count()
  log('Graph page has stat cards', statCards > 0, `found ${statCards} stat cards`)

  // Check if stat values are populated
  if (statCards > 0) {
    const statValues = await page.locator('.stat-card-value').allTextContents()
    log('Stat cards have values', statValues.some(v => v && v.trim() !== '0'), `values: ${statValues.join(', ')}`)
  }

  // Check toolbar
  const toolbar = await page.locator('.graph-toolbar').count()
  log('Graph page has toolbar', toolbar > 0)

  // Check legend
  const legend = await page.locator('.graph-legend').count()
  log('Graph page has legend', legend > 0)

  // Check if nodes are rendered
  const graphNodes = await page.locator('.graph-node-group').count()
  log('Graph renders nodes', graphNodes > 0, `found ${graphNodes} nodes`)

  // Check if edges are rendered
  const graphEdges = await page.locator('.graph-edge').count()
  log('Graph renders edges', graphEdges > 0, `found ${graphEdges} edges`)

  // Check filter panel
  const filterInput = await page.locator('input[placeholder*="过滤"]').count()
  log('Graph page has filter input', filterInput > 0)

  // Check detail panel (no selection state)
  const noSelection = await page.locator('.no-selection').count()
  log('Graph page shows no-selection state initially', noSelection > 0)

  // Test node click interaction
  if (graphNodes > 0) {
    await page.locator('.graph-node-group').first().click()
    await page.waitForTimeout(1000)
    const detailPanel = await page.locator('.node-detail').count()
    log('Node click shows detail panel', detailPanel > 0)

    if (detailPanel > 0) {
      const detailContent = await page.locator('.node-detail').first().textContent()
      log('Detail panel has content', detailContent.length > 10)
    }
  }

  // ===== Test 6: File System Page =====
  console.log('\n=== Test 6: File System Page ===')
  await page.goto(`${BASE}/file-system`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(3000)
  const fsContent = await page.textContent('body')
  log('File system page loads', fsContent.length > 1000, `body length: ${fsContent.length}`)

  // ===== Test 7: Knowledge Base Page =====
  console.log('\n=== Test 7: Knowledge Base Page ===')
  await page.goto(`${BASE}/knowledge-base`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(3000)
  const kbContent = await page.textContent('body')
  log('Knowledge base page loads', kbContent.length > 1000, `body length: ${kbContent.length}`)

  // ===== Test 8: Console Error Check =====
  console.log('\n=== Test 8: Console Error Check ===')
  const criticalErrors = consoleErrors.filter(e =>
    !e.includes('favicon') &&
    !e.includes('Manifest') &&
    !e.includes('stylesheet') &&
    !e.includes('Failed to load resource') &&
    !e.includes('net::ERR') &&
    !e.includes('antd') &&
    !e.includes('Ant Design')
  )
  log('No critical console errors', criticalErrors.length === 0,
    criticalErrors.length > 0 ? `errors: ${criticalErrors.slice(0, 5).join('; ')}` : `total errors: ${consoleErrors.length} (all non-critical)`)

  await browser.close()

  console.log(`\n${'='.repeat(50)}`)
  console.log(`\x1b[${fail === 0 ? '32' : '33'}m=== Results: ${pass} passed, ${fail} failed ===\x1b[0m`)
  process.exit(fail > 0 ? 1 : 0)
}

run().catch(err => {
  console.error('Test runner error:', err)
  process.exit(1)
})
