import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  reporter: 'line',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1',
    port: 4173,
    reuseExistingServer: true,
  },
  projects: [
    {
      name: 'mobile-chromium',
      use: {
        ...devices['iPhone 13'],
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: 'desktop-chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
});
