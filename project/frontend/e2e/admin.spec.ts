import { test, expect, Page } from '@playwright/test';

/**
 * 超级管理员后台 E2E 测试
 *
 * 前置条件:
 *   1. 后端运行在 http://localhost:8001
 *   2. 前端运行在 http://localhost:3000
 *   3. 数据库已有种子数据（包含 superadmin / demo123456）
 */

async function loginAsSuperAdmin(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder(/用户名|username/i).fill('superadmin');
  await page.getByPlaceholder(/密码|password/i).fill('kst@2026');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await page.waitForURL(/\/admin/, { timeout: 15000 });
}

async function skipOnboarding(page: Page) {
  await page.evaluate(() => {
    localStorage.setItem('qianchui_onboarding_completed', 'true');
  });
}

// ═══════════════════════════════════════════════
// 1. 超管登录
// ═══════════════════════════════════════════════

test.describe('超管登录', () => {
  test('superadmin 登录后跳转到管理后台', async ({ page }) => {
    await skipOnboarding(page);
    await loginAsSuperAdmin(page);
    await expect(page).toHaveURL(/\/admin/);
  });

  test('普通用户不能访问管理后台', async ({ page }) => {
    await skipOnboarding(page);
    await page.goto('/login');
    await page.getByPlaceholder(/用户名|username/i).fill('demo');
    await page.getByPlaceholder(/密码|password/i).fill('demo123456');
    await page.getByRole('button', { name: /登录|login/i }).click();
    await page.waitForURL(/\/(chat|dashboard)/, { timeout: 15000 });
    await page.goto('/admin');
    await expect(page).not.toHaveURL(/\/admin$/);
  });
});

// ═══════════════════════════════════════════════
// 2. 数据总览页
// ═══════════════════════════════════════════════

test.describe('数据总览', () => {
  test.beforeEach(async ({ page }) => {
    await skipOnboarding(page);
    await loginAsSuperAdmin(page);
  });

  test('总览页面正常加载并显示数据卡片', async ({ page }) => {
    await expect(page.locator('text=/系统数据总览|数据总览/i').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/企业总数/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/用户总数/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/话术总量/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/对话总量/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('总览页面显示增长趋势图', async ({ page }) => {
    await expect(page.locator('text=/增长趋势/i').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/7天|14天|30天/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('可切换趋势图时间范围', async ({ page }) => {
    await page.waitForSelector('text=/增长趋势/i', { timeout: 15000 });
    const btn7 = page.locator('button').filter({ hasText: /^7天$/ }).first();
    if (await btn7.isVisible()) {
      await btn7.click();
      await page.waitForTimeout(1000);
    }
  });

  test('总览页面显示培训/演练/诊断/物料卡片', async ({ page }) => {
    await expect(page.locator('text=/培训记录/i').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/演练次数/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/诊断报告/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/渠道物料/i').first()).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 3. 企业管理
// ═══════════════════════════════════════════════

test.describe('企业管理', () => {
  test.beforeEach(async ({ page }) => {
    await skipOnboarding(page);
    await loginAsSuperAdmin(page);
    await page.goto('/admin/enterprises');
  });

  test('企业管理页面正常加载', async ({ page }) => {
    await expect(page.locator('text=/企业管理/i').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/新增企业/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('企业列表显示数据', async ({ page }) => {
    await expect(page.locator('table').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/企业名称|企业/').first()).toBeVisible({ timeout: 10000 });
  });

  test('搜索企业', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="搜索"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill('千锤');
    await page.waitForTimeout(1000);
  });

  test('新增企业弹窗', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /新增企业/ }).first();
    await addBtn.click();
    await expect(page.locator('text=/企业名称/').nth(1)).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/所属行业/').first()).toBeVisible({ timeout: 5000 });

    const cancelBtn = page.locator('button').filter({ hasText: /取消|cancel/i }).first();
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click();
    }
  });
});

// ═══════════════════════════════════════════════
// 4. 账号管理
// ═══════════════════════════════════════════════

test.describe('账号管理', () => {
  test.beforeEach(async ({ page }) => {
    await skipOnboarding(page);
    await loginAsSuperAdmin(page);
    await page.goto('/admin/accounts');
  });

  test('账号管理页面正常加载', async ({ page }) => {
    await expect(page.locator('text=/账号管理/i').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/新增账号/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('账号列表显示数据', async ({ page }) => {
    await expect(page.locator('table').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/superadmin/').first()).toBeVisible({ timeout: 10000 });
  });

  test('角色筛选下拉可用', async ({ page }) => {
    const roleSelect = page.locator('select').first();
    await expect(roleSelect).toBeVisible({ timeout: 10000 });
  });

  test('搜索账号', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="搜索"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill('superadmin');
    await page.waitForTimeout(1000);
    await expect(page.locator('text=/superadmin/').first()).toBeVisible({ timeout: 10000 });
  });

  test('新增账号弹窗', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /新增账号/ }).first();
    await addBtn.click();
    await expect(page.locator('text=/用户名/').nth(1)).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/邮箱/').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/密码/').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/角色/').first()).toBeVisible({ timeout: 5000 });

    const cancelBtn = page.locator('button').filter({ hasText: /取消|cancel/i }).first();
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click();
    }
  });

  test('账号列表显示角色标签', async ({ page }) => {
    await expect(
      page.locator('text=/super_admin|admin|manager|staff/').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 5. 数据查询
// ═══════════════════════════════════════════════

test.describe('数据查询', () => {
  test.beforeEach(async ({ page }) => {
    await skipOnboarding(page);
    await loginAsSuperAdmin(page);
    await page.goto('/admin/query');
  });

  test('数据查询页面正常加载', async ({ page }) => {
    await expect(page.locator('text=/数据查询/i').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=/有什么想了解的/').first()).toBeVisible({ timeout: 10000 });
  });

  test('显示快捷问题按钮', async ({ page }) => {
    await expect(page.locator('text=/系统总览/').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/昨天新增多少企业/').first()).toBeVisible({ timeout: 10000 });
  });

  test('点击快捷问题发送查询', async ({ page }) => {
    const quickBtn = page.locator('button').filter({ hasText: /系统总览/ }).first();
    await quickBtn.click();
    await expect(page.locator('text=/企业|用户|话术|对话/').first()).toBeVisible({ timeout: 15000 });
  });

  test('输入框发送自定义问题', async ({ page }) => {
    const input = page.locator('input[placeholder*="输入"]').first();
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill('一共有多少用户');
    const sendBtn = page.locator('button').filter({ has: page.locator('svg.lucide-send') }).first();
    await sendBtn.click();
    await expect(page.locator('text=/用户/').first()).toBeVisible({ timeout: 15000 });
  });
});

// ═══════════════════════════════════════════════
// 6. 超管侧边栏导航
// ═══════════════════════════════════════════════

test.describe('超管侧边栏', () => {
  test.beforeEach(async ({ page }) => {
    await skipOnboarding(page);
    await loginAsSuperAdmin(page);
  });

  test('侧边栏包含所有导航项', async ({ page }) => {
    const navTexts = ['数据总览', '企业管理', '账号管理', '数据查询'];
    for (const text of navTexts) {
      await expect(page.locator(`text=${text}`).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('侧边栏显示返回前台链接', async ({ page }) => {
    await expect(page.locator('text=/返回前台/').first()).toBeVisible({ timeout: 10000 });
  });

  test('点击导航切换页面', async ({ page }) => {
    const navItems = [
      { text: '企业管理', url: '/admin/enterprises' },
      { text: '账号管理', url: '/admin/accounts' },
      { text: '数据查询', url: '/admin/query' },
      { text: '数据总览', url: '/admin' },
    ];
    for (const item of navItems) {
      const link = page.locator('a').filter({ hasText: item.text }).first();
      if (await link.isVisible()) {
        await link.click();
        await page.waitForTimeout(500);
        await expect(page).toHaveURL(new RegExp(item.url));
      }
    }
  });

  test('返回前台跳转到主应用', async ({ page }) => {
    const backLink = page.locator('a').filter({ hasText: /返回前台/ }).first();
    if (await backLink.isVisible()) {
      await backLink.click();
      await page.waitForTimeout(1000);
      await expect(page).toHaveURL(/\/(chat|dashboard)/);
    }
  });
});

// ═══════════════════════════════════════════════
// 7. 全流程集成：总览→企业→账号→查询
// ═══════════════════════════════════════════════

test.describe('全流程集成', () => {
  test('从总览页导航到所有子页面', async ({ page }) => {
    await skipOnboarding(page);
    await loginAsSuperAdmin(page);

    // 总览页加载
    await expect(page.locator('text=/系统数据总览|数据总览/').first()).toBeVisible({ timeout: 15000 });

    // 切换到企业管理
    await page.locator('a').filter({ hasText: '企业管理' }).first().click();
    await expect(page.locator('text=/企业管理/').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('table').first()).toBeVisible({ timeout: 10000 });

    // 切换到账号管理
    await page.locator('a').filter({ hasText: '账号管理' }).first().click();
    await expect(page.locator('text=/账号管理/').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('table').first()).toBeVisible({ timeout: 10000 });

    // 切换到数据查询
    await page.locator('a').filter({ hasText: '数据查询' }).first().click();
    await expect(page.locator('text=/数据查询/').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/有什么想了解的/').first()).toBeVisible({ timeout: 10000 });

    // 返回总览
    await page.locator('a').filter({ hasText: '数据总览' }).first().click();
    await expect(page.locator('text=/系统数据总览|数据总览/').first()).toBeVisible({ timeout: 10000 });
  });
});
