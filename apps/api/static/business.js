export const businessPages = {
  business: "Tổng quan kinh doanh",
  orders: "Lãi/lỗ đơn hàng",
  products: "Sản phẩm / SKU",
  marketing: "Quảng cáo & khuyến mãi",
  reconciliation: "Đối soát tiền sàn",
  setup: "Kết nối & giá vốn",
};
const channels = {
  shopee: "Shopee",
  tiktok_shop: "TikTok Shop",
  online: "Online",
  offline: "Offline",
};
const fields = {
  unit_cost: "Giá vốn",
  seller_discount: "Voucher/giảm giá do shop chịu",
  refund_amount: "Hoàn tiền",
  shipping_income: "Tiền vận chuyển thu được",
  other_income: "Thu nhập khác",
  platform_fee: "Phí sàn",
  payment_fee: "Phí thanh toán",
  shipping_cost: "Phí vận chuyển",
  return_shipping_cost: "Phí hoàn hàng",
  voucher_fee: "Phí chương trình voucher",
  ad_cost: "Quảng cáo",
  affiliate_cost: "Affiliate",
  packaging_cost: "Đóng gói",
  tax_cost: "Thuế đã ghi nhận",
  other_cost: "Chi phí khác",
  refunds_final: "Hoàn hàng chưa chốt",
  settlement_final: "Quyết toán chưa chốt",
  order_not_final: "Đơn chưa hoàn tất",
  allocated_costs: "Có khoản chi phí phân bổ",
  allocation_unresolved: "Chưa xác định cách gán chi phí",
  settlement_missing: "Thiếu số tiền đối soát",
  settlement_mismatch: "Tiền đối soát đang lệch",
  conflicting_unit_cost: "Giá vốn xung đột",
  dataset_quality: "Dữ liệu còn lỗi hoặc trùng",
  source_sync_unfinished: "Nguồn đang cập nhật hoặc lần cập nhật gặp lỗi",
};
const filters = {
  start: "",
  end: "",
  channel: "",
  currency: "VND",
  mode: "demo",
};
const e = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (value, currency = "VND") =>
  value == null
    ? "—"
    : `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: currency === "VND" ? 0 : 2 }).format(Number(value))} ${e(currency)}`;
const number = (value) => new Intl.NumberFormat("vi-VN").format(value);
const link = (hash, text) =>
  `<a class="button secondary" href="#${hash}">${text}</a>`;
const status = (row) =>
  row.confidence === "verified"
    ? '<span class="badge success">Đã đủ dữ liệu</span>'
    : '<span class="badge failed">Chưa đủ dữ liệu</span>';
const params = () =>
  new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
export async function loadBusinessData(page, api) {
  return page === "setup"
    ? await api("/api/v1/business/costs")
    : await api("/api/v1/business/report?" + params());
}
function filterForm() {
  return `<form id="business-filter" class="panel filters business-filter"><div><label for="business-mode">Dữ liệu đang xem</label><select id="business-mode"><option value="demo" ${filters.mode === "demo" ? "selected" : ""}>Dữ liệu demo</option><option value="company" ${filters.mode === "company" ? "selected" : ""}>Dữ liệu công ty</option></select></div><div><label for="business-start">Từ ngày</label><input id="business-start" type="date" value="${e(filters.start)}"></div><div><label for="business-end">Đến ngày</label><input id="business-end" type="date" value="${e(filters.end)}"></div><div><label for="business-channel">Kênh bán</label><select id="business-channel"><option value="">Tất cả kênh</option>${Object.entries(
    channels,
  )
    .map(
      ([v, l]) =>
        `<option value="${v}" ${v === filters.channel ? "selected" : ""}>${l}</option>`,
    )
    .join(
      "",
    )}</select></div><div><label for="business-currency">Tiền tệ</label><select id="business-currency">${["VND", "USD"].map((c) => `<option ${c === filters.currency ? "selected" : ""}>${c}</option>`).join("")}</select></div><button class="button primary">Xem báo cáo</button></form>`;
}
function card(label, value, note, negative = false) {
  return `<article class="metric ${negative ? "attention" : ""}"><div class="metric-label">${label}</div><div class="metric-number business-number">${value}</div><p class="metric-note">${note}</p></article>`;
}
function noData() {
  return `<section class="panel"><div class="empty-state"><div class="empty-icon">↗</div><h2>Chưa có dữ liệu kinh doanh</h2><p>Kết nối gian hàng và bổ sung giá vốn để bắt đầu tính lãi/lỗ. Dữ liệu mẫu kỹ thuật không được dùng làm báo cáo kinh doanh.</p>${link("setup", "Chuẩn bị kết nối & giá vốn")}</div></section>`;
}
function groupTable(rows, first) {
  if (!rows.length)
    return '<p class="business-empty">Chưa có dữ liệu phù hợp với bộ lọc.</p>';
  return `<div class="table-wrap"><table class="business-table"><thead><tr><th>${first}</th><th>Doanh thu sau điều chỉnh</th><th>Lãi/lỗ sau chi phí</th><th>Biên lãi</th><th>Độ đầy đủ</th></tr></thead><tbody>${rows
    .slice(0, 100)
    .map(
      (r) =>
        `<tr><td data-label="${first}"><strong>${e(channels[r.label] || r.label)}</strong>${r.key.length === 4 ? `<small>${e(channels[r.key[0]] || r.key[0])} · ${e(r.key[1])}</small>` : ""}</td><td data-label="Doanh thu">${money(r.net_revenue, r.currency)}</td><td data-label="Lãi/lỗ" class="${Number(r.profit_actual) < 0 ? "loss" : ""}">${money(r.profit_actual, r.currency)}</td><td data-label="Biên lãi">${r.margin_percent == null ? "—" : Number(r.margin_percent).toFixed(1) + "%"}</td><td data-label="Độ đầy đủ">${status(r)}<small>${r.incomplete_lines ? `${r.incomplete_lines}/${r.line_count} dòng cần bổ sung` : `${r.line_count} dòng đã đối soát`}</small></td></tr>`,
    )
    .join(
      "",
    )}</tbody></table></div>${rows.length > 100 ? '<p class="business-empty">Hiển thị 100 nhóm đầu. Thu hẹp thời gian hoặc xuất dữ liệu chi tiết.</p>' : ""}`;
}
function alerts(data) {
  const priority = (field) =>
    ({
      unit_cost: 0,
      settlement_mismatch: 1,
      allocated_costs: 2,
      settlement_missing: 3,
    })[field] ?? 10;
  return `<section class="panel"><div class="panel-head"><h2>Việc cần xử lý</h2></div><div class="panel-body">${
    data.alerts.length
      ? [
          ...data.alerts.filter((a) => a.kind !== "missing").slice(0, 2),
          ...data.alerts
            .filter((a) => a.kind === "missing")
            .sort((a, b) => priority(a.field) - priority(b.field))
            .slice(0, 4),
        ]
          .map((a) =>
            a.kind === "missing"
              ? `<div class="business-alert"><span class="badge failed">${a.count} dòng</span><div><strong>${e(fields[a.field] || a.field)}</strong><p>Bổ sung hoặc đối chiếu khoản này trước khi kết luận lợi nhuận.</p></div></div>`
              : `<div class="business-alert"><span class="badge failed">Đang lỗ</span><div><strong>${e(a.sku)} · Đơn ${e(a.order_id)}</strong><p>Lỗ ${money(Math.abs(Number(a.amount)), a.currency)}. Kiểm tra giá bán, giảm giá và các khoản phí trong chi tiết đơn.</p></div></div>`,
          )
          .join("")
      : '<p class="muted">Chưa có đủ dữ liệu để đưa ra cảnh báo kinh doanh.</p>'
  }</div></section>`;
}
export function renderBusiness(page, data, ctx) {
  const { main, title, api, reload, openDialog, toast, friendly } = ctx;
  if (page === "setup") {
    renderSetup(data, ctx);
    return;
  }
  main.innerHTML =
    title(
      businessPages[page],
      "Báo cáo theo ngày ghi nhận bán hàng · Tách riêng từng loại tiền tệ.",
      `${page === "products" ? '<button class="button primary" id="price-simulation">Thử giá bán</button>' : ""}<a class="button secondary" href="/api/v1/business/export?${params()}" download>Xuất chi tiết CSV / Excel</a>`,
    ) +
    filterForm() +
    `<div class="notice business-notice">Lợi nhuận chỉ được xác nhận khi đủ giá vốn, chi phí và số tiền đối soát. Khoản chưa biết hiển thị “—”, không được coi là 0. Báo cáo chưa phải lợi nhuận ròng toàn công ty.</div>`;
  if (data.demo)
    main
      .querySelector(".business-filter")
      .insertAdjacentHTML(
        "beforebegin",
        `<div class="demo-banner"><strong>BẢN DEMO · Dữ liệu giả lập</strong><span>18 đơn minh họa trên 4 kênh · 01–14/10/2026. Phí và giá chỉ dùng để trình diễn, không phải số liệu công ty.</span></div>`,
      );
  if (data.invalid_count || data.conflicting_lines)
    main.innerHTML += `<div class="form-error">Có ${data.invalid_count} bản ghi sai cấu trúc và ${data.conflicting_lines} dòng trùng giữa các nguồn. Báo cáo chưa thể xác nhận lợi nhuận cho đến khi đối chiếu xong.</div>`;
  if (!data.line_count) main.innerHTML += noData();
  else if (page === "business")
    main.innerHTML += `<div class="metric-grid">${card("Doanh thu sau điều chỉnh", money(data.net_revenue, data.currency), "Đã trừ giảm giá và hoàn tiền khi có đủ dữ liệu")}${card("Lãi/lỗ phần đã đủ dữ liệu", money(data.verified_profit, data.currency), `${data.verified_lines}/${data.line_count} dòng; chưa phải tổng lợi nhuận`, Number(data.verified_profit) < 0)}${card("Đơn hàng", number(data.order_count), `${data.line_count} dòng sản phẩm`)}${card("Dòng cần bổ sung", number(data.line_count - data.verified_lines), `${data.verified_lines} dòng đã đủ dữ liệu`)}</div><div class="business-columns"><section class="panel"><div class="panel-head"><h2>Hiệu quả theo kênh bán</h2></div>${revenueChart(data.by_channel)}${groupTable(data.by_channel, "Kênh")}</section>${alerts(data)}</div>`;
  else if (page === "products")
    main.innerHTML += `<section class="panel"><div class="panel-head"><h2>Lãi/lỗ theo SKU</h2><p>Cộng các đơn cùng SKU trong kỳ đã chọn</p></div>${groupTable(
      data.by_sku
        .slice()
        .sort(
          (a, b) =>
            (a.profit_actual == null) - (b.profit_actual == null) ||
            Number(b.profit_actual) - Number(a.profit_actual),
        ),
      "SKU",
    )}</section>`;
  else if (page === "marketing")
    main.innerHTML += `<div class="notice business-notice">Chi phí quảng cáo và khuyến mãi chỉ gắn vào đơn/SKU khi có căn cứ. Chi phí phân bổ vẫn được đánh dấu chưa xác nhận; doanh thu gán cho chiến dịch không chứng minh tác động tăng thêm.</div><section class="panel"><div class="panel-head"><h2>Theo chiến dịch quảng cáo</h2></div>${marketingTable(data.by_campaign, "Chiến dịch")}</section><section class="panel business-gap"><div class="panel-head"><h2>Theo chương trình khuyến mãi</h2></div>${marketingTable(data.by_promotion, "Chương trình")}</section>`;
  else if (page === "orders")
    main.innerHTML += `<section class="panel"><div class="panel-head"><h2>Lãi/lỗ theo đơn hàng</h2></div>${groupTable(data.by_order, "Mã đơn")}</section><section class="panel business-gap"><div class="panel-head"><h2>Chi tiết từng sản phẩm trong đơn</h2></div>${lineTable(data.rows, false)}</section>`;
  else if (page === "reconciliation")
    main.innerHTML += `<section class="panel"><div class="panel-head"><div><h2>Đối chiếu tiền quyết toán</h2><p>Số tiền kỳ vọng và số tiền sàn ghi nhận được so sánh riêng; không trừ phí thêm lần nữa từ tiền thực trả.</p></div></div>${lineTable(data.rows, true)}</section>`;
  const simulateButton = main.querySelector("#price-simulation");
  if (simulateButton) simulateButton.onclick = () => priceSimulation(ctx);
  const form = main.querySelector("#business-filter");
  form.onsubmit = (ev) => {
    ev.preventDefault();
    const start = main.querySelector("#business-start").value,
      end = main.querySelector("#business-end").value;
    if (start && end && start > end) {
      toast("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.", true);
      return;
    }
    Object.assign(filters, {
      start,
      end,
      channel: main.querySelector("#business-channel").value,
      currency: main.querySelector("#business-currency").value,
      mode: main.querySelector("#business-mode").value,
    });
    reload();
  };
  main
    .querySelectorAll("[data-business-line]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          showLine(data.rows[Number(b.dataset.businessLine)], openDialog)),
    );
}
function lineTable(rows, reconcile) {
  return `<div class="table-wrap"><table class="business-table"><thead><tr><th>Đơn / SKU</th>${reconcile ? "<th>Kỳ vọng nhận</th><th>Sàn ghi nhận trả</th><th>Chênh lệch</th>" : "<th>Doanh thu</th><th>Giá vốn đã xuất</th><th>Lãi/lỗ</th>"}<th>Chi tiết</th></tr></thead><tbody>${rows
    .slice(0, 100)
    .map(
      (r, i) =>
        `<tr><td data-label="Đơn / SKU"><strong>${e(r.order_id)}</strong><small>${e(r.sku)} · ${e(channels[r.channel])}</small></td>${reconcile ? `<td data-label="Kỳ vọng">${money(r.expected_payout, r.currency)}</td><td data-label="Sàn ghi nhận trả">${money(r.actual_payout, r.currency)}</td><td data-label="Chênh lệch">${money(r.payout_difference, r.currency)}</td>` : `<td data-label="Doanh thu">${money(r.net_revenue, r.currency)}</td><td data-label="Giá vốn">${money(r.cogs, r.currency)}</td><td data-label="Lãi/lỗ" class="${Number(r.profit_actual) < 0 ? "loss" : ""}">${money(r.profit_actual, r.currency)}</td>`}<td>${status(r)}<button class="text-link" data-business-line="${i}">Xem các khoản</button></td></tr>`,
    )
    .join(
      "",
    )}</tbody></table></div>${rows.length > 100 ? '<p class="business-empty">Hiển thị 100 dòng đầu. Xuất CSV để xem đầy đủ.</p>' : ""}`;
}
function showLine(row, openDialog) {
  const amounts = {
    gross_sales: "Tiền hàng trước giảm giá",
    seller_discount: fields.seller_discount,
    refund_amount: "Hoàn tiền sau điều chỉnh giảm giá",
    shipping_income: fields.shipping_income,
    other_income: fields.other_income,
    net_revenue: "Doanh thu sau điều chỉnh",
    cogs: "Giá vốn xuất trừ nhập lại",
    ...Object.fromEntries(
      Object.entries(fields).filter(
        ([k]) => k.endsWith("_cost") || k.endsWith("_fee"),
      ),
    ),
    profit_actual: "Lãi/lỗ đã xác nhận",
    profit_provisional: "Chênh lệch theo khoản đã biết (chưa kết luận lãi)",
  };
  openDialog(
    "Đơn " + row.order_id,
    `${row.sku} · ${channels[row.channel]}`,
    `${status(row)}<dl class="business-breakdown">${Object.entries(amounts)
      .map(
        ([k, v]) =>
          `<div><dt>${e(v)}</dt><dd>${money(row[k], row.currency)}</dd></div>`,
      )
      .join(
        "",
      )}</dl>${row.missing.length ? `<div class="notice warning">Cần bổ sung: ${row.missing.map((k) => e(fields[k] || k)).join("; ")}.</div>` : ""}<details class="technical"><summary>Nguồn số liệu</summary><p class="field-hint">${e(row.source_name)} · Bản ghi ${e(row.record_id)}</p><p class="field-hint">Giá vốn áp dụng: ${e(row.unit_cost_effective_from || "Theo dòng dữ liệu nguồn")} · Công thức profit-line-v1</p></details>`,
  );
}
function renderSetup(data, ctx) {
  const { main, title, api, reload, openDialog, toast, friendly } = ctx;
  main.innerHTML =
    title(
      "Kết nối dữ liệu & bảng giá vốn",
      "Chuẩn bị dữ liệu một lần, dùng chung cho toàn bộ báo cáo.",
    ) +
    `<div class="health-banner warning"><div class="health-icon">!</div><div><h2>Trình diễn ngay, kết nối thật khi triển khai</h2><p>Chọn Dữ liệu demo trong báo cáo để xem các tình huống nghiệp vụ. Chưa cần API hay thông tin của công ty. Các bước dưới đây dành cho giai đoạn tiếp nhận dữ liệu thật.</p></div></div><div class="connection-grid"><section class="panel"><div class="panel-head"><h2>Shopee</h2><span class="badge pending">Chưa kết nối</span></div><div class="panel-body"><ol class="setup-steps"><li>Mở Shopee Open Platform, đăng ký tài khoản nhà phát triển phù hợp với doanh nghiệp.</li><li>Tạo ứng dụng, làm theo yêu cầu xét duyệt và đăng ký quyền lấy đơn hàng, sản phẩm, hoàn hàng, tài chính.</li><li>Chủ gian hàng cấp quyền cho ứng dụng. Sau đó mới cấu hình và kiểm thử kết nối dữ liệu.</li></ol><a class="button secondary" href="https://open.shopee.com/" target="_blank" rel="noopener noreferrer">Mở Shopee Open Platform ↗</a><p class="field-hint">Yêu cầu cụ thể phụ thuộc thị trường và loại ứng dụng; xác nhận trong tài khoản đăng ký.</p></div></section><section class="panel"><div class="panel-head"><h2>TikTok Shop</h2><span class="badge pending">Chưa kết nối</span></div><div class="panel-body"><ol class="setup-steps"><li>Mở TikTok Shop Partner Center và đăng ký nhà phát triển cho cửa hàng của bạn.</li><li>Tạo ứng dụng phù hợp, chọn thị trường Việt Nam và các quyền đọc dữ liệu cần dùng.</li><li>Thực hiện yêu cầu xét duyệt nếu có, rồi để chủ gian hàng cấp quyền. Quảng cáo có thể cần quyền kết nối riêng.</li></ol><a class="button secondary" href="https://partner.tiktokshop.com/" target="_blank" rel="noopener noreferrer">Mở TikTok Shop Partner Center ↗</a><a class="text-link" href="https://partner.tiktokshop.com/docv2/page/app-review-process" target="_blank" rel="noopener noreferrer">Hướng dẫn loại ứng dụng và xét duyệt ↗</a></div></section></div><section class="panel business-gap"><div class="panel-head"><div><h2>Bảng giá vốn dùng chung</h2><p>Cho chế độ dữ liệu công ty · Theo đơn vị SKU và ngày áp dụng · Không thay đổi dữ liệu demo</p></div><button class="button primary" id="new-cost">+ Thêm giá vốn</button></div>${
      data.items.length
        ? `<div class="table-wrap"><table class="business-table"><thead><tr><th>SKU</th><th>Phạm vi</th><th>Từ ngày</th><th>Giá vốn / đơn vị</th></tr></thead><tbody>${data.items
            .slice(0, 100)
            .map(
              (c) =>
                `<tr><td data-label="SKU"><strong>${e(c.sku)}</strong></td><td data-label="Phạm vi">${c.shop_id === "*" ? "Toàn công ty" : e(c.shop_id)}</td><td data-label="Từ ngày">${e(c.effective_from)}</td><td data-label="Giá vốn">${money(c.unit_cost, c.currency)}</td></tr>`,
            )
            .join("")}</tbody></table></div>`
        : `<div class="empty-state"><h3>Bắt đầu bằng danh sách SKU đang bán</h3><p>Chuẩn bị mã SKU, giá vốn cho một đơn vị và ngày áp dụng. Mã SKU phải khớp với sản phẩm trên các kênh bán. Chưa rõ giá thì để thiếu, không nhập 0.</p></div>`
    }</section><section class="panel business-gap"><div class="panel-head"><h2>Chuẩn bị dữ liệu Online / Offline và chi phí</h2></div><div class="panel-body"><p class="muted">Chọn một nơi ghi dữ liệu thống nhất cho cả đội, có thể là Google Sheets hoặc phần mềm bán hàng. Kết nối tự động chỉ thiết lập được sau khi đã có nơi ghi và cấu trúc dữ liệu.</p><div class="preparation-grid"><div><h3>Đơn bán hàng</h3><p>Mã đơn, ngày bán, kênh, cửa hàng, SKU, số lượng, giá bán, giảm giá, hoàn hàng và trạng thái thanh toán.</p></div><div><h3>Chi phí ngoài sàn</h3><p>Ngày, khoản chi, số tiền, loại tiền, mã đơn/SKU/chiến dịch liên quan; đánh dấu khoản đã nằm trong quyết toán để tránh tính hai lần.</p></div><div><h3>Đối soát</h3><p>Tiền sàn quyết toán và tiền về ngân hàng là hai bước kiểm tra khác nhau. Giao diện hiện đối chiếu dòng quyết toán; chưa kết nối ngân hàng.</p></div></div><div class="title-actions">${link("sources", "Nguồn dữ liệu đã thiết lập")}${link("activity", "Lịch sử lấy dữ liệu")}${link("overview", "Tình trạng hệ thống")}</div><p class="field-hint">Chưa có adapter Shopee/TikTok Shop được kiểm thử trực tiếp. Đăng ký API và cấp quyền là điều kiện để hoàn thiện kết nối; nút mở cổng đăng ký không đồng nghĩa với đã kết nối.</p></div></section>`;
  if (ctx.cloudDemo) {
    main.insertAdjacentHTML(
      "afterbegin",
      '<div class="demo-banner"><strong>Bản demo trên Vercel</strong><span>Không có cơ sở dữ liệu công ty hoặc tác vụ đồng bộ đang chạy. Giá vốn thử nhập chỉ lưu trong trình duyệt này; không chia sẻ cho người khác và không sửa dữ liệu demo. Không nhập thông tin nội bộ thật.</span></div>',
    );
    main
      .querySelectorAll(
        'a[href="#sources"], a[href="#activity"], a[href="#overview"]',
      )
      .forEach((a) => a.remove());
    main.querySelectorAll("h2").forEach((h) => {
      if (h.textContent === "Bảng giá vốn dùng chung")
        h.textContent = "Thử nhập bảng giá vốn";
    });
    const costHint = main
      .querySelector("#new-cost")
      .previousElementSibling.querySelector("p");
    if (costHint)
      costHint.textContent =
        "Lưu thử trên trình duyệt hiện tại · Không đồng bộ giữa thiết bị · Không thay đổi dữ liệu demo";
  }
  main.querySelector("#new-cost").onclick = () => {
    const today = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    openDialog(
      "Thêm giá vốn theo SKU",
      "Nhập giá đã kiểm tra; ngày áp dụng quyết định đơn nào sử dụng mức giá này.",
      `<form id="cost-form"><div class="field"><label for="cost-sku">Mã SKU</label><input id="cost-sku" required maxlength="160" placeholder="Ví dụ: AO-THUN-DEN-M"></div><div class="field"><label for="cost-value">Giá vốn cho một đơn vị</label><input id="cost-value" type="number" min="0" step="0.000001" required placeholder="Ví dụ: 65000"><span class="field-hint">Đơn vị tính phải khớp đơn vị bán. Giá 0 chỉ dùng khi đã xác nhận không phát sinh giá vốn.</span></div><div class="field"><label for="cost-currency">Loại tiền</label><select id="cost-currency"><option>VND</option><option>USD</option></select></div><div class="field"><label for="cost-date">Áp dụng từ ngày</label><input id="cost-date" type="date" value="${e(today)}" required></div><div class="field"><label for="cost-note">Ghi chú hoặc chứng từ</label><input id="cost-note" maxlength="500" placeholder="Ví dụ: Bảng giá nhập tháng 10 đã kiểm tra"></div><details class="technical"><summary>Chỉ áp dụng cho một cửa hàng</summary><div class="field"><label for="cost-shop">Mã cửa hàng trên nguồn dữ liệu</label><input id="cost-shop" value="*" maxlength="160"><span class="field-hint">Để * nếu áp dụng toàn công ty. Mức riêng theo cửa hàng được ưu tiên.</span></div></details></form>`,
      `<button class="button secondary" data-action="close">Hủy</button><button id="cost-save" class="button primary" type="submit" form="cost-form">Lưu giá vốn</button>`,
    );
    document.querySelector("#cost-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const get = (id) => document.querySelector(id).value.trim(),
        button = document.querySelector("#cost-save");
      button.disabled = true;
      try {
        await api("/api/v1/business/costs", {
          method: "POST",
          body: JSON.stringify({
            sku: get("#cost-sku"),
            unit_cost: get("#cost-value"),
            currency: get("#cost-currency"),
            effective_from: get("#cost-date"),
            shop_id: get("#cost-shop") || "*",
            note: get("#cost-note"),
          }),
        });
        document.querySelector("#dialog").close();
        toast(
          ctx.cloudDemo
            ? "Đã lưu thử trong trình duyệt này. Dữ liệu demo giữ nguyên."
            : "Đã lưu giá vốn cho chế độ Dữ liệu công ty. Dữ liệu demo giữ nguyên.",
        );
        reload();
      } catch (error) {
        const el = document.querySelector("#dialog-error");
        el.hidden = false;
        el.textContent = friendly(error);
        button.disabled = false;
      }
    };
  };
}
function priceSimulation({ openDialog, api, friendly }) {
  openDialog(
    "Mô phỏng giá bán & chi phí",
    "Các số ban đầu là giả định minh họa; không phải mức phí của sàn.",
    `<form id="price-form"><div class="simulation-grid">${[
      ["price", "Giá bán / đơn vị (VND)", "180000"],
      ["unit_cost", "Giá vốn / đơn vị (VND)", "60000"],
      ["fixed_cost", "Chi phí khác / đơn vị (VND)", "31000"],
      ["ad_cost", "Quảng cáo / đơn vị (VND)", "15000"],
      ["fee_percent", "Phí theo doanh thu (%)", "5"],
      ["discount_percent", "Giảm giá do shop chịu (%)", "5"],
      ["target_margin_percent", "Biên lãi mong muốn (%)", "20"],
    ]
      .map(
        ([key, label, value]) =>
          `<div class="field"><label for="sim-${key}">${label}</label><input id="sim-${key}" name="${key}" type="number" min="0" ${key.endsWith("percent") ? 'max="100"' : ""} step="0.000001" value="${value}" required></div>`,
      )
      .join(
        "",
      )}</div><p class="field-hint">Giả định phí tính trên tiền hàng sau giảm giá; chi phí khác đã gộp vận chuyển, đóng gói và các khoản cố định trên một sản phẩm. Không thay đổi giá trên sàn.</p></form><div id="simulation-result" role="status" class="business-gap"></div>`,
    `<button class="button secondary" data-action="close">Đóng</button><button class="button primary" id="simulation-submit" form="price-form" type="submit">Tính thử</button>`,
  );
  document.querySelector("#price-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const button = document.querySelector("#simulation-submit");
    button.disabled = true;
    const body = Object.fromEntries(new FormData(ev.target).entries());
    try {
      const r = await api("/api/v1/business/simulate", {
        method: "POST",
        body: JSON.stringify(body),
      });
      document.querySelector("#simulation-result").innerHTML =
        `<div class="notice"><span>Lãi dự kiến / đơn vị: <strong>${money(r.profit)}</strong><br>Biên lãi: <strong>${r.margin_percent == null ? "—" : Number(r.margin_percent).toFixed(1) + "%"}</strong><br>Giá hòa vốn theo giả định: <strong>${money(r.break_even_price)}</strong><br>Giá đạt biên lãi đã chọn: <strong>${money(r.target_price)}</strong>${r.target_price == null ? "<br>Không có giá khả thi với tỷ lệ phí, giảm giá và biên mục tiêu đang chọn." : ""}</span></div>`;
    } catch (error) {
      const el = document.querySelector("#dialog-error");
      el.hidden = false;
      el.textContent = friendly(error);
    } finally {
      button.disabled = false;
    }
  };
}
function revenueChart(groups) {
  const max = Math.max(1, ...groups.map((g) => Number(g.net_revenue) || 0));
  return `<div class="revenue-chart" role="group" aria-label="So sánh doanh thu theo kênh">${groups.map((g) => `<div><span>${e(channels[g.label] || g.label)}</span><svg viewBox="0 0 400 20" preserveAspectRatio="none" role="img" aria-label="${e(channels[g.label] || g.label)}: ${money(g.net_revenue, g.currency)}"><rect width="400" height="20" rx="5" fill="#edf2e9"/><rect width="${(Math.max(0, Number(g.net_revenue) || 0) / max) * 400}" height="20" rx="5" fill="#3c8b71"/></svg><strong>${money(g.net_revenue, g.currency)}</strong></div>`).join("")}</div>`;
}
function marketingTable(groups, label) {
  if (!groups.length)
    return '<p class="business-empty">Chưa có dữ liệu chiến dịch được gắn với đơn hàng trong kỳ.</p>';
  return `<div class="table-wrap"><table class="business-table"><thead><tr><th>${label}</th><th>Doanh thu gán nguồn</th><th>Chi quảng cáo</th><th>ROAS gán nguồn</th><th>Lãi/lỗ</th></tr></thead><tbody>${groups
    .slice(0, 100)
    .map(
      (g) =>
        `<tr><td data-label="${label}"><strong>${e(g.label)}</strong><small>${g.line_count} dòng sản phẩm</small></td><td data-label="Doanh thu">${money(g.net_revenue, g.currency)}</td><td data-label="Quảng cáo">${money(g.ad_cost, g.currency)}</td><td data-label="ROAS">${g.net_revenue != null && Number(g.ad_cost) > 0 ? (Number(g.net_revenue) / Number(g.ad_cost)).toFixed(2) + "x" : "—"}</td><td data-label="Lãi/lỗ" class="${Number(g.profit_actual) < 0 ? "loss" : ""}">${money(g.profit_actual, g.currency)}<small>${g.incomplete_lines ? "Còn " + g.incomplete_lines + " dòng thiếu dữ liệu" : "Đã đủ dữ liệu"}</small></td></tr>`,
    )
    .join("")}</tbody></table></div>`;
}
export function renderDemoGuide({ main, title }) {
  main.innerHTML =
    title(
      "Trình diễn trong 5 phút",
      "Bản mẫu nghiệp vụ dành cho buổi trao đổi với công ty. Không cần API thật.",
    ) +
    `<div class="demo-banner"><strong>Giới thiệu đúng phạm vi</strong><span>“Tôi đã xây dựng bản mẫu chạy được để minh họa việc gom dữ liệu, tính lãi/lỗ và đối soát. Số liệu đang dùng là giả lập; khi nhận API và quy tắc của công ty, tôi sẽ nối dữ liệu thật và kiểm thử lại.”</span></div><div class="guide-cards">${[
      [
        "1",
        "Xem toàn cảnh",
        "Mở Tổng quan kinh doanh. Chỉ ra 4 kênh bán, phần lãi đã đủ dữ liệu và những dòng còn thiếu.",
      ],
      [
        "2",
        "Giải thích một đơn bị lỗ",
        "Vào Lãi/lỗ đơn hàng, mở “Xem các khoản”. Theo dõi doanh thu → giảm giá/hoàn tiền → giá vốn → từng khoản phí.",
      ],
      [
        "3",
        "Thử một phương án giá",
        "Vào Sản phẩm / SKU → Thử giá bán. Thay quảng cáo hoặc giá vốn rồi so sánh giá hòa vốn và giá đạt biên lãi mong muốn.",
      ],
    ]
      .map(
        ([n, h, p]) =>
          `<article class="guide-card"><span class="step-number">${n}</span><h3>${h}</h3><p>${p}</p></article>`,
      )
      .join(
        "",
      )}</div><section class="panel"><div class="panel-head"><h2>Tiếp tục phần trình diễn</h2></div><div class="guide-list"><details open><summary>4. Chỉ ra vấn đề đối soát và hoàn hàng</summary><p>Đơn DEMO-0008 bị lệch quyết toán 3.500 VND. DEMO-0009 hoàn hàng và nhập lại kho; DEMO-0010 hoàn tiền nhưng hàng không nhập lại. Giá vốn của hai tình huống được xử lý khác nhau.</p></details><details><summary>5. So sánh chiến dịch và xuất báo cáo</summary><p>Quảng cáo & khuyến mãi hiển thị doanh thu được gán cho chiến dịch, chi quảng cáo, ROAS và lãi/lỗ khi đủ dữ liệu. Nút Xuất chi tiết tạo CSV mở được bằng Excel. Có truy vấn mẫu cho Excel Power Query / Power BI đọc dữ liệu demo từ API.</p><a class="button secondary" href="/assets/demo-power-query.pq" download>Tải truy vấn Power Query mẫu</a></details><details><summary>Điểm đã chạy được</summary><p>Dashboard có bộ lọc; chi tiết lãi/lỗ; tính giá vốn theo ngày áp dụng; đối soát dòng quyết toán; cảnh báo thiếu dữ liệu/lỗ; mô phỏng giá; xuất CSV; API demo và luồng nhập dữ liệu nền đã có kiểm thử.</p></details><details><summary>Phần cần triển khai khi vào công ty</summary><p>Adapter và cấp quyền Shopee/TikTok Shop thật; nguồn giá vốn, quảng cáo và đơn Online/Offline; thống nhất thuế, hoàn hàng, phân bổ chi phí và thời điểm ghi nhận; đối chiếu chứng từ và ngân hàng. Tự động gửi báo cáo lên Sheets/Power BI và lịch làm mới đám mây chưa được cấu hình.</p></details><details><summary>Phân biệt demo và dữ liệu công ty</summary><p>Mỗi báo cáo có lựa chọn Dữ liệu demo / Dữ liệu công ty. Dữ liệu demo không ghi vào cơ sở dữ liệu công ty. Các mức phí là số minh họa, không phải biểu phí Shopee/TikTok Shop. Bảng giá vốn nhập tay chỉ dùng trong chế độ dữ liệu công ty.</p></details></div></section>`;
}
