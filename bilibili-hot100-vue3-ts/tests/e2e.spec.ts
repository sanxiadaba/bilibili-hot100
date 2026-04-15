import { test, expect } from '@playwright/test';

test.describe('B站热门视频 TOP 100 测试', () => {
  test.beforeEach(async ({ page }) => {
    // 导航到前端页面
    await page.goto('http://localhost:3004/');
  });

  test('页面加载正常，显示视频列表', async ({ page }) => {
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 检查页面标题
    await expect(page).toHaveTitle('B站热门视频 TOP 100 - Vue3 + TS');
    
    // 检查视频列表是否存在
    await expect(page.locator('.video-grid')).toBeVisible();
    
    // 检查是否有视频卡片
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(100);
  });

  test('数据分析页面可以访问', async ({ page }) => {
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 点击数据分析按钮
    await page.click('button:has-text("数据分析")');
    
    // 等待数据分析页面加载
    await page.waitForSelector('.stats-view');
    
    // 检查数据分析页面是否显示
    await expect(page.locator('.stats-view')).toBeVisible();
    
    // 检查数据概览是否存在
    await expect(page.locator('.stats-overview')).toBeVisible();
  });

  test('主题切换功能正常', async ({ page }) => {
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 检查初始主题（默认应该是浅色）
    await expect(page.locator('.app')).not.toHaveClass(/dark/);
    
    // 点击主题切换按钮
    await page.click('.theme-toggle');
    
    // 检查是否切换到深色主题
    await expect(page.locator('.app')).toHaveClass(/dark/);
    
    // 再次点击主题切换按钮
    await page.click('.theme-toggle');
    
    // 检查是否切换回浅色主题
    await expect(page.locator('.app')).not.toHaveClass(/dark/);
  });

  test('搜索功能正常', async ({ page }) => {
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 输入搜索关键词
    await page.fill('input[placeholder="搜索视频或UP主..."]', 'B站');
    
    // 等待搜索结果
    await page.waitForTimeout(1000);
    
    // 检查搜索结果是否存在
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCountGreaterThan(0);
  });

  test('分类筛选功能正常', async ({ page }) => {
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 点击分类标签
    const categoryTags = page.locator('.filter-tag');
    const firstCategory = categoryTags.nth(1); // 第一个是"全部"，第二个是第一个分类
    const categoryText = await firstCategory.textContent();
    
    if (categoryText) {
      await firstCategory.click();
      
      // 等待筛选结果
      await page.waitForTimeout(1000);
      
      // 检查筛选结果是否存在
      const videoCards = page.locator('.video-card');
      await expect(videoCards).toHaveCountGreaterThan(0);
    }
  });

  test('点赞最多 TOP 5 可以点击跳转', async ({ page }) => {
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 点击数据分析按钮
    await page.click('button:has-text("数据分析")');
    
    // 等待数据分析页面加载
    await page.waitForSelector('.top-liked');
    
    // 点击第一个视频
    const topItems = page.locator('.top-item');
    await topItems.nth(0).click();
    
    // 检查是否打开了新标签页
    const newPage = await page.context().waitForEvent('page');
    await newPage.waitForLoadState('networkidle');
    
    // 检查新页面是否是B站视频页面
    await expect(newPage).toHaveURL(/https:\/\/www\.bilibili\.com\/video\//);
    
    // 关闭新页面
    await newPage.close();
  });

  test('页面性能测试', async ({ page }) => {
    // 导航到页面并测量性能
    const metrics = await page.evaluate(() => {
      return {
        loadTime: window.performance.timing.loadEventEnd - window.performance.timing.navigationStart,
        domContentLoaded: window.performance.timing.domContentLoadedEventEnd - window.performance.timing.navigationStart
      };
    });
    
    // 打印性能指标
    console.log('页面加载时间:', metrics.loadTime, 'ms');
    console.log('DOM加载时间:', metrics.domContentLoaded, 'ms');
    
    // 检查页面加载时间是否在合理范围内
    expect(metrics.loadTime).toBeLessThan(5000); // 5秒内加载完成
  });
});
