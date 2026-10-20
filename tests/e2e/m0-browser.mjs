import 'dotenv/config';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(process.env.WEB_URL ?? 'http://127.0.0.1:5173');
  await page.getByLabel('Mật khẩu quản trị').fill(process.env.SMOKE_ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Mở workspace' }).click();
  await page.getByText('DEMO / SYNTHETIC', { exact: true }).waitFor();
  await page.getByRole('cell', { name: 'DEMOA', exact: true }).waitFor();
  assert.equal(await page.getByText('Invalid PrimeUI License', { exact: true }).count(), 0);
  await page.screenshot({ path: '.runtime/dashboard-dark.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: 'Chuyển giao diện sáng' }).click();
  assert.equal(await page.evaluate(() => localStorage.getItem('quant-theme')), 'light');
  await page.screenshot({ path: '.runtime/dashboard-light.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('link', { name: 'Scanner', exact: false }).click();
  await page.getByRole('heading', { name: 'Chưa có kết quả scan' }).waitFor();
  await page.getByRole('link', { name: 'Strategy Lab', exact: false }).click();
  await page.getByRole('heading', { name: 'Chưa triển khai milestone này' }).waitFor();
  await page.getByRole('link', { name: 'Dữ liệu & vận hành', exact: false }).click();
  await page.getByRole('heading', { name: 'Lịch sử ingestion' }).waitFor();
  assert.deepEqual(errors, []);
  console.log('PASS M0 browser: login, DB-backed DEMO overview, theme persistence setting, empty scanner, pending lab, operations, no uncaught page errors.');
} finally { await browser.close(); }
