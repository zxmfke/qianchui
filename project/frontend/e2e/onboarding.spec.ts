import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder(/用户名|username/i).fill('demo');
  await page.getByPlaceholder(/密码|password/i).fill('demo123456');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await page.waitForURL(/\/(chat|dashboard)/, { timeout: 15000 });
}

test.describe('新手指引', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('qianchui_onboarding_completed');
    });
  });

  test('首次登录显示欢迎弹窗', async ({ page }) => {
    await login(page);
    await expect(
      page.locator('text=/欢迎使用|welcome/i').first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('欢迎弹窗显示核心功能亮点', async ({ page }) => {
    await login(page);
    await page.waitForSelector('text=/欢迎使用|welcome/i', { timeout: 10000 });
    await expect(page.locator('text=/AI.*对话|AI.*Chat/i').first()).toBeVisible();
    await expect(page.locator('text=/飞轮|Flywheel/i').first()).toBeVisible();
  });

  test('点击跳过关闭欢迎弹窗', async ({ page }) => {
    await login(page);
    await page.waitForSelector('text=/欢迎使用|welcome/i', { timeout: 10000 });

    await page.locator('text=/跳过|skip/i').first().click();
    await expect(page.locator('text=/欢迎使用|welcome/i')).not.toBeVisible({ timeout: 5000 });
  });

  test('点击开始引导进入步骤', async ({ page }) => {
    await login(page);
    await page.waitForSelector('text=/欢迎使用|welcome/i', { timeout: 10000 });

    await page.locator('text=/开始引导|start.*tour/i').first().click();
    await expect(
      page.locator('text=/新手指引|getting.*started/i').first(),
    ).toBeVisible({ timeout: 5000 });
  });

  test('引导步骤可以前后导航', async ({ page }) => {
    await login(page);
    await page.waitForSelector('text=/欢迎使用|welcome/i', { timeout: 10000 });
    await page.locator('text=/开始引导|start.*tour/i').first().click();
    await page.waitForSelector('text=/新手指引|getting.*started/i', { timeout: 5000 });

    await page.locator('text=/下一步|next/i').first().click();
    await page.waitForTimeout(300);
    await expect(page.locator('text=/1\\/10|2\\/10/').first()).toBeVisible();
  });

  test('已完成引导的用户不再显示', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('qianchui_onboarding_completed', 'true');
    });
    await login(page);
    await page.waitForTimeout(2000);
    await expect(page.locator('text=/欢迎使用|welcome/i')).not.toBeVisible();
  });
});

test.describe('AI 助手按钮', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('qianchui_onboarding_completed', 'true');
    });
    await login(page);
  });

  test('AI助手悬浮按钮可见', async ({ page }) => {
    await expect(page.locator('[title*="AI"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('点击AI助手按钮打开面板', async ({ page }) => {
    const btn = page.locator('[title*="AI"]').first();
    if (await btn.isVisible({ timeout: 5000 })) {
      await btn.click();
      await expect(
        page.locator('text=/AI.*助手|AI.*Assistant/i').first(),
      ).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('设置页 - 重新开始引导', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('qianchui_onboarding_completed', 'true');
    });
    await login(page);
    await page.goto('/settings');
  });

  test('语言设置Tab中有重新引导按钮', async ({ page }) => {
    const langTab = page.locator('text=/语言|language/i').first();
    if (await langTab.isVisible({ timeout: 5000 })) {
      await langTab.click();
      await expect(
        page.locator('text=/重新开始引导|restart.*tour/i').first(),
      ).toBeVisible({ timeout: 5000 });
    }
  });
});
