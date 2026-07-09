import { chromium } from 'playwright'

const BASE_URL = 'http://localhost:6789'
const TIMEOUT = 15000

async function visualCheck() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  const issues = []

  // ========== Home Page ==========
  console.log('\n========== 首页视觉检查 ==========')
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(1500)

  // Check header
  const header = await page.$('header, .ant-layout-header')
  console.log(header ? '✅ Header存在' : '❌ Header缺失')

  // Check logo/title
  const logo = await page.$('.logo, .ant-layout-header .logo, header img, header .title')
  console.log(logo ? '✅ Logo存在' : '⚠️ Logo未检测到')

  // Check navigation menu
  const menuItems = await page.$$('.ant-menu-item, .ant-menu-submenu')
  console.log(`✅ 导航菜单项: ${menuItems.length}个`)

  // Check footer
  const footer = await page.$('footer, .ant-layout-footer')
  console.log(footer ? '✅ Footer存在' : '⚠️ Footer未检测到')

  // Check main content area
  const content = await page.$('.ant-layout-content, main, .ant-card')
  console.log(content ? '✅ 主内容区域存在' : '❌ 主内容区域缺失')

  // Check hero section or dashboard cards
  const cards = await page.$$('.ant-card')
  console.log(`✅ 卡片组件: ${cards.length}个`)

  // Check buttons
  const buttons = await page.$$('button, .ant-btn')
  console.log(`✅ 按钮组件: ${buttons.length}个`)

  // Check for broken images
  const brokenImages = await page.evaluate(() => {
    const imgs = Array.from(document.querySelectorAll('img'))
    return imgs.filter(img => !img.complete || img.naturalWidth === 0).length
  })
  console.log(brokenImages === 0 ? '✅ 无破损图片' : `❌ ${brokenImages}个破损图片`)

  // ========== Knowledge Search Page ==========
  console.log('\n========== 检索页面视觉检查 ==========')
  await page.goto(`${BASE_URL}/knowledge-search`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(1500)

  // Check page layout
  const searchLayout = await page.$('.search-page, .knowledge-search, .ant-layout-content')
  console.log(searchLayout ? '✅ 检索页面布局存在' : '❌ 检索页面布局缺失')

  // Check search mode tabs
  const radioGroup = await page.$('.ant-radio-group')
  console.log(radioGroup ? '✅ 检索模式切换存在' : '❌ 检索模式切换缺失')

  // Check search input area
  const searchArea = await page.$('.ant-input-search, .ant-input-affix-wrapper')
  console.log(searchArea ? '✅ 搜索框存在' : '❌ 搜索框缺失')

  // Check KB catalog section
  const kbCatalog = await page.$$('.kb-catalog, .kb-card-container, .kb-section')
  console.log(kbCatalog.length > 0 ? `✅ 知识库目录区域: ${kbCatalog.length}个` : '⚠️ 知识库目录区域未检测到')

  // Check stats/info area
  const statBadges = await page.$$('.ant-statistic, .stat-card, .info-badge')
  console.log(`✅ 统计/信息区域: ${statBadges.length}个`)

  // Check for styling issues (overflow, hidden content)
  const overflowIssues = await page.evaluate(() => {
    const els = document.querySelectorAll('*')
    let issues = 0
    for (const el of els) {
      if (el.scrollWidth > el.clientWidth + 5 && el.clientWidth > 100) {
        issues++
      }
    }
    return issues
  })
  console.log(overflowIssues < 5 ? '✅ 无明显溢出问题' : `⚠️ ${overflowIssues}个可能的溢出元素`)

  // ========== Knowledge Graph Page ==========
  console.log('\n========== 图谱页面视觉检查 ==========')
  await page.goto(`${BASE_URL}/knowledge-graph`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(3000)

  // Check graph container
  const graphContainer = await page.$('.graph-container, .graph-wrapper, .graph-svg-container')
  console.log(graphContainer ? '✅ 图谱容器存在' : '❌ 图谱容器缺失')

  // Check SVG
  const svg = await page.$('svg')
  if (svg) {
    const svgBox = await svg.boundingBox()
    console.log(`✅ SVG画布: ${svgBox?.width}x${svgBox?.height}`)
  } else {
    console.log('❌ SVG画布缺失')
  }

  // Check nodes and edges
  const nodes = await page.$$('.graph-node-group, .graph-node')
  const edges = await page.$$('.graph-edge, .graph-link')
  console.log(`✅ 图谱节点: ${nodes.length}个, 边: ${edges.length}条`)

  // Check stat cards
  const graphStatCards = await page.$$('.stat-card')
  console.log(`✅ 统计卡片: ${graphStatCards.length}个`)

  // Check legend
  const legend = await page.$$('.legend, .legend-item, .graph-legend')
  console.log(`✅ 图例: ${legend.length}个`)

  // Check toolbar
  const toolbar = await page.$$('.graph-toolbar, .tool-btn, .toolbar')
  console.log(`✅ 工具栏: ${toolbar.length}个`)

  // Check detail panel
  const detailPanel = await page.$('.detail-panel, .node-detail, .graph-detail')
  console.log(detailPanel ? '✅ 详情面板存在' : '✅ 详情面板（未选中状态）')

  // Check filter area
  const filterArea = await page.$('.filter-area, .filter-section, .graph-filter')
  console.log(filterArea ? '✅ 过滤区域存在' : '⚠️ 过滤区域未检测到')

  // ========== File System Page ==========
  console.log('\n========== 文件系统页面视觉检查 ==========')
  await page.goto(`${BASE_URL}/file-system`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(2000)

  const treeNodes = await page.$$('.ant-tree-treenode, .tree-node')
  console.log(`✅ 文件树节点: ${treeNodes.length}个`)

  const treeContainer = await page.$('.ant-tree, .file-tree, .tree-container')
  console.log(treeContainer ? '✅ 文件树容器存在' : '❌ 文件树容器缺失')

  // ========== Knowledge Base Page ==========
  console.log('\n========== 知识库管理页面视觉检查 ==========')
  await page.goto(`${BASE_URL}/knowledge-base`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(2000)

  const kbItems = await page.$$('.kb-item, .kb-list-item')
  console.log(`✅ 知识库列表: ${kbItems.length}个`)

  // Click first KB
  if (kbItems.length > 0) {
    await kbItems[0].click()
    await page.waitForTimeout(1500)

    const docCards = await page.$$('.doc-card, .document-item')
    console.log(`✅ 文档列表: ${docCards.length}个`)

    // Check document metadata
    if (docCards.length > 0) {
      const docText = await docCards[0].evaluate(el => el.innerText.slice(0, 100))
      console.log(`✅ 文档内容: ${docText.replace(/\n/g, ' ').slice(0, 60)}...`)
    }
  }

  // Check layout split
  const splitPanel = await page.$('.ant-row, .split-pane, .kb-layout')
  console.log(splitPanel ? '✅ 分栏布局存在' : '⚠️ 分栏布局未检测到')

  // ========== Responsive Check ==========
  console.log('\n========== 响应式检查 ==========')
  await page.setViewportSize({ width: 768, height: 1024 })
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(1000)

  const mobileMenu = await page.$('.ant-menu-mobile, .ant-drawer, .ant-menu-horizontal')
  const bodyWidth = await page.evaluate(() => document.body?.clientWidth || 0)
  console.log(`✅ 移动端视口: ${bodyWidth}px`)
  console.log(mobileMenu ? '✅ 移动端菜单适配' : '⚠️ 移动端菜单可能需要优化')

  // Check horizontal scroll on mobile
  const horizontalScroll = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth
  })
  console.log(horizontalScroll ? '⚠️ 移动端有水平滚动条' : '✅ 移动端无水平滚动')

  await browser.close()
  console.log('\n========== 视觉检查完成 ==========')
}

visualCheck().catch(console.error)
