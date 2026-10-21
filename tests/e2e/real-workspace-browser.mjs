import 'dotenv/config';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL??'msedge'});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5173/dashboard');await page.getByLabel('Mật khẩu quản trị').fill(process.env.SMOKE_ADMIN_PASSWORD);await page.getByRole('button',{name:'Mở workspace'}).click();
 await page.getByText('REAL EOD · PROVISIONAL',{exact:true}).waitFor();await page.getByText('Phiên 2026-10-20',{exact:true}).waitFor();await page.screenshot({path:'.runtime/real-dashboard.png',fullPage:true});
 for(const path of ['/scanner','/symbols/FPT','/lab']){await page.locator(`nav a[href="${path}"]`).click();await page.getByText('REAL EOD · PROVISIONAL',{exact:true}).waitFor();assert.equal(await page.locator('main').innerText().then(s=>s.includes('SIM00')),false);if(path==='/symbols/FPT')await page.locator('canvas').first().waitFor();}
 await page.locator('nav a[href="/operations"]').click();await page.getByText('VNDIRECT public EOD đã bật.',{exact:false}).waitFor();assert.equal(await page.getByRole('button',{name:'Nhập lịch sử DEMO 2022–2026'}).count(),0);
 assert.deepEqual(errors,[]);console.log('PASS real workspace browser: dashboard, scanner, FPT chart, lab, operations');
}finally{await browser.close();}
