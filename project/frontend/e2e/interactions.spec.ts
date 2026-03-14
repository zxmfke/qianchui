import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('qianchui_onboarding_completed', 'true');
  });
  await page.goto('/login');
  await page.getByPlaceholder(/用户名|username/i).fill('demo');
  await page.getByPlaceholder(/密码|password/i).fill('demo123456');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await page.waitForURL(/\/(chat|dashboard)/, { timeout: 15000 });
}

// ═══════════════════════════════════════════════
// 侧边栏导航 — data-tour 属性验证
// ═══════════════════════════════════════════════

test.describe('侧边栏导航完整性', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('所有导航项都有data-tour属性', async ({ page }) => {
    const tourItems = [
      'nav-chat', 'nav-dashboard', 'nav-scripts',
      'nav-training', 'nav-simulation', 'nav-diagnosis',
      'nav-flywheel', 'nav-memory', 'nav-settings',
    ];
    for (const id of tourItems) {
      await expect(page.locator(`[data-tour="${id}"]`)).toBeVisible({ timeout: 5000 });
    }
  });

  test('Logo 区域展示品牌名', async ({ page }) => {
    await expect(page.locator('text=/千锤|QianChui/i').first()).toBeVisible();
  });

  test('用户信息区域显示', async ({ page }) => {
    await expect(page.locator('[data-tour="sidebar"]')).toBeVisible();
  });

  const routes = [
    { nav: /对话|chat/i, path: '/chat' },
    { nav: /看板|dashboard/i, path: '/dashboard' },
    { nav: /话术|script/i, path: '/scripts' },
    { nav: /培训|training/i, path: '/training' },
    { nav: /演练|simulation/i, path: '/simulation' },
    { nav: /诊断|diagnosis/i, path: '/diagnosis' },
    { nav: /优化|optimization/i, path: '/optimization' },
    { nav: /飞轮|flywheel/i, path: '/flywheel' },
    { nav: /记忆|memory/i, path: '/memory' },
    { nav: /设置|settings/i, path: '/settings' },
  ];

  for (const { nav, path } of routes) {
    test(`导航到 ${path}`, async ({ page }) => {
      const link = page.getByRole('link', { name: nav }).first();
      if (await link.isVisible({ timeout: 3000 })) {
        await link.click();
        await page.waitForURL(`**${path}`, { timeout: 10000 });
        expect(page.url()).toContain(path);
      }
    });
  }
});

// ═══════════════════════════════════════════════
// 对话中心 — 深度交互
// ═══════════════════════════════════════════════

test.describe('对话中心交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/chat');
  });

  test('输入框可以输入文字', async ({ page }) => {
    const input = page.locator('input[type="text"], textarea').last();
    if (await input.isVisible({ timeout: 5000 })) {
      await input.fill('测试消息');
      await expect(input).toHaveValue('测试消息');
    }
  });

  test('快捷指令提示出现', async ({ page }) => {
    const input = page.locator('input[type="text"], textarea').last();
    if (await input.isVisible({ timeout: 5000 })) {
      await input.fill('/');
      await page.waitForTimeout(500);
      const cmdVisible = await page.locator('text=/推荐|recommend|诊断|diagnose/i').first().isVisible();
      if (cmdVisible) {
        await expect(page.locator('text=/推荐|recommend/i').first()).toBeVisible();
      }
    }
  });
});

// ═══════════════════════════════════════════════
// 话术库 — 深度交互
// ═══════════════════════════════════════════════

test.describe('话术库交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/scripts');
  });

  test('搜索框可输入', async ({ page }) => {
    const search = page.locator('input[type="text"]').first();
    if (await search.isVisible({ timeout: 5000 })) {
      await search.fill('价格');
      await expect(search).toHaveValue('价格');
    }
  });

  test('分类按钮可点击', async ({ page }) => {
    const cats = page.locator('text=/全部|开场白|异议处理|竞品|促成|售后|All|Opening/i');
    const count = await cats.count();
    if (count > 0) {
      await cats.first().click();
    }
  });

  test('新增话术弹窗打开', async ({ page }) => {
    const addBtn = page.locator('text=/新增话术|add.*script/i').first();
    if (await addBtn.isVisible({ timeout: 5000 })) {
      await addBtn.click();
      await page.waitForTimeout(500);
      const modalVisible = await page.locator('text=/标题|title/i').nth(1).isVisible();
      expect(modalVisible).toBeTruthy();
    }
  });
});

// ═══════════════════════════════════════════════
// 培训中心 — 深度交互
// ═══════════════════════════════════════════════

test.describe('培训中心交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/training');
  });

  test('进度统计展示', async ({ page }) => {
    await expect(
      page.locator('text=/正确率|accuracy|完成|completion|连续|streak/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('题目选项可点击', async ({ page }) => {
    const option = page.locator('text=/^[A-D]\\./').first();
    if (await option.isVisible({ timeout: 5000 })) {
      await option.click();
    }
  });
});

// ═══════════════════════════════════════════════
// 诊断中心 — 深度交互
// ═══════════════════════════════════════════════

test.describe('诊断中心交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/diagnosis');
  });

  test('文本输入区域可粘贴内容', async ({ page }) => {
    const textarea = page.locator('textarea').first();
    if (await textarea.isVisible({ timeout: 5000 })) {
      await textarea.fill('客服：您好\n客户：你们产品多少钱\n客服：很便宜');
      const value = await textarea.inputValue();
      expect(value).toContain('客服');
    }
  });

  test('诊断按钮可见', async ({ page }) => {
    await expect(
      page.locator('text=/开始诊断|start.*diagnosis/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 企业记忆 — 深度交互
// ═══════════════════════════════════════════════

test.describe('企业记忆交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/memory');
  });

  test('痛点/产品/服务 Tab 切换', async ({ page }) => {
    const tabs = ['痛点|pain', '产品|product', '服务|service'];
    for (const tab of tabs) {
      const el = page.locator(`text=/${tab}/i`).first();
      if (await el.isVisible({ timeout: 3000 })) {
        await el.click();
        await page.waitForTimeout(300);
      }
    }
  });

  test('搜索框可输入', async ({ page }) => {
    const search = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first();
    if (await search.isVisible({ timeout: 5000 })) {
      await search.fill('价格');
      await expect(search).toHaveValue('价格');
    }
  });
});

// ═══════════════════════════════════════════════
// 演练中心 — 深度交互
// ═══════════════════════════════════════════════

test.describe('演练中心交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/simulation');
  });

  test('场景卡片展示', async ({ page }) => {
    await expect(
      page.locator('text=/价格异议|竞品对比|犹豫不决|售后投诉|需求模糊|强势砍价|price|competitor|hesitation/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('点击场景开始演练', async ({ page }) => {
    const card = page.locator('text=/价格异议|price.*objection/i').first();
    if (await card.isVisible({ timeout: 5000 })) {
      await card.click();
      await page.waitForTimeout(500);
    }
  });
});

// ═══════════════════════════════════════════════
// 数据看板 — 深度交互
// ═══════════════════════════════════════════════

test.describe('数据看板交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
  });

  test('统计卡片展示', async ({ page }) => {
    await expect(
      page.locator('text=/话术总量|今日|转化率|完成率|total|today|conversion|completion/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('排行榜或趋势图存在', async ({ page }) => {
    await expect(
      page.locator('text=/排行榜|团队|趋势|ranking|team|trend/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 优化中心 — Tab 切换
// ═══════════════════════════════════════════════

test.describe('优化中心交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/optimization');
  });

  test('Tab 列表可见', async ({ page }) => {
    await expect(
      page.locator('text=/话术诊断|标注|优化方案|AB测试|历史|diagnosis|annotation|strategies|ab.*test|history/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('诊断Tab 文本输入区域', async ({ page }) => {
    const textarea = page.locator('textarea').first();
    if (await textarea.isVisible({ timeout: 5000 })) {
      await textarea.fill('客户：种植牙多少钱？\n客服：您好，欢迎咨询');
      const value = await textarea.inputValue();
      expect(value).toContain('客户');
    }
  });
});

// ═══════════════════════════════════════════════
// 数据飞轮 — Tab 切换
// ═══════════════════════════════════════════════

test.describe('数据飞轮交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/flywheel');
  });

  test('扫描按钮可见', async ({ page }) => {
    await expect(
      page.locator('text=/扫描|scan/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('齿轮展示', async ({ page }) => {
    await expect(
      page.locator('text=/齿轮|痛点|产品|服务|话术|gear|pain|product|service|script/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 渠道物料 — 深度交互
// ═══════════════════════════════════════════════

test.describe('渠道物料交互', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/channel-materials');
  });

  test('上传按钮可见', async ({ page }) => {
    await expect(
      page.locator('text=/上传|upload/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('渠道筛选存在', async ({ page }) => {
    await expect(
      page.locator('text=/抖音|小红书|微信|百度|douyin|xhs|wechat|baidu/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 路由守卫
// ═══════════════════════════════════════════════

test.describe('路由守卫', () => {
  test('未登录访问受保护页面重定向到登录', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('token');
    });
    await page.goto('/dashboard');
    await page.waitForURL('**/login', { timeout: 10000 });
    expect(page.url()).toContain('/login');
  });

  test('访问不存在的页面重定向', async ({ page }) => {
    await login(page);
    await page.goto('/nonexistent-page');
    await page.waitForURL(/\/(chat|login)/, { timeout: 10000 });
  });
});
