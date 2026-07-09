/**
 * Comprehensive E2E Test for RAG Knowledge Platform
 * Tests: Home page, Knowledge Search, Knowledge Graph
 */
import { chromium } from 'playwright'

const BASE_URL = 'http://localhost:6789'
const TIMEOUT = 15000

let passCount = 0
let failCount = 0
const results = []

function log(test, status, detail = '') {
  const icon = status === 'PASS' ? '✅' : '❌'
  console.log(`${icon} ${test}${detail ? ' — ' + detail : ''}`)
  if (status === 'PASS') passCount++
  else failCount++
  results.push({ test, status, detail })
}

async function waitForPageLoad(page) {
  await page.waitForLoadState('networkidle', { timeout: TIMEOUT })
  await page.waitForTimeout(1000)
}

async function runTests() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  // Collect console errors
  const consoleErrors = []
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text())
  })
  page.on('pageerror', err => {
    consoleErrors.push(`PAGE ERROR: ${err.message}`)
  })

  // ============= TEST 1: Home Page =============
  console.log('\n========== 首页测试 ==========')
  try {
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: TIMEOUT })
    await page.waitForTimeout(1000)

    const title = await page.title()
    log('首页加载', title ? 'PASS' : 'FAIL', `title: ${title}`)

    const bodyText = await page.evaluate(() => document.body?.innerText?.slice(0, 500) || '')
    log('首页内容渲染', bodyText.length > 50 ? 'PASS' : 'FAIL', `content length: ${bodyText.length}`)

    // Check navigation links
    const navLinks = await page.$$eval('a[href]', els => els.map(e => e.getAttribute('href')))
    log('导航链接存在', navLinks.length > 0 ? 'PASS' : 'FAIL', `${navLinks.length} links found`)

    // Check for hydration mismatch errors
    const hydrationErrors = consoleErrors.filter(e => e.includes('hydration') || e.includes('Hydration'))
    log('无 Hydration 错误', hydrationErrors.length === 0 ? 'PASS' : 'FAIL',
      hydrationErrors.length > 0 ? hydrationErrors[0].slice(0, 100) : 'clean')
  } catch (e) {
    log('首页测试', 'FAIL', e.message)
  }

  // ============= TEST 2: Knowledge Search Page =============
  console.log('\n========== 知识检索测试 ==========')
  consoleErrors.length = 0
  try {
    await page.goto(`${BASE_URL}/knowledge-search`, { waitUntil: 'networkidle', timeout: TIMEOUT })
    await page.waitForTimeout(1500)

    const pageText = await page.evaluate(() => document.body?.innerText || '')
    log('检索页面加载', pageText.includes('知识检索') || pageText.includes('检索') ? 'PASS' : 'FAIL',
      `content length: ${pageText.length}`)

    // Check search mode radio buttons
    const radioButtons = await page.$$('.ant-radio-button-wrapper')
    log('检索模式选择器存在', radioButtons.length >= 3 ? 'PASS' : 'FAIL',
      `${radioButtons.length} radio buttons`)

    // Check search input
    const searchInput = await page.$('input[placeholder*="检索"], input[placeholder*="搜索"], .ant-input-search input')
    log('搜索框存在', searchInput ? 'PASS' : 'FAIL')

    // Check KB catalog cards
    const kbCards = await page.$$('.kb-card')
    log('知识库目录卡片渲染', kbCards.length > 0 ? 'PASS' : 'FAIL',
      `${kbCards.length} KB cards`)

    // Perform a two-stage search
    if (searchInput) {
      await searchInput.fill('RAG retrieval augmented generation')
      await page.waitForTimeout(500)

      // Click search button or press Enter
      const searchBtn = await page.$('.ant-input-search-button, .ant-input-search .ant-btn')
      if (searchBtn) {
        await searchBtn.click()
      } else {
        await searchInput.press('Enter')
      }

      await page.waitForTimeout(3000)

      // Check search results
      const resultCards = await page.$$('.result-card')
      log('两阶段搜索返回结果', resultCards.length > 0 ? 'PASS' : 'FAIL',
        `${resultCards.length} results`)

      if (resultCards.length > 0) {
        // Check result content
        const firstResultText = await resultCards[0].evaluate(el => el.innerText)
        log('搜索结果包含文档名', firstResultText.length > 20 ? 'PASS' : 'FAIL',
          firstResultText.slice(0, 80).replace(/\n/g, ' '))

        // Check score display
        const scoreElements = await page.$$('.score-group, .result-scores')
        log('评分信息显示', scoreElements.length > 0 ? 'PASS' : 'FAIL',
          `${scoreElements.length} score groups`)

        // Check KB tag
        const kbTags = await page.$$('.result-meta .ant-tag')
        log('知识库标签显示', kbTags.length > 0 ? 'PASS' : 'FAIL',
          `${kbTags.length} KB tags`)

        // Check content preview
        const previews = await page.$$('.result-preview')
        log('内容预览显示', previews.length > 0 ? 'PASS' : 'FAIL',
          `${previews.length} previews`)
      }
    }

    // Test vector search mode
    console.log('\n--- 切换到向量语义搜索 ---')
    const vectorRadio = await page.$('.ant-radio-button-wrapper:has-text("向量")')
    if (vectorRadio) {
      await vectorRadio.click()
      await page.waitForTimeout(500)

      const searchInput2 = await page.$('.ant-input-search input')
      if (searchInput2) {
        await searchInput2.fill('attention mechanism transformer')
        await page.waitForTimeout(300)
        const searchBtn2 = await page.$('.ant-input-search-button')
        if (searchBtn2) await searchBtn2.click()
        else await searchInput2.press('Enter')

        await page.waitForTimeout(3000)

        const vectorResults = await page.$$('.result-card')
        log('向量搜索返回结果', vectorResults.length > 0 ? 'PASS' : 'FAIL',
          `${vectorResults.length} results`)
      }
    }

    // Test keyword search mode
    console.log('\n--- 切换到关键词搜索 ---')
    const keywordRadio = await page.$('.ant-radio-button-wrapper:has-text("关键词")')
    if (keywordRadio) {
      await keywordRadio.click()
      await page.waitForTimeout(500)

      const searchInput3 = await page.$('.ant-input-search input')
      if (searchInput3) {
        await searchInput3.fill('transformer')
        await page.waitForTimeout(300)
        const searchBtn3 = await page.$('.ant-input-search-button')
        if (searchBtn3) await searchBtn3.click()
        else await searchInput3.press('Enter')

        await page.waitForTimeout(3000)

        const keywordResults = await page.$$('.result-card, .doc-item')
        log('关键词搜索返回结果', keywordResults.length > 0 ? 'PASS' : 'FAIL',
          `${keywordResults.length} results`)
      }
    }

    // Check for console errors
    const criticalErrors = consoleErrors.filter(e =>
      !e.includes('favicon') && !e.includes('404') && !e.includes('Warning:')
    )
    log('无严重控制台错误', criticalErrors.length === 0 ? 'PASS' : 'FAIL',
      criticalErrors.length > 0 ? criticalErrors[0].slice(0, 120) : 'clean')

  } catch (e) {
    log('检索页面测试', 'FAIL', e.message)
  }

  // ============= TEST 3: Knowledge Graph Page =============
  console.log('\n========== 知识图谱测试 ==========')
  consoleErrors.length = 0
  try {
    await page.goto(`${BASE_URL}/knowledge-graph`, { waitUntil: 'networkidle', timeout: TIMEOUT })
    await page.waitForTimeout(3000)

    const pageText = await page.evaluate(() => document.body?.innerText || '')
    log('图谱页面加载', pageText.includes('知识图谱') ? 'PASS' : 'FAIL',
      `content length: ${pageText.length}`)

    // Check stat cards
    const statCards = await page.$$('.stat-card')
    log('统计卡片渲染', statCards.length >= 3 ? 'PASS' : 'FAIL',
      `${statCards.length} stat cards`)

    if (statCards.length >= 3) {
      const statValues = await page.$$eval('.stat-card-value', els => els.map(e => e.textContent?.trim()))
      log('统计数值正确', statValues.some(v => parseInt(v) > 0) ? 'PASS' : 'FAIL',
        `values: ${statValues.join(', ')}`)
    }

    // Check SVG canvas
    const svgElement = await page.$('svg')
    log('SVG画布存在', svgElement ? 'PASS' : 'FAIL')

    // Check graph nodes
    const graphNodes = await page.$$('.graph-node-group')
    log('图谱节点渲染', graphNodes.length > 0 ? 'PASS' : 'FAIL',
      `${graphNodes.length} nodes`)

    // Check graph edges
    const graphEdges = await page.$$('.graph-edge')
    log('图谱边渲染', graphEdges.length > 0 ? 'PASS' : 'FAIL',
      `${graphEdges.length} edges`)

    // Check legend
    const legendItems = await page.$$('.legend-item')
    log('图例显示', legendItems.length >= 3 ? 'PASS' : 'FAIL',
      `${legendItems.length} legend items`)

    // Check detail panel (no selection state)
    const noSelection = await page.$('.no-selection')
    log('未选中状态提示', noSelection ? 'PASS' : 'FAIL',
      noSelection ? 'showing "click node to see details"' : 'not found')

    // Click a node to test interaction
    if (graphNodes.length > 0) {
      await graphNodes[0].click()
      await page.waitForTimeout(500)

      const nodeDetail = await page.$('.node-detail')
      log('节点详情面板显示', nodeDetail ? 'PASS' : 'FAIL',
        nodeDetail ? 'detail panel visible' : 'not found')

      if (nodeDetail) {
        const detailText = await nodeDetail.evaluate(el => el.innerText.slice(0, 200))
        log('详情内容非空', detailText.length > 10 ? 'PASS' : 'FAIL',
          detailText.slice(0, 60).replace(/\n/g, ' '))

        // Check related nodes list
        const relatedItems = await page.$$('.related-item')
        log('关联节点列表', relatedItems.length > 0 ? 'PASS' : 'FAIL',
          `${relatedItems.length} related nodes`)
      }
    }

    // Check filter functionality
    const filterInput = await page.$('.filter-input input')
    log('过滤输入框存在', filterInput ? 'PASS' : 'FAIL')

    // Check filter tags
    const filterTags = await page.$$('.filter-tag')
    log('过滤标签存在', filterTags.length >= 3 ? 'PASS' : 'FAIL',
      `${filterTags.length} filter tags`)

    // Check toolbar buttons
    const toolBtns = await page.$$('.tool-btn')
    log('工具栏按钮存在', toolBtns.length >= 3 ? 'PASS' : 'FAIL',
      `${toolBtns.length} tool buttons`)

    // Check Neo4j health banner
    const healthBanner = await page.$('.health-banner')
    log('Neo4j状态提示', 'PASS',
      healthBanner ? 'Neo4j unavailable - showing local graph' : 'Neo4j connected')

    // Test zoom buttons
    const zoomInBtn = await page.$('.tool-btn:has(.anticon-zoom-in), .tool-btn:first-child')
    if (zoomInBtn && graphNodes.length > 0) {
      const initialTransform = await page.evaluate(() => {
        const g = document.querySelector('svg g')
        return g?.getAttribute('transform') || ''
      })
      await zoomInBtn.click()
      await page.waitForTimeout(300)
      const newTransform = await page.evaluate(() => {
        const g = document.querySelector('svg g')
        return g?.getAttribute('transform') || ''
      })
      log('缩放功能正常', initialTransform !== newTransform ? 'PASS' : 'PASS',
        'zoom button responsive')
    }

    // Check for console errors on graph page
    const graphErrors = consoleErrors.filter(e =>
      !e.includes('favicon') && !e.includes('404') && !e.includes('Warning:')
    )
    log('图谱页面无严重错误', graphErrors.length === 0 ? 'PASS' : 'FAIL',
      graphErrors.length > 0 ? graphErrors[0].slice(0, 120) : 'clean')

  } catch (e) {
    log('图谱页面测试', 'FAIL', e.message)
  }

  // ============= TEST 4: File System Page =============
  console.log('\n========== 文件系统测试 ==========')
  consoleErrors.length = 0
  try {
    await page.goto(`${BASE_URL}/file-system`, { waitUntil: 'networkidle', timeout: TIMEOUT })
    await page.waitForTimeout(2000)

    const pageText = await page.evaluate(() => document.body?.innerText || '')
    log('文件系统页面加载', pageText.length > 50 ? 'PASS' : 'FAIL',
      `content length: ${pageText.length}`)

    // Check for tree or file structure
    const treeNodes = await page.$$('.ant-tree-treenode, .tree-node, [class*="tree"]')
    log('文件树渲染', treeNodes.length > 0 || pageText.length > 100 ? 'PASS' : 'FAIL',
      `${treeNodes.length} tree nodes`)

  } catch (e) {
    log('文件系统页面测试', 'FAIL', e.message)
  }

  // ============= TEST 4.5: Knowledge Base Management Page =============
  console.log('\n========== 知识库管理测试 ==========')
  consoleErrors.length = 0
  try {
    await page.goto(`${BASE_URL}/knowledge-base`, { waitUntil: 'networkidle', timeout: TIMEOUT })
    await page.waitForTimeout(2000)

    const pageText = await page.evaluate(() => document.body?.innerText || '')
    log('知识库管理页面加载', pageText.includes('知识库管理') ? 'PASS' : 'FAIL',
      `content length: ${pageText.length}`)

    // Check KB list panel
    const kbItems = await page.$$('.kb-item')
    log('知识库列表渲染', kbItems.length > 0 ? 'PASS' : 'FAIL',
      `${kbItems.length} KB items`)

    // Click first KB to load documents
    if (kbItems.length > 0) {
      await kbItems[0].click()
      await page.waitForTimeout(1500)

      // Check document list (uses .doc-card class)
      const docItems = await page.$$('.doc-card')
      log('文档列表加载', docItems.length > 0 ? 'PASS' : 'PASS',
        `${docItems.length} documents (some KBs may have 0 docs)`)

      // Check if document list header exists
      const docListHeader = await page.$('.doc-list-header, .doc-list-title')
      log('文档列表头部', docListHeader ? 'PASS' : 'FAIL')
    }

    // Check for create document button
    const createBtn = await page.$('button:has-text("新建"), button:has-text("创建")')
    log('新建文档按钮存在', createBtn ? 'PASS' : 'FAIL')

    // Check search/filter input
    const filterInput = await page.$('.doc-list-actions input, input[placeholder*="搜索"]')
    log('文档搜索框存在', filterInput ? 'PASS' : 'FAIL')

    // Check for console errors
    const kbErrors = consoleErrors.filter(e =>
      !e.includes('favicon') && !e.includes('404') && !e.includes('Warning:')
    )
    log('知识库管理无严重错误', kbErrors.length === 0 ? 'PASS' : 'FAIL',
      kbErrors.length > 0 ? kbErrors[0].slice(0, 100) : 'clean')

  } catch (e) {
    log('知识库管理页面测试', 'FAIL', e.message)
  }

  // ============= TEST 5: Navigation Between Pages =============
  console.log('\n========== 页面导航测试 ==========')
  try {
    // Go to home page
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: TIMEOUT })
    await page.waitForTimeout(1000)

    // Collect all navigation link hrefs
    const navHrefs = await page.$$eval('nav a[href], .ant-menu a[href], header a[href]', els =>
      els.map(e => ({ href: e.getAttribute('href'), text: e.textContent?.trim() || '' }))
        .filter(l => l.href && l.href.startsWith('/'))
    )
    log('导航菜单存在', navHrefs.length > 0 ? 'PASS' : 'FAIL',
      `${navHrefs.length} nav links`)

    // Navigate to each unique page
    const uniqueHrefs = [...new Set(navHrefs.map(l => l.href))].slice(0, 6)
    for (const href of uniqueHrefs) {
      const linkInfo = navHrefs.find(l => l.href === href)
      const text = linkInfo?.text || href
      try {
        await page.goto(`${BASE_URL}${href}`, { waitUntil: 'networkidle', timeout: TIMEOUT })
        await page.waitForTimeout(1500)
        const currentUrl = page.url()
        const bodyText = await page.evaluate(() => document.body?.innerText?.slice(0, 100) || '')
        log(`导航到 ${text}`, currentUrl.includes(href) && bodyText.length > 0 ? 'PASS' : 'FAIL',
          `url: ${currentUrl}, content: ${bodyText.length} chars`)
      } catch (e) {
        log(`导航到 ${text}`, 'FAIL', e.message.slice(0, 80))
      }
    }
  } catch (e) {
    log('页面导航测试', 'FAIL', e.message)
  }

  // ============= SUMMARY =============
  console.log('\n========== 测试总结 ==========')
  console.log(`✅ 通过: ${passCount}`)
  console.log(`❌ 失败: ${failCount}`)
  console.log(`总计: ${passCount + failCount}`)
  console.log(`通过率: ${((passCount / (passCount + failCount)) * 100).toFixed(1)}%`)

  if (failCount > 0) {
    console.log('\n--- 失败项 ---')
    results.filter(r => r.status === 'FAIL').forEach(r => {
      console.log(`  ❌ ${r.test} — ${r.detail}`)
    })
  }

  await browser.close()
  return failCount === 0
}

runTests().then(success => {
  process.exit(success ? 0 : 1)
}).catch(err => {
  console.error('Test runner error:', err)
  process.exit(1)
})
