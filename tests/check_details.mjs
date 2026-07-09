import { chromium } from 'playwright'

const BASE_URL = 'http://localhost:6789'
const TIMEOUT = 15000

async function checkSvgDetails() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  // Check graph page SVG details
  await page.goto(`${BASE_URL}/knowledge-graph`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(3000)

  const svgInfo = await page.evaluate(() => {
    const svgs = Array.from(document.querySelectorAll('svg'))
    return svgs.map(svg => ({
      width: svg.getAttribute('width') || svg.style.width || getComputedStyle(svg).width,
      height: svg.getAttribute('height') || svg.style.height || getComputedStyle(svg).height,
      viewBox: svg.getAttribute('viewBox'),
      classes: svg.className?.baseVal || svg.className || '',
      parentId: svg.parentElement?.id || svg.parentElement?.className?.baseVal || '',
      childCount: svg.children.length,
    }))
  })
  
  console.log('SVG elements on graph page:')
  svgInfo.forEach((s, i) => {
    console.log(`  SVG ${i}: ${s.width}x${s.height}, viewBox=${s.viewBox}, classes="${s.classes}", parent="${s.parentId}", children=${s.childCount}`)
  })

  // Check home page structure
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(1500)
  
  const homeStructure = await page.evaluate(() => {
    const main = document.querySelector('.ant-layout-content, main')
    if (!main) return { found: false }
    
    const sections = main.querySelectorAll(':scope > *')
    return {
      found: true,
      mainClass: main.className,
      sectionCount: sections.length,
      sections: Array.from(sections).map(s => ({
        tag: s.tagName,
        class: s.className?.baseVal || s.className || '',
        text: s.innerText?.slice(0, 80)?.replace(/\n/g, ' ') || '',
      })),
    }
  })
  
  console.log('\nHome page main content structure:')
  console.log(`  Found: ${homeStructure.found}`)
  if (homeStructure.found) {
    console.log(`  Main class: "${homeStructure.mainClass}"`)
    console.log(`  Sections: ${homeStructure.sectionCount}`)
    homeStructure.sections.forEach((s, i) => {
      console.log(`  [${i}] <${s.tag}> class="${s.class}" text="${s.text}"`)
    })
  }

  // Check search page structure  
  await page.goto(`${BASE_URL}/knowledge-search`, { waitUntil: 'networkidle', timeout: TIMEOUT })
  await page.waitForTimeout(1500)

  const searchStructure = await page.evaluate(() => {
    const main = document.querySelector('.ant-layout-content, main')
    if (!main) return { found: false }
    const sections = main.querySelectorAll(':scope > *')
    return {
      found: true,
      sectionCount: sections.length,
      sections: Array.from(sections).map(s => ({
        tag: s.tagName,
        class: s.className?.baseVal || s.className || '',
        text: s.innerText?.slice(0, 80)?.replace(/\n/g, ' ') || '',
      })),
    }
  })

  console.log('\nSearch page main content structure:')
  console.log(`  Found: ${searchStructure.found}`)
  if (searchStructure.found) {
    console.log(`  Sections: ${searchStructure.sectionCount}`)
    searchStructure.sections.forEach((s, i) => {
      console.log(`  [${i}] <${s.tag}> class="${s.class}" text="${s.text}"`)
    })
  }

  await browser.close()
}

checkSvgDetails().catch(console.error)
