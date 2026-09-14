import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const backendDir = fileURLToPath(new URL('../backend/', import.meta.url));
const patientDir = fileURLToPath(new URL('../patient-app/', import.meta.url));
const doctorDir = fileURLToPath(new URL('../doctor-portal/', import.meta.url));
const adminDir = fileURLToPath(new URL('../admin-portal/', import.meta.url));

const backendUrl = process.env.API_URL ?? 'http://127.0.0.1:8080';
const patientUrl = process.env.PATIENT_URL ?? 'http://127.0.0.1:5174';
const doctorUrl = process.env.DOCTOR_URL ?? 'http://127.0.0.1:5175';
const adminUrl = process.env.ADMIN_URL ?? 'http://127.0.0.1:5176';

export default defineConfig({
  testDir: './tests',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['line'], ['html', { outputFolder: 'playwright-report', open: 'never' }]] : 'list',
  outputDir: 'test-results',
  use: {
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    colorScheme: 'light',
    locale: 'en-US',
    timezoneId: 'UTC',
  },
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8080',
      cwd: backendDir,
      url: `${backendUrl}/ready`,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --strictPort',
      cwd: patientDir,
      url: `${patientUrl}/login`,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --strictPort',
      cwd: doctorDir,
      url: `${doctorUrl}/login`,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --strictPort',
      cwd: adminDir,
      url: `${adminUrl}/login`,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
  projects: [
    {
      name: 'mobile-390',
      use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 },
    },
    {
      name: 'tablet-768',
      use: { ...devices['Desktop Chrome'], viewport: { width: 768, height: 1024 }, deviceScaleFactor: 1 },
    },
    {
      name: 'desktop-1440',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 },
    },
  ],
});
