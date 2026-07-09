import { chromium } from 'playwright'

const BASE_URL = 'http://localhost:6789'
const SCREENSHOT_DIR = './tests/screenshots'

async function takeScreenshots() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  const pages = [
    { name: 'home', url: BASE_URL },
    { name: 'knowledge-search', url: `${BASE_URL}/knowledge-search` },
    { name: 'knowledge-graph', url: `${BASE_URL}/knowledge-graph` },
    { name: 'file-system', url: `${BASE_URL}/file-system` },
    { name: 'knowledge-base', url: `${BASE_URL}/knowledge-base` },
  ]

  for (const p of pages) {
    try {
      await page.goto(p.url, { waitUntil: 'networkidle', timeout: 20000 })
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/${p.name}.png`, fullPage: true })
      console.log(`✅ Screenshot: ${p.name}.png`)
    } catch (e) {
      console.log(`❌ Failed: ${p.name} — ${e.message}`)
    }
  }

  // Take a search results screenshot
  try {
    await page.goto(`${BASE_URL}/knowledge-search`, { waitUntil: 'networkidle', timeout: 20000 })
    await page.waitForTimeout(1500)
    const searchInput = await page.$('.ant-input-search input')
    if (searchInput) {
      await searchInput.fill('RAG retrieval augmented generation')
      const searchBtn = await page.$('.ant-input-search-button')
      if (searchBtn) await searchBtn.click()
      await page.waitForTimeout(3000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/search-results.png`, fullPage: true })
      console.log('✅ Screenshot: search-results.png')
    }
  } catch (e) {
    console.log(`❌ Failed: search-results — ${e.message}`)
  }

  // Take a graph node detail screenshot
  try {
    await page.goto(`${BASE_URL}/knowledge-graph`, { waitUntil: 'networkidle', timeout: 20000 })
    await page.waitForTimeout(3000)
    const graphNodes = await page.$$('.graph-node-group')
    if (graphNodes.length > 0) {
      await graphNodes[0].click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/graph-detail.png`, fullPage: true })
      console.log('✅ Screenshot: graph-detail.png')
    }
  } catch (e) {
    console.log(`❌ Failed: graph-detail — ${e.message}`)
  }

  await browser.close()
  console.log('\nDone!')
}

takeScreenshots().catch(console.error)
