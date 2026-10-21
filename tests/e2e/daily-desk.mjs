import 'dotenv/config';import assert from 'node:assert/strict';import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL??'msedge'});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:5173');await page.getByLabel('Mật khẩu quản trị').fill(process.env.SMOKE_ADMIN_PASSWORD);await page.getByRole('button',{name:'Mở workspace'}).click();
 await page.getByRole('heading',{name:'Danh mục & kế hoạch',exact:true}).waitFor();await page.getByText('Đang giữ tiền mặt.',{exact:true}).waitFor();assert.ok(page.url().endsWith('/portfolio'));
 await page.getByRole('button',{name:'Chart & checklist'}).click();await page.getByRole('dialog').waitFor();await page.locator('canvas').first().waitFor();await page.getByText('Được S1 chọn: top 15%, điểm ≥70',{exact:false}).waitFor();
 await page.screenshot({path:'.runtime/desk-chart.png',fullPage:true,animations:"disabled"});await page.keyboard.press('Escape');
 await page.screenshot({path:'.runtime/daily-desk.png',fullPage:true,animations:"disabled"});await page.getByRole('button',{name:'Chuyển giao diện sáng'}).click();await page.setViewportSize({width:390,height:844});await page.screenshot({path:'.runtime/daily-desk-mobile.png',fullPage:true,animations:"disabled"});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);console.log('PASS localhost default desk, paired forward cash, real chart/checklist, dark/light/mobile');
}finally{await browser.close();}
