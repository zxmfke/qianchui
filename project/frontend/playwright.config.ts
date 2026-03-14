import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  retries: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'off',
    trace: 'off',
    actionTimeout: 15000,
    navigationTimeout: 30000,
    launchOptions: {
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    },
  },
  projects: [
    {
      name: 'chrome',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: {
    command: 'npx vite --port 3000',
    port: 3000,
    timeout: 120000,
    reuseExistingServer: true,
  },
});
