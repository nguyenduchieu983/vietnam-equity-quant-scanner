import 'dotenv/config';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL??'msedge'});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5173/scanner');
 await page.getByLabel('Mật khẩu quản trị').fill(process.env.SMOKE_ADMIN_PASSWORD);
 await page.getByRole('button',{name:'Mở workspace'}).click();
 await page.getByRole('link',{name:'SIM00',exact:true}).waitFor();
 await page.getByRole('button',{name:'Chi tiết',exact:true}).first().click();
 await page.getByText('Giải thích tín hiệu',{exact:true}).waitFor();
 await page.keyboard.press('Escape');
 await page.getByRole('link',{name:'SIM00',exact:true}).click();
 await page.locator('canvas').first().waitFor();
 await page.screenshot({path:'.runtime/symbol-m2.png',fullPage:true,animations:'disabled'});
 assert.deepEqual(errors,[]);
 console.log('PASS M2 browser scanner explanation and real candlestick canvas.');
}finally{await browser.close();}
