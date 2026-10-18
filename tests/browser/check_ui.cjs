// Run only against the isolated preview server, never against the shared workspace.
const assert = require('node:assert/strict');
const { chromium } = require('../../.local/ui-qa/node_modules/playwright');
(async () => {
  const browser = await chromium.launch(process.env.CDIP_BROWSER_PATH
    ? { executablePath: process.env.CDIP_BROWSER_PATH, headless: true }
    : { headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto('http://127.0.0.1:8010/#overview');
    await page.getByRole('heading', { name: 'Mọi dữ liệu, một nơi quản lý' }).waitFor();
    assert.equal(await page.locator('input[type=password]').count(), 0);
    await page.getByRole('button', { name: 'Thêm nguồn dữ liệu', exact: true }).click();
    await page.getByRole('button', { name: /Tải tệp CSV/ }).click();
    await page.locator('#csv-file').setInputFiles({ name: 'duplicate.csv', mimeType: 'text/csv', buffer: Buffer.from('id,name\n1,A\n1,B\n') });
    await page.getByRole('button', { name: 'Xem trước dữ liệu' }).click();
    await page.getByRole('button', { name: 'Nhập 2 dòng' }).click();
    await page.locator('#dialog-error:not([hidden])').waitFor();
    assert.match(await page.locator('#dialog-error').innerText(), /giá trị trùng/);
    await page.getByRole('button', { name: 'Chọn tệp khác' }).click();
    await page.locator('#csv-file').setInputFiles({ name: 'browser-check.csv', mimeType: 'text/csv', buffer: Buffer.from('id,name\n1,Nguyễn An\n2,<img src=x onerror=alert(1)>\n') });
    await page.getByRole('button', { name: 'Xem trước dữ liệu' }).click();
    await page.locator('#csv-name').waitFor();
    assert.equal(await page.locator('.preview-table img').count(), 0);
    await page.locator('#csv-name').fill(`Browser check ${Date.now()}`);
    await page.getByRole('button', { name: 'Nhập 2 dòng' }).click();
    await page.getByRole('heading', { name: 'Đã tiếp nhận dữ liệu' }).waitFor();
    await page.getByRole('button', { name: 'Theo dõi cập nhật' }).click();
    await page.getByRole('heading', { name: 'Lịch sử cập nhật', exact: true }).waitFor();
    for (let i = 0; i < 12; i++) {
      await page.getByRole('button', { name: 'Làm mới thông tin' }).click();
      await page.locator('.activity-table').waitFor();
      if (await page.locator('.activity-table .badge.success').count()) break;
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    assert.equal(await page.locator('.activity-table .badge.success').count(), 1);
    await page.getByRole('button', { name: 'Xem kết quả' }).click();
    await page.locator('#dialog .detail-grid').waitFor();
    assert.equal(await page.locator('#dialog .detail-grid dd').nth(2).innerText(), '2');
    await page.getByRole('button', { name: 'Xem nguồn dữ liệu', exact: true }).click();
    await page.locator('#schedule').selectOption('900');
    await page.getByRole('button', { name: 'Lưu lịch cập nhật' }).click();
    await page.getByText('Đã lưu lịch cập nhật.', { exact: true }).waitFor();
    await page.getByText('Thao tác khác', { exact: true }).click();
    await page.getByRole('button', { name: 'Tạm dừng nguồn' }).click();
    await page.locator('#dialog .badge.paused').waitFor();
    await page.getByText('Thao tác khác', { exact: true }).click();
    await page.getByRole('button', { name: 'Bật lại nguồn' }).click();
    await page.getByRole('button', { name: 'Cập nhật ngay' }).click();
    await page.getByText('Đã gửi yêu cầu.', { exact: false }).waitFor();
    await page.goto('http://127.0.0.1:8010/#sources');
    await page.locator('#source-search').fill('not-present-unique-value');
    await page.getByRole('button', { name: 'Tìm kiếm', exact: true }).click();
    await page.getByRole('heading', { name: 'Không tìm thấy nguồn phù hợp' }).waitFor();
    await page.getByRole('button', { name: 'Bỏ bộ lọc' }).click();
    await page.locator('.source-table').waitFor();
    await page.getByRole('button', { name: 'Thêm nguồn dữ liệu', exact: true }).click();
    await page.getByRole('button', { name: /Kết nối Google Sheets/ }).click();
    await page.getByRole('heading', { name: 'Chuẩn bị kết nối Google Sheets' }).waitFor();
    await page.getByRole('button', { name: 'Đóng', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    for (const [hash, heading] of [['overview','Mọi dữ liệu, một nơi quản lý'],['sources','Nguồn dữ liệu'],['activity','Lịch sử cập nhật'],['guide','Trình diễn trong 5 phút']]) {
      await page.goto(`http://127.0.0.1:8010/#${hash}`);
      await page.getByRole('heading', { name: heading, exact: true }).waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `Overflow on ${hash}`);
    }
    await page.getByRole('button', { name: 'Mở danh mục' }).click();
    await page.locator('#sidebar [data-nav=business]').click();
    await page.getByRole('heading', { name: 'Tổng quan kinh doanh', exact: true }).waitFor();
    assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'), 'false');
    assert.deepEqual(errors, []);
    console.log('Browser checks passed: shared entry, CSV validation/import/XSS, job results, schedules, pause/resume, filters, Sheets setup, mobile pages and menu.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });