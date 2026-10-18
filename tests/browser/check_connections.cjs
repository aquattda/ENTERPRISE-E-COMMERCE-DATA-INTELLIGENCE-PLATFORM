const assert=require('node:assert/strict');
const {chromium}=require('../../.local/ui-qa/node_modules/playwright');
const base=process.env.CDIP_QA_URL||'http://127.0.0.1:8010';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
 await page.goto(base);
 await page.getByRole('heading',{name:'Lấy dữ liệu. Đơn giản hơn.'}).waitFor();
 assert.equal(await page.getByText('Lãi/lỗ',{exact:false}).count(),0);
 await page.screenshot({path:'.local/connections-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'Thử API mẫu'}).click();
 await page.getByText('3 dòng nhận được',{exact:true}).waitFor();
 await page.getByRole('button',{name:'JSON gốc',exact:true}).click();
 assert.match(await page.locator('#json-view').innerText(),/"example": true/);
 await page.locator('[data-kind=website]').click();
 await page.locator('#url').fill('https://example.com/api?api_key=URL-SECRET');
 await page.locator('#auth').selectOption('bearer');
 await page.locator('#token').fill('TOKEN-MUST-NOT-PERSIST');
 await page.getByText('Đặt tên & tùy chọn dữ liệu',{exact:true}).click();
 await page.locator('#source-name').fill('Website kiểm thử');
 await page.getByRole('button',{name:'Lưu mẫu kết nối',exact:true}).click();
 const stored=await page.evaluate(()=>localStorage.getItem('cdip-source-templates-v1'));
 assert.ok(!stored.includes('TOKEN-MUST-NOT-PERSIST')&&!stored.includes('URL-SECRET'));
 await page.reload();
 await page.locator('[data-open]').first().click();
 assert.equal(await page.locator('#token').inputValue(),'');
 assert.equal(await page.locator('#url').inputValue(),'https://example.com/api');
 await page.route('**/api/sources/read',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({rows:[{id:1,name:'<img src=x onerror=alert(1)>',formula:'=1+1'}],raw:{items:[{id:1}]},row_count:1,http_status:200,elapsed_ms:23,bytes:100,next_cursor:''})}));
 await page.locator('#token').fill('temporary');
 await page.getByRole('button',{name:'Kiểm tra & lấy dữ liệu',exact:false}).click();
 await page.getByText('1 dòng nhận được',{exact:true}).waitFor();
 assert.equal(await page.locator('#table-view img').count(),0);
 const promise=page.waitForEvent('download');await page.getByRole('button',{name:'Tải CSV',exact:true}).click();
 const stream=await (await promise).createReadStream();let csv='';for await(const chunk of stream)csv+=chunk.toString();
 assert.ok(csv.includes("'=1+1"));
 await page.unroute('**/api/sources/read');
 await page.route('**/api/sources/read',route=>route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({error:'Token hết hạn. Kiểm tra lại quyền truy cập.'})}));
 await page.getByRole('button',{name:'Kiểm tra & lấy dữ liệu',exact:false}).click();
 await page.locator('#form-error:not([hidden])').waitFor();
 assert.match(await page.locator('#form-error').innerText(),/Token hết hạn/);
 assert.equal(await page.locator('#export-actions').isVisible(),false);
 await page.setViewportSize({width:390,height:844});
 for(const type of ['shopee','tiktok','sheets','website']){
 await page.locator('[data-kind='+type+']').click();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Overflow '+type);
 if(type==='tiktok'){await page.locator('#operation').selectOption('orders');assert.equal(await page.locator('#order-options').isVisible(),true);}
 if(type==='sheets'){await page.locator('#sheet_mode').selectOption('private');assert.equal(await page.locator('#sheet-private').isVisible(),true);}
 }
 await page.screenshot({path:'.local/connections-mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);
 console.log('Connection UI passed: source cards, example, secret-free presets, preview/XSS, CSV, errors, mobile. Outbound response tests mocked; API example real.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});