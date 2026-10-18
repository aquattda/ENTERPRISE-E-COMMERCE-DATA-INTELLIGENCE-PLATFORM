// Live smoke test against public example data only; no company credentials.
const assert=require('node:assert/strict');
const {chromium}=require('../../.local/ui-qa/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
 await page.goto('https://cdip-business-demo.vercel.app');
 await page.locator('#url').fill('https://jsonplaceholder.typicode.com/todos?_limit=3');
 await page.getByRole('button',{name:'Kiểm tra & lấy dữ liệu',exact:false}).click();
 await page.getByText('3 dòng nhận được',{exact:true}).waitFor({timeout:45000});
 assert.equal(await page.locator('#connection-status').innerText(),'Đã lấy dữ liệu');
 await page.locator('[data-kind=sheets]').click();
 await page.locator('#url').fill('https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0');
 await page.getByRole('button',{name:'Kiểm tra & lấy dữ liệu',exact:false}).click();
 await page.getByText('30 dòng nhận được',{exact:true}).waitFor({timeout:45000});
 assert.equal(await page.locator('#table-view tbody tr').count(),30);
 const promise=page.waitForEvent('download');await page.getByRole('button',{name:'Tải CSV',exact:true}).click();
 assert.equal((await promise).suggestedFilename(),'du-lieu-nguon.csv');
 await page.screenshot({path:'.local/connections-live-data.png',fullPage:true});
 assert.deepEqual(errors,[]);
 console.log('Live hosted browser verified: website 3 rows, public Google Sheet 30 rows, CSV download, no page errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});