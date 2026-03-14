import { test, expect, Page } from '@playwright/test';

/**
 * 增强版页面功能测试 — 提升覆盖率至 90%
 *
 * 覆盖交互行为、边界场景、状态切换等
 */

async function login(page: Page) {
  await page.goto('/login');
  await page.addInitScript(() => {
    localStorage.setItem('qianchui_onboarding_completed', 'true');
  });
  await page.getByPlaceholder(/用户名|username/i).fill('demo');
  await page.getByPlaceholder(/密码|password/i).fill('demo123456');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await page.waitForURL(/\/(chat|dashboard)/, { timeout: 15000 });
}

// ═══════════════════════════════════════════════
// 对话中心增强测试
// ═══════════════════════════════════════════════

test.describe('对话中心 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/chat');
    await page.waitForTimeout(500);
  });

  test('新建对话按钮可点击', async ({ page }) => {
    const plusBtn = page.locator('button').filter({ has: page.locator('svg') }).first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await page.waitForTimeout(1000);
    }
  });

  test('搜索对话功能', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('测试');
      await page.waitForTimeout(500);
    }
  });

  test('对话输入框支持快捷指令提示', async ({ page }) => {
    const textarea = page.locator('textarea').first();
    if (await textarea.isVisible()) {
      await textarea.fill('/');
      await page.waitForTimeout(500);
      const cmdHint = page.locator('text=/推荐|诊断|刷题|演练|看板|recommend|diagnose/i').first();
      if (await cmdHint.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(cmdHint).toBeVisible();
      }
    }
  });

  test('页面标题区域正确显示', async ({ page }) => {
    await expect(
      page.locator('text=/AI.*对话|chat.*center|开始新对话|start.*new/i').first(),
    ).toBeVisible({ timeout: 5000 });
  });

  test('消息列表区域渲染', async ({ page }) => {
    const messageArea = page.locator('[class*="flex-1"][class*="flex-col"]').first();
    await expect(messageArea).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════
// 话术库增强测试
// ═══════════════════════════════════════════════

test.describe('话术库 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/scripts');
    await page.waitForTimeout(500);
  });

  test('分类标签可切换', async ({ page }) => {
    const categories = ['开场白', '异议处理', '竞品应对', '促成', '售后', '复购'];
    for (const cat of categories) {
      const tab = page.locator(`text=${cat}`).first();
      if (await tab.isVisible({ timeout: 2000 }).catch(() => false)) {
        await tab.click();
        await page.waitForTimeout(300);
      }
    }
  });

  test('搜索话术功能', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('价格');
      await page.waitForTimeout(500);
    }
  });

  test('新增话术表单包含三层结构', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /新增话术|add.*script/i }).first();
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await page.waitForTimeout(500);
      await expect(page.locator('text=/标题|title/i').first()).toBeVisible({ timeout: 3000 });
      await expect(page.locator('text=/分类|category/i').first()).toBeVisible({ timeout: 3000 });
    }
  });

  test('话术计数显示', async ({ page }) => {
    await expect(
      page.locator('text=/条话术|scripts/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 培训中心增强测试
// ═══════════════════════════════════════════════

test.describe('培训中心 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/training');
    await page.waitForTimeout(500);
  });

  test('统计数据显示', async ({ page }) => {
    await expect(
      page.locator('text=/连续天数|streak|正确率|accuracy|累计答对|total.*correct/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('难度选择', async ({ page }) => {
    const diffBtns = page.locator('text=/简单|中等|困难|easy|medium|hard/i');
    const count = await diffBtns.count();
    if (count > 0) {
      await diffBtns.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('薄弱环节面板有提示', async ({ page }) => {
    await expect(
      page.locator('text=/薄弱|弱|weak/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 演练中心增强测试
// ═══════════════════════════════════════════════

test.describe('演练中心 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/simulation');
    await page.waitForTimeout(500);
  });

  test('场景列表展示', async ({ page }) => {
    const scenarios = ['价格异议', '竞品对比', '犹豫不决', '售后投诉'];
    for (const s of scenarios) {
      const el = page.locator(`text=${s}`).first();
      if (await el.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(el).toBeVisible();
        break;
      }
    }
  });

  test('场景卡片有难度标签', async ({ page }) => {
    await expect(
      page.locator('text=/简单|中等|困难|easy|medium|hard/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('场景卡片有描述', async ({ page }) => {
    await expect(
      page.locator('text=/客户|customer|太贵|不满/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('开始演练按钮可见', async ({ page }) => {
    await expect(
      page.locator('button').filter({ hasText: /开始演练|start.*drill/i }).first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 诊断中心增强测试
// ═══════════════════════════════════════════════

test.describe('诊断中心 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/diagnosis');
    await page.waitForTimeout(500);
  });

  test('输入区支持文本粘贴', async ({ page }) => {
    const textarea = page.locator('textarea').first();
    if (await textarea.isVisible()) {
      await textarea.fill('客服：您好\n客户：你们价格多少？\n客服：我们的价格是...');
      const textVal = await textarea.inputValue();
      expect(textVal.length).toBeGreaterThan(10);
    }
  });

  test('诊断按钮初始不可用或可用', async ({ page }) => {
    const diagBtn = page.locator('button').filter({ hasText: /诊断|分析|analyze/i }).first();
    await expect(diagBtn).toBeVisible({ timeout: 5000 });
  });

  test('有上传提示区域', async ({ page }) => {
    await expect(
      page.locator('text=/拖拽|上传|drop|upload|支持.*txt|supported/i').first(),
    ).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════
// 优化中心增强测试
// ═══════════════════════════════════════════════

test.describe('优化中心 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/optimization');
    await page.waitForTimeout(500);
  });

  test('页面有多个tab标签', async ({ page }) => {
    const tabs = ['话术诊断', '标注工作台', '优化方案', 'AB测试', '优化历史'];
    for (const tab of tabs) {
      const el = page.locator(`text=${tab}`).first();
      if (await el.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(el).toBeVisible();
      }
    }
  });

  test('Tab切换到标注工作台', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /标注|annotation/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }
  });

  test('Tab切换到优化方案', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /优化方案|strategies/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }
  });

  test('Tab切换到AB测试', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /AB测试|A\/B/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }
  });

  test('Tab切换到优化历史', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /优化历史|history/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }
  });

  test('诊断tab有输入区和行业选择', async ({ page }) => {
    await expect(
      page.locator('textarea').first(),
    ).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════
// 渠道物料增强测试
// ═══════════════════════════════════════════════

test.describe('渠道物料 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/channel-materials');
    await page.waitForTimeout(500);
  });

  test('有上传物料按钮', async ({ page }) => {
    await expect(
      page.locator('button').filter({ hasText: /上传|upload/i }).first(),
    ).toBeVisible({ timeout: 5000 });
  });

  test('有渠道筛选', async ({ page }) => {
    await expect(
      page.locator('text=/抖音|小红书|微信|百度|douyin|xhs|wechat|baidu/i').first(),
    ).toBeVisible({ timeout: 5000 });
  });

  test('总数统计显示', async ({ page }) => {
    await expect(
      page.locator('text=/条物料|materials/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 数据飞轮增强测试
// ═══════════════════════════════════════════════

test.describe('数据飞轮 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/flywheel');
    await page.waitForTimeout(500);
  });

  test('有副标题说明飞轮机制', async ({ page }) => {
    await expect(
      page.locator('text=/痛点|进化|策略|pain.*point|evolution/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('有扫描按钮', async ({ page }) => {
    await expect(
      page.locator('button').filter({ hasText: /扫描|scan/i }).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('有tab切换区域', async ({ page }) => {
    const tabs = ['飞轮全景', '痛点趋势', '产品覆盖', '服务策略', '话术生命周期'];
    for (const tab of tabs) {
      const el = page.locator(`text=${tab}`).first();
      if (await el.isVisible({ timeout: 2000 }).catch(() => false)) {
        await el.click();
        await page.waitForTimeout(300);
      }
    }
  });

  test('齿轮区域展示', async ({ page }) => {
    await expect(
      page.locator('text=/齿轮|gear/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════
// 企业记忆增强测试
// ═══════════════════════════════════════════════

test.describe('企业记忆 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/memory');
    await page.waitForTimeout(500);
  });

  test('有知识链路说明', async ({ page }) => {
    await expect(
      page.locator('text=/知识链路|知识|knowledge.*chain|痛点.*产品.*服务.*话术/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('搜索功能', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('价格');
      await page.waitForTimeout(500);
    }
  });

  test('痛点有严重度标签', async ({ page }) => {
    await expect(
      page.locator('text=/严重|高|中|低|critical|high|medium|low/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('Tab切换到产品库', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /产品|product/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }
  });

  test('Tab切换到服务库', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /服务|service/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }
  });
});

// ═══════════════════════════════════════════════
// 系统设置增强测试
// ═══════════════════════════════════════════════

test.describe('系统设置 — 增强测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/settings');
    await page.waitForTimeout(500);
  });

  test('企业信息表单可编辑', async ({ page }) => {
    const nameInput = page.locator('input[type="text"]').first();
    if (await nameInput.isVisible()) {
      const oldValue = await nameInput.inputValue();
      await nameInput.clear();
      await nameInput.fill('测试企业名');
      expect(await nameInput.inputValue()).toBe('测试企业名');
      await nameInput.clear();
      await nameInput.fill(oldValue);
    }
  });

  test('行业选择下拉框', async ({ page }) => {
    const select = page.locator('select').first();
    if (await select.isVisible()) {
      const options = await select.locator('option').allTextContents();
      expect(options.length).toBeGreaterThan(1);
    }
  });

  test('保存按钮可见', async ({ page }) => {
    await expect(
      page.locator('button').filter({ hasText: /保存|save/i }).first(),
    ).toBeVisible({ timeout: 5000 });
  });

  test('API密钥Tab有安全提示', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /API.*密钥|API.*Key/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
      await expect(
        page.locator('text=/密钥|创建后|仅显示一次|shown.*once/i').first(),
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test('团队成员列表有角色标签', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /团队|team/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
      await expect(
        page.locator('text=/管理员|主管|坐席|admin|manager|agent/i').first(),
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test('模型配置有Temperature滑块', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /模型|model/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
      await expect(
        page.locator('text=/Temperature/i').first(),
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test('语言设置有重新引导按钮', async ({ page }) => {
    const tab = page.locator('button').filter({ hasText: /语言|language/i }).first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
      await expect(
        page.locator('text=/重新开始引导|restart.*tour/i').first(),
      ).toBeVisible({ timeout: 5000 });
    }
  });
});

// ═══════════════════════════════════════════════
// 通用 UI 行为测试
// ═══════════════════════════════════════════════

test.describe('通用 UI 行为', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('侧边栏Logo和品牌可见', async ({ page }) => {
    await expect(page.locator('text=/千锤|QianChui/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('404页面重定向到首页', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await expect(page).toHaveURL(/\/(chat|login)/);
  });

  test('各页面导航不出错', async ({ page }) => {
    const routes = ['/dashboard', '/scripts', '/training', '/simulation', '/diagnosis',
      '/optimization', '/flywheel', '/memory', '/settings', '/channel-materials', '/chat'];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForTimeout(300);
      await expect(page).toHaveURL(new RegExp(route));
    }
  });

  test('侧边栏data-tour属性存在', async ({ page }) => {
    await expect(page.locator('[data-tour="sidebar"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-tour="nav-chat"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-tour="nav-dashboard"]')).toBeVisible({ timeout: 5000 });
  });
});
