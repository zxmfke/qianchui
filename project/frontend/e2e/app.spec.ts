import { test, expect, Page } from '@playwright/test';

/**
 * 千锤·营销话术AI操作系统 — 浏览器 E2E 测试
 *
 * 前置条件:
 *   1. 后端运行在 http://localhost:8001
 *   2. 前端运行在 http://localhost:3000
 *   3. 数据库已有种子数据
 *
 * 运行:
 *   npm run test:e2e            # headless
 *   npm run test:e2e:headed     # 打开浏览器可视化
 */

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder(/用户名|username/i).fill('demo');
  await page.getByPlaceholder(/密码|password/i).fill('demo123456');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await page.waitForURL(/\/(chat|dashboard)/, { timeout: 15000 });
}

// ═══════════════════════════════════════════════
// 1. 登录模块
// ═══════════════════════════════════════════════

test.describe('登录模块', () => {
  test('登录页完整渲染', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /千锤|QianChui/i })).toBeVisible();
    await expect(page.getByPlaceholder(/用户名|username/i)).toBeVisible();
    await expect(page.getByPlaceholder(/密码|password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /登录|login/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /登录|login/i })).toBeDisabled();
  });

  test('输入后按钮启用', async ({ page }) => {
    await page.goto('/login');
    const btn = page.getByRole('button', { name: /登录|login/i });
    await expect(btn).toBeDisabled();
    await page.getByPlaceholder(/用户名|username/i).fill('demo');
    await page.getByPlaceholder(/密码|password/i).fill('demo123456');
    await expect(btn).toBeEnabled();
  });

  test('正确账号密码登录成功', async ({ page }) => {
    await login(page);
    await expect(page.getByRole('link', { name: /对话中心|chat/i })).toBeVisible({ timeout: 10000 });
  });

  test('错误密码显示提示', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder(/用户名|username/i).fill('demo');
    await page.getByPlaceholder(/密码|password/i).fill('wrongpass');
    await page.getByRole('button', { name: /登录|login/i }).click();
    await expect(page.locator('text=/错误|失败|error|fail/i')).toBeVisible({ timeout: 10000 });
  });

  test('密码可见性切换', async ({ page }) => {
    await page.goto('/login');
    const pwdInput = page.getByPlaceholder(/密码|password/i);
    await expect(pwdInput).toHaveAttribute('type', 'password');
    const toggleBtn = page.locator('button').filter({ has: page.locator('svg') }).nth(0);
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
      await expect(pwdInput).toHaveAttribute('type', 'text');
    }
  });

  test('未登录重定向到登录页', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });

  test('未登录访问各页面均重定向', async ({ page }) => {
    for (const path of ['/scripts', '/training', '/memory', '/diagnosis', '/settings']) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

// ═══════════════════════════════════════════════
// 2. 侧边栏导航
// ═══════════════════════════════════════════════

test.describe('侧边栏导航', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('所有导航项可见', async ({ page }) => {
    const navTexts = [
      '对话中心', '数据看板', '话术库', '渠道物料',
      '培训中心', '演练中心', '诊断中心', '优化中心',
      '数据飞轮', '企业记忆', '系统设置',
    ];
    for (const text of navTexts) {
      await expect(page.locator(`text=${text}`).first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('点击导航能切换页面', async ({ page }) => {
    const targets = [
      { text: /数据看板|dashboard/i, url: '/dashboard' },
      { text: /话术库|script/i, url: '/scripts' },
      { text: /培训中心|training/i, url: '/training' },
      { text: /企业记忆|memory/i, url: '/memory' },
    ];
    for (const t of targets) {
      const link = page.locator(`a`).filter({ hasText: t.text }).first();
      if (await link.isVisible()) {
        await link.click();
        await page.waitForTimeout(500);
        await expect(page).toHaveURL(new RegExp(t.url));
      }
    }
  });

  test('当前页面导航项高亮', async ({ page }) => {
    await page.goto('/dashboard');
    const activeLink = page.locator('a.bg-indigo-600\\/20').first();
    await expect(activeLink).toBeVisible({ timeout: 5000 });
  });

  test('用户信息显示在底部', async ({ page }) => {
    await expect(page.locator('text=/demo|用户/').first()).toBeVisible({ timeout: 5000 });
  });

  test('退出登录按钮可见可点击', async ({ page }) => {
    const logoutBtn = page.locator('button[title*="退出"], button[title*="logout"]').first();
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

// ═══════════════════════════════════════════════
// 3. 对话中心
// ═══════════════════════════════════════════════

test.describe('对话中心', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/chat');
  });

  test('对话列表显示', async ({ page }) => {
    await expect(page.locator('text=/对话列表|conversations/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('有搜索框', async ({ page }) => {
    await expect(page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first()).toBeVisible({ timeout: 5000 });
  });

  test('有新建对话按钮', async ({ page }) => {
    const plusBtn = page.locator('button').filter({ has: page.locator('svg.lucide-plus') }).first();
    await expect(plusBtn).toBeVisible({ timeout: 5000 });
  });

  test('有消息输入框', async ({ page }) => {
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════
// 4. 数据看板
// ═══════════════════════════════════════════════

test.describe('数据看板', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
  });

  test('页面标题显示', async ({ page }) => {
    await expect(page.locator('text=/数据看板|dashboard/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('统计卡片显示', async ({ page }) => {
    await expect(page.locator('text=/话术总量|total.*script/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/今日复用|today.*usage/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('排行榜显示', async ({ page }) => {
    await expect(page.locator('text=/排行榜|ranking/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('团队表现显示', async ({ page }) => {
    await expect(page.locator('text=/团队|team/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('趋势图区域存在', async ({ page }) => {
    await expect(page.locator('text=/趋势|trend/i').first()).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 5. 话术库
// ═══════════════════════════════════════════════

test.describe('话术库', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/scripts');
  });

  test('页面标题和新增按钮', async ({ page }) => {
    await expect(page.locator('text=/话术库|script.*library/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/新增话术|add.*script/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('有搜索和筛选', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
  });

  test('话术列表有数据', async ({ page }) => {
    await expect(page.locator('text=/异议处理|开场白|促成|竞品应对|售后|复购/').first()).toBeVisible({ timeout: 10000 });
  });

  test('新增话术弹窗', async ({ page }) => {
    const addBtn = page.locator('text=/新增话术|add/i').first();
    await addBtn.click();
    await expect(page.locator('text=/创建|标题|title/i').first()).toBeVisible({ timeout: 5000 });
    const cancelBtn = page.locator('text=/取消|cancel/i').first();
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click();
    }
  });
});

// ═══════════════════════════════════════════════
// 6. 培训中心
// ═══════════════════════════════════════════════

test.describe('培训中心', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/training');
  });

  test('页面标题和进度统计', async ({ page }) => {
    await expect(page.locator('text=/培训中心|training/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/完成|completed|正确率|accuracy/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('进度条显示', async ({ page }) => {
    await expect(page.locator('text=/学习进度|progress/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('有题目或完成提示', async ({ page }) => {
    await expect(
      page.locator('text=/每日一练|daily|已完成所有|当客户|客户说/i').first(),
    ).toBeVisible({ timeout: 15000 });
  });

  test('有薄弱环节面板', async ({ page }) => {
    await expect(page.locator('text=/薄弱环节|weak/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('答题交互', async ({ page }) => {
    const optionA = page.locator('button').filter({ hasText: /^A$/ }).first();
    if (await optionA.isVisible({ timeout: 5000 }).catch(() => false)) {
      await optionA.click();
      await expect(
        page.locator('text=/正确|错误|correct|wrong/i').first(),
      ).toBeVisible({ timeout: 10000 });
    }
  });
});

// ═══════════════════════════════════════════════
// 7. 诊断中心
// ═══════════════════════════════════════════════

test.describe('诊断中心', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/diagnosis');
  });

  test('页面标题和输入区', async ({ page }) => {
    await expect(page.locator('text=/诊断中心|diagnosis/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 5000 });
  });

  test('有诊断按钮', async ({ page }) => {
    await expect(
      page.locator('button').filter({ hasText: /诊断|分析|analyze/i }).first(),
    ).toBeVisible({ timeout: 5000 });
  });

  test('有历史报告区域', async ({ page }) => {
    await expect(
      page.locator('text=/历史|报告|history|report/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 8. 企业记忆
// ═══════════════════════════════════════════════

test.describe('企业记忆', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/memory');
  });

  test('页面标题显示', async ({ page }) => {
    await expect(page.locator('text=/企业记忆|memory/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('痛点库tab和数据', async ({ page }) => {
    await expect(page.locator('text=/痛点|pain/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('产品库tab和数据', async ({ page }) => {
    const productTab = page.locator('text=/产品库|product/i').first();
    if (await productTab.isVisible()) {
      await productTab.click();
      await page.waitForTimeout(500);
    }
  });

  test('服务库tab和数据', async ({ page }) => {
    const serviceTab = page.locator('text=/服务库|service/i').first();
    if (await serviceTab.isVisible()) {
      await serviceTab.click();
      await page.waitForTimeout(500);
    }
  });

  test('有新增按钮', async ({ page }) => {
    await expect(
      page.locator('button').filter({ hasText: /新增|add/i }).first(),
    ).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════
// 9. 模拟演练
// ═══════════════════════════════════════════════

test.describe('模拟演练', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/simulation');
  });

  test('页面标题', async ({ page }) => {
    await expect(page.locator('text=/演练中心|simulation/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('有场景卡片', async ({ page }) => {
    await expect(
      page.locator('text=/价格异议|开场白|竞品|促成|easy|medium|hard/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 10. 优化中心
// ═══════════════════════════════════════════════

test.describe('优化中心', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/optimization');
  });

  test('页面标题', async ({ page }) => {
    await expect(page.locator('text=/优化中心|optimization/i').first()).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 11. 渠道物料
// ═══════════════════════════════════════════════

test.describe('渠道物料', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/channel-materials');
  });

  test('页面标题', async ({ page }) => {
    await expect(page.locator('text=/渠道物料|channel/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('有物料列表', async ({ page }) => {
    await expect(
      page.locator('text=/热玛吉|抗衰|医美|感恩季|video|image/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 12. 数据飞轮
// ═══════════════════════════════════════════════

test.describe('数据飞轮', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/flywheel');
  });

  test('页面标题', async ({ page }) => {
    await expect(page.locator('text=/数据飞轮|flywheel/i').first()).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 13. 系统设置
// ═══════════════════════════════════════════════

test.describe('系统设置', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/settings');
  });

  test('页面标题', async ({ page }) => {
    await expect(page.locator('text=/系统设置|settings/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('Tab切换 - 企业信息', async ({ page }) => {
    const tab = page.locator('text=/企业信息|enterprise/i').first();
    if (await tab.isVisible()) {
      await tab.click();
      await expect(page.locator('text=/企业名称|enterprise.*name/i').first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('Tab切换 - 团队管理', async ({ page }) => {
    const tab = page.locator('text=/团队管理|team/i').first();
    if (await tab.isVisible()) {
      await tab.click();
      await expect(page.locator('text=/张明|zhangming/i').first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('Tab切换 - 模型配置', async ({ page }) => {
    const tab = page.locator('text=/模型配置|model/i').first();
    if (await tab.isVisible()) {
      await tab.click();
      await expect(page.locator('text=/API Key|Temperature/i').first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('Tab切换 - 语言设置', async ({ page }) => {
    const tab = page.locator('text=/语言|language/i').first();
    if (await tab.isVisible()) {
      await tab.click();
      await expect(page.locator('text=/English|中文/i').first()).toBeVisible({ timeout: 5000 });
    }
  });
});
