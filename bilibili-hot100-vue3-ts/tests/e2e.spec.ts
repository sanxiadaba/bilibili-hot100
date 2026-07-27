import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.video-card').first()).toBeVisible({ timeout: 30_000 })
})

test('列表分页、搜索与主题切换正常', async ({ page }) => {
  await expect(page).toHaveTitle('B站热门视频 TOP 100 - Vue3 + TS')
  await expect(page.locator('.video-card')).toHaveCount(24)
  await expect(page.getByLabel('视频分页')).toBeVisible()

  const title = (await page.locator('.video-card .title').first().textContent())?.trim()
  expect(title).toBeTruthy()
  await page.getByPlaceholder('搜索视频或UP主...').fill(title!)
  await expect(page.locator('.video-card')).toHaveCount(1)

  await page.getByLabel('切换到深色模式').click()
  await expect(page.locator('.app')).toHaveClass(/dark/)
  await page.getByLabel('切换到浅色模式').click()
  await expect(page.locator('.app')).not.toHaveClass(/dark/)
})

test('分析页图表和点赞 TOP 10 使用完整数据集', async ({ page }) => {
  const expectedTitles = await page.evaluate(async () => {
    const response = await fetch('/api/hot100')
    const payload = await response.json()
    return payload.data
      .slice()
      .sort((left: any, right: any) => right.stat.like - left.stat.like)
      .slice(0, 10)
      .map((video: any) => video.title)
  })

  await page.getByLabel('打开数据分析').click()
  await expect(page.locator('.stats-view')).toBeVisible()
  await expect(page.locator('.chart-container canvas')).toHaveCount(3)
  await page.getByLabel('查看点赞前十').click()
  await expect(page.locator('.detail-item')).toHaveCount(10)
  await expect(page.locator('.detail-title').allTextContents()).resolves.toEqual(expectedTitles)
})

test('图标按钮和视频卡片可以通过键盘操作', async ({ page }) => {
  await expect(page.getByLabel('刷新数据')).toBeVisible()
  await expect(page.getByLabel('查看日志')).toBeVisible()
  await expect(page.getByLabel('打开数据分析')).toBeVisible()

  const firstCard = page.locator('.video-card').first()
  await expect(firstCard).toHaveAttribute('tabindex', '0')
  await expect(firstCard).toHaveAttribute('role', 'link')
})

test('移动端没有横向溢出且首屏可见视频内容', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()
  await expect(page.locator('.video-card').first()).toBeVisible({ timeout: 30_000 })
  const metrics = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    firstCardTop: document.querySelector('.video-card')?.getBoundingClientRect().top ?? Infinity
  }))
  expect(metrics.documentWidth).toBeLessThanOrEqual(metrics.viewportWidth)
  expect(metrics.firstCardTop).toBeLessThan(844)
})
