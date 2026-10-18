const $ = (s) => document.querySelector(s);
const e = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const names = {
  website: "API website",
  sheets: "Google Sheets",
  shopee: "Shopee",
  tiktok: "TikTok Shop",
};
let kind = "website",
  result = null,
  lastBody = null,
  busy = false,
  toastTimer;
const storageKey = "cdip-source-templates-v1";
const field = (id, label, type = "text", placeholder = "", hint = "") =>
  `<div class="field"><label for="${id}">${label}</label><input id="${id}" name="${id}" type="${type}" placeholder="${e(placeholder)}" ${type === "password" ? 'autocomplete="new-password"' : 'autocomplete="off"'} maxlength="${type === "password" ? 8192 : 6000}">${hint ? `<small>${hint}</small>` : ""}</div>`;
const secret = (label = "Access token") =>
  field("token", label, "password", "Chỉ dùng cho lần kết nối này");
function notify(text) {
  clearTimeout(toastTimer);
  $("#toast").textContent = text;
  $("#toast").hidden = false;
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 5000);
}
function resetResult() {
  result = null;
  lastBody = null;
  $("#export-actions").hidden = true;
  $("#connection-status").textContent = "Chưa kiểm tra";
  $("#connection-status").className = "pill";
  $("#result-body").innerHTML =
    '<div class="empty"><div class="empty-symbol">⇣</div><h3>Dữ liệu sẽ xuất hiện ở đây</h3><p>Chọn nguồn ở trên rồi bấm “Kiểm tra & lấy dữ liệu”.</p></div>';
  $("#form-error").hidden = true;
}
function selectSource(next, template = {}) {
  if (busy) return;
  kind = next;
  resetResult();
  $("#connection-form").reset();
  document.querySelectorAll("[data-kind]").forEach((b) => {
    b.classList.toggle("selected", b.dataset.kind === kind);
    b.setAttribute("aria-pressed", String(b.dataset.kind === kind));
  });
  $("#connection-heading").textContent = "2. Kết nối " + names[kind];
  $("#path-wrap").hidden = kind !== "website";
  let html = "";
  if (kind === "website")
    html =
      field(
        "url",
        "Địa chỉ API",
        "url",
        "https://website-cua-ban.vn/api/products",
        "Dùng endpoint trả dữ liệu JSON/CSV, không phải URL trang bán hàng.",
      ) +
      '<div class="field"><label for="auth">Cách xác thực</label><select id="auth" name="auth"><option value="none">Không cần xác thực</option><option value="bearer">Bearer token</option><option value="header">API key trong header</option></select></div><div id="auth-fields"></div>';
  if (kind === "sheets")
    html =
      '<div class="source-tip">Dán liên kết bảng tính bạn có quyền đọc. Bảng riêng tư dùng Google Access token; không cần công khai dữ liệu nội bộ.</div>' +
      field(
        "url",
        "Liên kết Google Sheets",
        "url",
        "https://docs.google.com/spreadsheets/d/.../edit",
      ) +
      '<div class="field-row"><div><label for="sheet_mode">Quyền truy cập</label><select id="sheet_mode" name="sheet_mode"><option value="public">Bảng công khai / đã công bố</option><option value="private">Bảng riêng tư · Access token</option></select></div>' +
      field(
        "gid",
        "Mã tab (gid)",
        "text",
        "0",
        "Lấy từ phần gid= trong liên kết bảng tính.",
      ) +
      '</div><div id="sheet-private" hidden>' +
      secret("Google Access token") +
      field(
        "sheet_range",
        "Vùng dữ liệu",
        "text",
        "A1:Z1000",
        "Ví dụ: 'Tên tab'!A1:Z1000. Dòng đầu dùng làm tên cột.",
      ) +
      "</div>";
  if (kind === "shopee" || kind === "tiktok") {
    const shopee = kind === "shopee";
    html = `<div class="source-tip">Dùng thông tin ứng dụng đã được cấp quyền trên ${names[kind]}. Hiện chưa có kết nối sàn nào được thiết lập. Khóa/token nhập bên dưới chỉ được gửi tới API chính thức để lấy dữ liệu.</div><div class="field"><label for="operation">Dữ liệu muốn lấy</label><select id="operation" name="operation"><option value="shops">${shopee ? "Thông tin cửa hàng" : "Cửa hàng được cấp quyền"}</option><option value="orders">Danh sách đơn hàng</option></select></div><div class="field-row">${field("app_id", shopee ? "Partner ID" : "App key", "text", shopee ? "Mã ứng dụng Shopee" : "Mã ứng dụng TikTok Shop")}${field("app_secret", shopee ? "Partner key" : "App secret", "password", "Khóa bí mật của ứng dụng")}</div>${secret()}${field("shop_id", shopee ? "Shop ID" : "Shop cipher", "text", shopee ? "Mã cửa hàng Shopee" : "Cần khi lấy đơn hàng", shopee ? "Cửa hàng đã cấp quyền cho ứng dụng." : "Lấy từ trường cipher trong kết quả “Cửa hàng được cấp quyền”.")}<div id="order-options" hidden><label for="days">Khoảng thời gian tạo đơn</label><select id="days" name="days"><option value="1">24 giờ gần nhất</option><option value="7" selected>7 ngày gần nhất</option><option value="14">14 ngày gần nhất</option></select><small>Lấy 20 đơn mỗi trang. Không thay đổi đơn hàng trên sàn.</small></div>`;
  }
  $("#source-fields").innerHTML = html;
  if ($("#gid")) $("#gid").value = "0";
  if ($("#sheet_range")) $("#sheet_range").value = "A1:Z1000";
  Object.entries(template).forEach(([key, value]) => {
    const input = $("#connection-form").elements.namedItem(key);
    if (
      input &&
      typeof value !== "object" &&
      !["token", "app_secret"].includes(key)
    )
      input.value = value;
  });
  if ($("#auth")) {
    $("#auth").onchange = renderAuth;
    renderAuth();
  }
  if ($("#sheet_mode")) {
    $("#sheet_mode").onchange = () => {
      $("#sheet-private").hidden = $("#sheet_mode").value !== "private";
    };
    $("#sheet_mode").onchange();
    $("#url").addEventListener("change", () => {
      try {
        const u = new URL($("#url").value);
        const gid =
          new URLSearchParams(u.hash.slice(1)).get("gid") ||
          u.searchParams.get("gid");
        if (gid && /^\d+$/.test(gid)) $("#gid").value = gid;
      } catch {}
    });
  }
  if ($("#operation")) {
    $("#operation").onchange = () =>
      ($("#order-options").hidden = $("#operation").value !== "orders");
    $("#operation").onchange();
  }
  if ($("#header_name") && template.header_name)
    $("#header_name").value = template.header_name;
}
function renderAuth() {
  const a = $("#auth").value;
  $("#auth-fields").innerHTML =
    a === "none"
      ? ""
      : (a === "header"
          ? '<div class="field"><label for="header_name">Tên header chứa API key</label><select id="header_name" name="header_name">' +
            [
              "X-API-Key",
              "API-Key",
              "Authorization",
              "X-Auth-Token",
              "Token",
              "X-Shopify-Access-Token",
            ]
              .map((v) => `<option>${v}</option>`)
              .join("") +
            "</select></div>"
          : "") +
        secret(a === "bearer" ? "Bearer token" : "Giá trị API key / header");
}
function collect() {
  const raw = Object.fromEntries(new FormData($("#connection-form")));
  delete raw.name;
  return { ...raw, kind, days: Number(raw.days || 7) };
}
function saved() {
  try {
    const list = JSON.parse(localStorage.getItem(storageKey) || "[]");
    return Array.isArray(list)
      ? list
          .filter((x) => x && names[x.kind] && typeof x.name === "string")
          .slice(0, 20)
      : [];
  } catch {
    return [];
  }
}
function showSaved() {
  const list = saved();
  $("#saved-count").textContent = list.length;
  $("#saved-list").innerHTML = list.length
    ? list
        .map(
          (s, i) =>
            `<div class="saved-item"><button type="button" class="saved-open" data-open="${i}"><strong>${e(s.name)}</strong><span>${names[s.kind]} · Nhập lại token khi dùng</span></button><button type="button" class="delete" data-delete="${i}" aria-label="Xóa mẫu ${e(s.name)}">×</button></div>`,
        )
        .join("")
    : '<div class="saved-empty"><strong>Chưa có mẫu kết nối</strong><p>Lưu thông tin nguồn để lần sau không phải nhập lại từ đầu.</p></div>';
}
$("#save-button").onclick = () => {
  const raw = Object.fromEntries(new FormData($("#connection-form")));
  const item = { kind, name: raw.name?.trim() || names[kind] };
  for (const key of [
    "auth",
    "header_name",
    "records_path",
    "sheet_mode",
    "sheet_range",
    "gid",
    "operation",
    "app_id",
    "shop_id",
    "days",
  ])
    if (raw[key]) item[key] = raw[key];
  if (raw.url) {
    try {
      const u = new URL(raw.url);
      if (u.protocol !== "https:" || u.username || u.password) throw Error();
      item.url = u.origin + u.pathname;
    } catch {
      return notify("Nhập URL HTTPS hợp lệ trước khi lưu mẫu.");
    }
  }
  try {
    const list = saved();
    const idx = list.findIndex((x) => x.name === item.name && x.kind === kind);
    if (idx >= 0) list[idx] = item;
    else list.unshift(item);
    localStorage.setItem(storageKey, JSON.stringify(list.slice(0, 20)));
    showSaved();
    notify(
      "Đã lưu mẫu trên trình duyệt. Token, khóa bí mật và tham số URL không được lưu.",
    );
  } catch {
    notify(
      "Trình duyệt không cho phép lưu. Bạn vẫn có thể lấy dữ liệu trực tiếp.",
    );
  }
};
$("#saved-list").onclick = (ev) => {
  if (busy) return;
  const open = ev.target.closest("[data-open]"),
    del = ev.target.closest("[data-delete]");
  if (open) {
    selectSource(
      saved()[Number(open.dataset.open)].kind,
      saved()[Number(open.dataset.open)],
    );
    notify("Đã mở mẫu. Nhập lại token / khóa nếu nguồn yêu cầu.");
  }
  if (del) {
    const list = saved();
    list.splice(Number(del.dataset.delete), 1);
    try {
      localStorage.setItem(storageKey, JSON.stringify(list));
      showSaved();
    } catch {
      notify("Không thể xóa mẫu trong trình duyệt này.");
    }
  }
};
function setBusy(value) {
  busy = value;
  document
    .querySelectorAll(
      "#connection-form input,#connection-form select,#connection-form button,[data-kind],#example-button,.saved-open,.delete",
    )
    .forEach((el) => (el.disabled = value));
  $("#fetch-button").textContent = value
    ? "Đang lấy dữ liệu…"
    : "↗ Kiểm tra & lấy dữ liệu";
}
async function requestData(body) {
  setBusy(true);
  $("#form-error").hidden = true;
  $("#export-actions").hidden = true;
  $("#result-body").innerHTML =
    '<div class="busy-note" role="status">Đang kết nối và chờ dữ liệu từ nguồn…</div>';
  result = null;
  try {
    const response = await fetch("/api/sources/read", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CDIP-Request": "1" },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(45000),
    });
    const data = await response.json();
    if (!response.ok)
      throw Error(data.error || "Chưa lấy được dữ liệu. Vui lòng thử lại.");
    result = data;
    lastBody = body;
    renderResults();
    $("#connection-status").textContent = "Đã lấy dữ liệu";
    $("#connection-status").className = "pill success";
  } catch (error) {
    $("#form-error").textContent = ["TimeoutError", "AbortError"].includes(
      error.name,
    )
      ? "Nguồn phản hồi quá lâu. Thu hẹp phạm vi dữ liệu rồi thử lại."
      : error instanceof TypeError
        ? "Không kết nối được. Kiểm tra mạng rồi thử lại."
        : error.message;
    $("#form-error").hidden = false;
    $("#connection-status").textContent = "Chưa kết nối được";
    $("#connection-status").className = "pill error";
    $("#result-body").innerHTML =
      '<div class="empty"><div class="empty-symbol">!</div><h3>Chưa nhận được dữ liệu</h3><p>Xem hướng dẫn sửa thông tin bên trên rồi thử lại.</p></div>';
  } finally {
    setBusy(false);
  }
}
$("#connection-form").onsubmit = (ev) => {
  ev.preventDefault();
  requestData(collect());
};
$("#connection-form").addEventListener("input", () => {
  if (!busy && result) resetResult();
});
$("#connection-form").addEventListener("change", () => {
  if (!busy && result) resetResult();
});
function cell(value) {
  return value == null
    ? ""
    : typeof value === "object"
      ? JSON.stringify(value)
      : String(value);
}
function renderResults() {
  const rows = result.rows;
  const columns = [...new Set(rows.flatMap((r) => Object.keys(r)))].slice(
    0,
    60,
  );
  const shown = rows.slice(0, 100);
  $("#export-actions").hidden = false;
  $("#result-body").innerHTML =
    `${result.example ? '<div class="result-warning">DỮ LIỆU MẪU · Chỉ dùng để thử thao tác, chưa kết nối nguồn của bạn.</div>' : ""}<div class="result-meta"><strong>${result.row_count} dòng nhận được</strong><span>HTTP ${result.http_status}</span><span>${result.elapsed_ms} ms</span><span>${(result.bytes / 1024).toFixed(1)} KB</span></div><div class="result-tabs"><button class="tab active" data-tab="table">Dạng bảng</button><button class="tab" data-tab="json">JSON gốc</button></div><div id="table-view" class="table-scroll">${rows.length ? `<table><thead><tr>${columns.map((k) => `<th>${e(k)}</th>`).join("")}</tr></thead><tbody>${shown.map((row) => `<tr>${columns.map((k) => `<td title="${e(cell(row[k]).slice(0, 500))}">${e(cell(row[k]).slice(0, 500))}</td>`).join("")}</tr>`).join("")}</tbody></table>` : '<div class="empty"><h3>Kết nối thành công, không có dòng dữ liệu</h3><p>Kiểm tra bộ lọc, khoảng ngày hoặc vùng bảng tính.</p></div>'}</div><pre id="json-view" class="raw" hidden></pre><div class="result-foot"><span>Đang xem ${shown.length}/${rows.length} dòng · ${columns.length} cột hiển thị.<br>Một phản hồi từ nguồn, chưa phải toàn bộ dữ liệu. Tệp tải chứa toàn bộ phản hồi này.</span>${result.next_cursor ? '<button class="secondary" id="next-page">Trang tiếp theo →</button>' : ""}</div>`;
  $("#json-view").textContent = JSON.stringify(result.raw, null, 2);
  $("#result-body")
    .querySelectorAll("[data-tab]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          const json = b.dataset.tab === "json";
          $("#table-view").hidden = json;
          $("#json-view").hidden = !json;
          $("#result-body")
            .querySelectorAll("[data-tab]")
            .forEach((t) => t.classList.toggle("active", t === b));
        }),
    );
  if ($("#next-page"))
    $("#next-page").onclick = () =>
      requestData({
        ...lastBody,
        cursor: result.next_cursor,
        until: result.window_end,
      });
}
function download(text, type, name) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("#export-json").onclick = () => {
  if (result)
    download(
      JSON.stringify(result.raw, null, 2),
      "application/json",
      "du-lieu-nguon.json",
    );
};
$("#export-csv").onclick = () => {
  if (!result) return;
  const cols = [...new Set(result.rows.flatMap((r) => Object.keys(r)))];
  const safe = (v) => {
    let s = cell(v);
    if (/^[\s]*[=+@-]/.test(s)) s = "'" + s;
    return '"' + s.replaceAll('"', '""') + '"';
  };
  const text = [
    cols.map(safe).join(","),
    ...result.rows.map((r) => cols.map((k) => safe(r[k])).join(",")),
  ].join("\r\n");
  download("\ufeff" + text, "text/csv;charset=utf-8", "du-lieu-nguon.csv");
};
$("#example-button").onclick = async () => {
  selectSource("website");
  setBusy(true);
  try {
    const start = performance.now();
    const r = await fetch("/api/sources/example", { cache: "no-store" });
    if (!r.ok) throw Error();
    const raw = await r.json();
    result = {
      rows: raw.items,
      raw,
      row_count: raw.items.length,
      http_status: r.status,
      elapsed_ms: Math.round(performance.now() - start),
      bytes: new TextEncoder().encode(JSON.stringify(raw)).length,
      example: true,
    };
    renderResults();
    $("#connection-status").textContent = "Đang xem API mẫu";
    $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch {
    notify("Chưa tải được API mẫu. Thử lại sau.");
  } finally {
    setBusy(false);
  }
};
document
  .querySelectorAll("[data-kind]")
  .forEach((b) => (b.onclick = () => selectSource(b.dataset.kind)));
$("#help-toggle").onclick = () => {
  $("#help").hidden = !$("#help").hidden;
  if (!$("#help").hidden)
    $("#help").scrollIntoView({ behavior: "smooth", block: "start" });
};
$("#help-close").onclick = () => ($("#help").hidden = true);
showSaved();
selectSource("website");
