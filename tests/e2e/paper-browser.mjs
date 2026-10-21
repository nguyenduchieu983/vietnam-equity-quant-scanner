import 'dotenv/config';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL??'msedge'});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5173/portfolio');
 await page.getByLabel('Mật khẩu quản trị').fill(process.env.SMOKE_ADMIN_PASSWORD);
 await page.getByRole('button',{name:'Mở workspace'}).click();
 try{await page.getByText('Chưa có phiên paper đã xử lý.',{exact:false}).first().waitFor();}catch(e){console.log(await page.locator('main').innerText());throw e;}
 await page.getByRole('button',{name:'Xem trước & mô phỏng phiên mới'}).click();
 await page.getByRole('dialog').waitFor();
 assert.equal(await page.getByRole('button',{name:'Phê duyệt & chạy cả hai'}).isDisabled(),true);
 await page.keyboard.press('Escape');
 await page.getByRole('combobox',{name:'Cặp paper',exact:true}).click();
 await page.getByRole('option').filter({hasText:'REPLAY'}).first().click();
 await page.locator('canvas').first().waitFor();
 await page.getByText('Đã xử lý 2026-10-20',{exact:false}).waitFor();
 const downloadPromise=page.waitForEvent('download');
 await page.getByRole('button',{name:'Xuất ledger JSON'}).click();
 await (await downloadPromise).saveAs('.runtime/browser-paper.json');
 const ledger=JSON.parse(readFileSync('.runtime/browser-paper.json'));
 assert.equal(ledger.accounts.length,2);assert.equal(ledger.accounts[0].equity.length,34);
 await page.screenshot({path:'.runtime/paper-dark.png',fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'Chuyển giao diện sáng'}).click();
 assert.equal(await page.locator('html').evaluate(e=>e.classList.contains('app-dark')),false);
 await page.screenshot({path:'.runtime/paper-light.png',fullPage:true,animations:'disabled'});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'.runtime/paper-mobile.png',fullPage:true});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 assert.deepEqual(errors,[]);
 console.log('PASS paper UI: forward empty, approval dialog, paired replay metrics/charts/ledger export, dark/light, mobile, no page errors');
}finally{await browser.close();}
