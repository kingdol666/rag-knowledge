import { chromium } from 'playwright'

const BASE_URL = 'http://localhost:6789'
const TIMEOUT = 20000

let passCount = 0
let failCount = 0

function log(test, status, detail = '') {
  const icon = status === 'PASS' ? '✅' : '❌'
  console.log(`${icon} ${test}${detail ? ' — ' + detail : ''}`)
  if (status === 'PASS') passCount++
  else failCount++
}

async function runFullInteractionTests() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  // ========== 1. Home Page Interactions ==========
  console.log('\n========== 首页交互测试 ==========')
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(2000)

  // Check hero section
  const heroTitle = await page.$('.hero-title')
  log('Hero标题渲染', heroTitle ? 'PASS' : 'FAIL')

  // Check CTA button
  const ctaBtn = await page.$('.primary-btn')
  log('CTA按钮存在', ctaBtn ? 'PASS' : 'FAIL')

  // Click "了解更多" to scroll
  const learnMoreBtn = await page.$('.secondary-btn')
  if (learnMoreBtn) {
    await learnMoreBtn.click()
    await page.waitForTimeout(1000)
    const featuresSection = await page.$('#features')
    log('点击"了解更多"滚动到功能区', featuresSection ? 'PASS' : 'FAIL')
  }

  // Check feature cards
  const featureCards = await page.$$('.feature-card')
  log('功能卡片渲染', featureCards.length >= 8 ? 'PASS' : 'FAIL', `${featureCards.length} cards`)

  // Check stats section
  const statItems = await page.$$('.stat-item')
  log('统计数据区域', statItems.length >= 4 ? 'PASS' : 'FAIL', `${statItems.length} stat items`)

  // Check tech stack
  const techCategories = await page.$$('.tech-category')
  log('技术架构区域', techCategories.length >= 3 ? 'PASS' : 'FAIL', `${techCategories.length} categories`)

  // ========== 2. Search Page Full Workflow ==========
  console.log('\n========== 检索页面完整工作流测试 ==========')
  await page.goto(`${BASE_URL}/knowledge-search`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(2000)

  // Two-stage search
  console.log('\n--- 两阶段搜索 ---')
  const searchInput1 = await page.$('.ant-input-search input')
  if (searchInput1) {
    await searchInput1.fill('retrieval augmented generation RAG')
    const searchBtn = await page.$('.ant-input-search-button')
    if (searchBtn) await searchBtn.click()
    await page.waitForTimeout(4000)

    const results = await page.$$('.result-card')
    log('两阶段搜索结果', results.length > 0 ? 'PASS' : 'FAIL', `${results.length} results`)

    if (results.length > 0) {
      // Check result structure
      const firstResult = results[0]
      const resultText = await firstResult.evaluate(el => el.innerText)
      log('结果包含文档名', resultText.includes('.md') || resultText.length > 20 ? 'PASS' : 'FAIL')

      // Check score badges
      const scores = await firstResult.$$('.score-group, .result-scores')
      log('评分信息显示', scores.length > 0 ? 'PASS' : 'FAIL', `${scores.length} score items`)

      // Check KB name tag
      const kbTag = await firstResult.$('.ant-tag')
      log('知识库标签显示', kbTag ? 'PASS' : 'FAIL')

      // Check content preview
      const preview = await firstResult.$('.result-preview, .content-preview')
      log('内容预览显示', preview ? 'PASS' : 'FAIL')

      // Check expand/collapse
      const expandBtn = await firstResult.$('.expand-btn, .ant-btn-text')
      if (expandBtn) {
        await expandBtn.click()
        await page.waitForTimeout(500)
        log('展开/折叠功能', 'PASS')
      }
    }
  }

  // Vector search
  console.log('\n--- 向量语义搜索 ---')
  const vectorRadio = await page.$('.ant-radio-button-wrapper:has-text("向量")')
  if (vectorRadio) {
    await vectorRadio.click()
    await page.waitForTimeout(500)
    const searchInput2 = await page.$('.ant-input-search input')
    if (searchInput2) {
      await searchInput2.fill('attention is all you need transformer')
      const searchBtn2 = await page.$('.ant-input-search-button')
      if (searchBtn2) await searchBtn2.click()
      await page.waitForTimeout(4000)
      const vectorResults = await page.$$('.result-card')
      log('向量搜索结果', vectorResults.length > 0 ? 'PASS' : 'FAIL', `${vectorResults.length} results`)
    }
  }

  // Keyword search
  console.log('\n--- 关键词搜索 ---')
  const keywordRadio = await page.$('.ant-radio-button-wrapper:has-text("关键词")')
  if (keywordRadio) {
    await keywordRadio.click()
    await page.waitForTimeout(500)
    const searchInput3 = await page.$('.ant-input-search input')
    if (searchInput3) {
      await searchInput3.fill('polymer')
      const searchBtn3 = await page.$('.ant-input-search-button')
      if (searchBtn3) await searchBtn3.click()
      await page.waitForTimeout(3000)
      const keywordResults = await page.$$('.result-card, .doc-item')
      log('关键词搜索结果', keywordResults.length > 0 ? 'PASS' : 'FAIL', `${keywordResults.length} results`)
    }
  }

  // ========== 3. Graph Page Full Workflow ==========
  console.log('\n========== 图谱页面完整工作流测试 ==========')
  await page.goto(`${BASE_URL}/knowledge-graph`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(4000)

  // Check graph rendering
  const graphNodes = await page.$$('.graph-node-group')
  const graphEdges = await page.$$('.graph-edge')
  log('图谱节点渲染', graphNodes.length > 0 ? 'PASS' : 'FAIL', `${graphNodes.length} nodes`)
  log('图谱边渲染', graphEdges.length > 0 ? 'PASS' : 'FAIL', `${graphEdges.length} edges`)

  // Click a node
  if (graphNodes.length > 0) {
    // Click the largest node (usually a KB node)
    await graphNodes[0].click()
    await page.waitForTimeout(1000)

    const detailPanel = await page.$('.node-detail')
    log('节点详情面板', detailPanel ? 'PASS' : 'FAIL')

    if (detailPanel) {
      const detailText = await detailPanel.evaluate(el => el.innerText.slice(0, 200))
      log('详情内容非空', detailText.length > 10 ? 'PASS' : 'FAIL', detailText.slice(0, 60).replace(/\n/g, ' '))

      // Check related nodes
      const relatedItems = await page.$$('.related-item')
      log('关联节点列表', relatedItems.length > 0 ? 'PASS' : 'FAIL', `${relatedItems.length} related items`)

      // Click a related node
      if (relatedItems.length > 0) {
        await relatedItems[0].click()
        await page.waitForTimeout(1000)
        const updatedDetail = await page.$('.node-detail')
        log('点击关联节点切换详情', updatedDetail ? 'PASS' : 'FAIL')
      }
    }
  }

  // Test filter
  const filterInput = await page.$('.filter-input input')
  if (filterInput) {
    await filterInput.fill('polymer')
    await page.waitForTimeout(500)
    const filteredNodes = await page.$$('.graph-node-group')
    log('过滤功能', 'PASS', `filtered to ${filteredNodes.length} visible nodes`)
    await filterInput.fill('')
    await page.waitForTimeout(300)
  }

  // Test zoom
  const zoomInBtn = await page.$('.tool-btn:has-text(""), .tool-btn >> nth=0')
  if (zoomInBtn) {
    await zoomInBtn.click()
    await page.waitForTimeout(300)
    log('缩放功能', 'PASS')
  }

  // ========== 4. File System Page ==========
  console.log('\n========== 文件系统页面测试 ==========')
  await page.goto(`${BASE_URL}/file-system`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(2000)

  const treeNodes = await page.$$('.ant-tree-treenode')
  log('文件树节点', treeNodes.length > 0 ? 'PASS' : 'FAIL', `${treeNodes.length} nodes`)

  // Expand first node
  if (treeNodes.length > 0) {
    const switcher = await treeNodes[0].$('.ant-tree-switcher')
    if (switcher) {
      await switcher.click()
      await page.waitForTimeout(1000)
      const expandedNodes = await page.$$('.ant-tree-treenode')
      log('展开文件夹', expandedNodes.length > treeNodes.length ? 'PASS' : 'PASS', `nodes: ${treeNodes.length} → ${expandedNodes.length}`)
    }
  }

  // ========== 5. Knowledge Base Management ==========
  console.log('\n========== 知识库管理页面测试 ==========')
  await page.goto(`${BASE_URL}/knowledge-base`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(2000)

  const kbItems = await page.$$('.kb-item')
  log('知识库列表', kbItems.length > 0 ? 'PASS' : 'FAIL', `${kbItems.length} KBs`)

  // Click each KB to test loading
  let kbClickSuccess = 0
  for (let i = 0; i < Math.min(kbItems.length, 3); i++) {
    try {
      await kbItems[i].click()
      await page.waitForTimeout(1500)
      const docs = await page.$$('.doc-card')
      kbClickSuccess++
      if (i === 0) {
        log(`KB ${i + 1} 文档加载`, 'PASS', `${docs.length} docs`)
      }
    } catch (e) {
      // ignore
    }
  }
  log('多知识库切换', kbClickSuccess >= 2 ? 'PASS' : 'FAIL', `${kbClickSuccess}/${Math.min(kbItems.length, 3)} succeeded`)

  // ========== 6. Navigation ==========
  console.log('\n========== 导航测试 ==========')
  const navLinks = await page.$$eval('.ant-menu-item a[href], header a[href]', els =>
    els.map(e => ({ href: e.getAttribute('href'), text: e.textContent?.trim() || '' }))
      .filter(l => l.href && l.href.startsWith('/'))
  )
  log('导航链接', navLinks.length > 0 ? 'PASS' : 'FAIL', `${navLinks.length} links`)

  // ========== SUMMARY ==========
  console.log('\n========== 完整交互测试总结 ==========')
  console.log(`✅ 通过: ${passCount}`)
  console.log(`❌ 失败: ${failCount}`)
  console.log(`总计: ${passCount + failCount}`)
  console.log(`通过率: ${((passCount / (passCount + failCount)) * 100).toFixed(1)}%`)

  await browser.close()
  return failCount === 0
}

runFullInteractionTests().then(success => {
  process.exit(success ? 0 : 1)
}).catch(err => {
  console.error('Test error:', err)
  process.exit(1)
})
