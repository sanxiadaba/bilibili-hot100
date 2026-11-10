import { expect, test } from '@playwright/test'

const rows = '.video-list .row'

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/')
  await expect(page.locator(rows).first()).toBeVisible({ timeout: 30_000 })
})

test('列表、搜索与主题切换', async ({ page }) => {
  await expect(page).toHaveTitle('B站热门视频 TOP 100')
  await expect(page.locator(rows)).toHaveCount(100)

  const title = (await page.locator(`${rows} .title`).first().textContent())?.trim()
  expect(title).toBeTruthy()
  await page.getByLabel('搜索视频或UP主').fill(title!)
  await expect(page.locator(rows)).toHaveCount(1)

  await page.getByLabel('搜索视频或UP主').fill('没有这个视频 xyz')
  await expect(page.locator(rows)).toHaveCount(0)

  const before = await page.locator('html').getAttribute('data-theme')
  await page.locator('button[aria-label^="切换到"]').click()
  await expect(page.locator('html')).not.toHaveAttribute('data-theme', before ?? 'light')
})

test('统计页的点赞 TOP 10 来自完整数据集', async ({ page }) => {
  const expected = await page.evaluate(async () => {
    const response = await fetch('/api/hot100')
    const payload = (await response.json()) as {
      data: Array<{ title: string; stat: { like: number } }>
    }
    return payload.data
      .slice()
      .sort((left, right) => right.stat.like - left.stat.like)
      .slice(0, 10)
      .map(video => video.title)
  })

  await page.getByLabel('打开数据分析').click()
  await expect(page.locator('.stats-view')).toBeVisible()
  await page.getByRole('tab', { name: '点赞' }).click()
  await expect(page.locator('.top-list li')).toHaveCount(10)
  await expect(page.locator('.top-line a')).toHaveText(expected)

  await page.getByLabel('返回列表').click()
  await expect(page.locator(rows).first()).toBeVisible()
})

test('视频行是可直接打开的链接，导出有下载地址', async ({ page }) => {
  const first = page.locator(rows).first()
  await expect(first).toHaveAttribute('href', /bilibili\.com\/video\/BV/)
  await expect(first).toHaveAttribute('target', '_blank')

  await expect(page.getByLabel('导出当前数据')).toHaveAttribute('href', '/api/export')
  await expect(page.getByLabel('刷新数据')).toBeVisible()
  await expect(page.getByLabel('查看日志')).toBeVisible()
})

test('日志面板能连上 WebSocket', async ({ page }) => {
  await page.getByLabel('查看日志').click()
  await expect(page.getByRole('dialog', { name: '后台日志' })).toBeVisible()
  await expect(page.getByText('已连接')).toBeVisible({ timeout: 10_000 })
  await page.getByLabel('关闭日志').click()
  await expect(page.getByRole('dialog', { name: '后台日志' })).toBeHidden()
})

test('390px 窄屏没有横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()
  await expect(page.locator(rows).first()).toBeVisible({ timeout: 30_000 })

  const metrics = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
    firstRowTop: document.querySelector('.video-list .row')?.getBoundingClientRect().top ?? Infinity
  }))
  expect(metrics.document).toBeLessThanOrEqual(metrics.viewport)
  expect(metrics.firstRowTop).toBeLessThan(844)
})
