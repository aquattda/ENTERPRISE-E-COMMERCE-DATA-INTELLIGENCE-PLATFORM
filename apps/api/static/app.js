import {
  businessPages,
  loadBusinessData,
  renderBusiness,
  renderDemoGuide,
} from "./business.js";
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const paths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  sources:
    '<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4 2c-1.5 1-1.5 1.5-1.5 2M12 17h.01"/>',
  logout:
    '<path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4M14 8l4 4-4 4M8 12h12"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  refresh:
    '<path d="M20 10a8 8 0 0 0-14-5L3 8m0-5v5h5M4 14a8 8 0 0 0 14 5l3-3m0 5v-5h-5"/>',
  arrow: '<path d="M5 12h14M14 7l5 5-5 5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  shield: '<path d="m12 3 8 3v6c0 4-8 9-8 9s-8-5-8-9V6zM8 12l3 3 5-6"/>',
  alert: '<path d="m12 3 10 17H2zM12 9v4M12 17h.01"/>',
  database:
    '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  file: '<path d="M14 2H5v20h14V7zM14 2v6h5M8 12h8M8 16h8"/>',
  sheets:
    '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M4 9h16M4 15h16M10 9v12"/>',
  link: '<path d="m10 13 4-4M8 16l-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m2 1 2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0" transform="translate(2 0) scale(.9)"/>',
  search: '<circle cx="10" cy="10" r="6.5"/><path d="m15 15 5 5"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  upload: '<path d="M4 16v5h16v-5M12 16V3m-5 5 5-5 5 5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  play: '<path d="m7 4 13 8-13 8z"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
};
const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
$$("[data-icon]").forEach((el) => (el.innerHTML = icon(el.dataset.icon)));
const labels = {
  ...businessPages,
  overview: "Tình trạng hệ thống",
  sources: "Nguồn dữ liệu",
  activity: "Lịch sử cập nhật",
  guide: "Hướng dẫn sử dụng",
};
const kinds = {
  rest: "Kết nối ứng dụng",
  csv: "Tệp CSV",
  sheets: "Google Sheets",
  postgres: "Cơ sở dữ liệu",
};
const statusNames = {
  succeeded: "Đã cập nhật",
  running: "Đang cập nhật",
  queued: "Đang chờ",
  failed: "Cần kiểm tra",
  paused: "Đã tạm dừng",
  pending: "Chưa cập nhật",
  delayed: "Cập nhật chậm",
};
const runKinds = {
  sync: "Cập nhật dữ liệu",
  backfill: "Đọc lại toàn bộ",
  reconcile: "Đối chiếu dữ liệu",
  webhook: "Cập nhật từ nguồn",
};
const nf = new Intl.NumberFormat("vi-VN");
const dt = new Intl.DateTimeFormat("vi-VN", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "Asia/Ho_Chi_Minh",
});
const asDate = (value) =>
  new Date(/[zZ]$|[+-]\d{2}:\d{2}$/.test(value) ? value : value + "Z");
const formatTime = (value) =>
  value ? dt.format(asDate(value)) : "Chưa có lần cập nhật";
const relative = (value) => {
  if (!value) return "Chưa cập nhật";
  const m = Math.floor((Date.now() - asDate(value)) / 60000);
  return m < 1
    ? "Vừa xong"
    : m < 60
      ? `${m} phút trước`
      : m < 1440
        ? `${Math.floor(m / 60)} giờ trước`
        : formatTime(value);
};
const intervalText = (s) =>
  s >= 86400
    ? "Mỗi ngày"
    : s >= 3600
      ? `Mỗi ${s / 3600} giờ`
      : `Mỗi ${s / 60} phút`;
const badge = (status) =>
  `<span class="badge ${status === "succeeded" ? "success" : status}">${statusNames[status] || "Chưa rõ trạng thái"}</span>`;
const symbol = (kind) =>
  `<span class="source-symbol ${esc(kind)}">${icon({ rest: "link", csv: "file", sheets: "sheets", postgres: "database" }[kind])}</span>`;
const sampleSource = (s) =>
  s.config?.base_url === "http://mock-api:9000" ||
  (s.kind === "csv" && s.config?.path === "employees.csv");
const sourceStatus = (s, c = {}) => {
  if (!s.enabled) return "paused";
  if (["running", "queued", "failed"].includes(c.latest_run?.status))
    return c.latest_run.status;
  if (
    c.last_success_at &&
    (Date.now() - asDate(c.last_success_at)) / 1000 >
      Math.max(s.sync_interval_seconds * 3, 900)
  )
    return "delayed";
  return c.latest_run?.status || "pending";
};
const state = {
  session: null,
  page: "overview",
  sources: [],
  sourceStates: {},
  sourceOffset: 0,
  sourceTotal: 0,
  sourceQuery: "",
  sourceKind: "",
  runs: [],
  runOffset: 0,
  runTotal: 0,
  runStatus: "",
  runSource: "",
  sourceNames: {},
  overview: null,
  busy: false,
  loadSerial: 0,
};
let toastTimer,
  dialogReturnFocus,
  wizard = {};
const admin = () => Boolean(state.session);
const main = $("#main"),
  dialog = $("#dialog");
const errors = {
  csv_headers:
    "Dòng đầu tiên phải có tên cột, không được trống. Tệp hỗ trợ tối đa 50 cột.",
  csv_duplicate_headers:
    "Có tên cột bị trùng. Đặt tên riêng cho từng cột rồi tải lại.",
  csv_width:
    "Một số dòng không có cùng số cột với dòng tiêu đề. Kiểm tra và xuất lại tệp CSV.",
  csv_empty:
    "Tệp chưa có dữ liệu. Thêm dữ liệu bên dưới dòng tiêu đề rồi thử lại.",
  csv_row_limit:
    "Tệp vượt quá 100.000 dòng. Nhờ người phụ trách kỹ thuật thiết lập kết nối trực tiếp cho dữ liệu lớn.",
  csv_encoding:
    "Không đọc được tệp. Hãy lưu lại dưới dạng CSV UTF-8 rồi thử lại.",
  csv_key_missing: "Không tìm thấy cột định danh đã chọn trong tệp.",
  csv_key_empty:
    "Cột định danh có ô trống hoặc mã quá dài. Mỗi dòng cần một mã riêng, tối đa 200 ký tự.",
  csv_key_duplicate:
    "Cột định danh có giá trị trùng. Chọn cột mã khác hoặc sửa các mã trùng rồi thử lại.",
  sheets_key_missing:
    "Chưa tìm thấy cột định danh trong trang tính. Kiểm tra tên cột và vùng dữ liệu.",
  sheets_connection_failed:
    "Chưa truy cập được trang tính. Kiểm tra liên kết, vùng dữ liệu và quyền chia sẻ.",
  "Source name already exists":
    "Tên nguồn này đã được sử dụng. Hãy chọn tên khác để dễ phân biệt.",
  "Source is disabled":
    "Nguồn đang tạm dừng. Bật lại nguồn trước khi cập nhật.",
  body_too_large: "Tệp quá lớn. Chọn tệp CSV có dung lượng tối đa 10 MB.",
};
function friendly(e) {
  if (e.status === 401)
    return "Phiên làm việc đang được làm mới. Vui lòng thử lại thao tác.";
  if (e.status === 403)
    return "Bạn chưa có quyền thực hiện thao tác này. Vui lòng liên hệ người phụ trách kỹ thuật.";
  if (e.status === 429)
    return "Bạn vừa thực hiện nhiều thao tác. Chờ khoảng một phút rồi thử lại.";
  if (errors[e.message]) return errors[e.message];
  if (e.status === 422)
    return "Thông tin chưa hợp lệ. Kiểm tra các trường đã nhập rồi thử lại.";
  if (e.status >= 500)
    return "Hệ thống chưa xử lý được yêu cầu. Thử lại sau ít phút; nếu vẫn lỗi, liên hệ người phụ trách kỹ thuật.";
  return "Chưa kết nối được với hệ thống. Kiểm tra kết nối mạng rồi thử lại.";
}
async function api(url, options = {}) {
  if (
    state.session?.deployment === "vercel_demo" &&
    url === "/api/v1/business/costs"
  ) {
    const key = "cdip-demo-costs-v1";
    let items;
    try {
      items = JSON.parse(localStorage.getItem(key) || "[]");
    } catch {
      items = [];
    }
    if (!Array.isArray(items)) items = [];
    if (options.method === "POST") {
      const entry = JSON.parse(options.body);
      items = items.filter(
        (c) =>
          !(
            c.sku === entry.sku &&
            c.shop_id === entry.shop_id &&
            c.currency === entry.currency &&
            c.effective_from === entry.effective_from
          ),
      );
      items.push(entry);
      localStorage.setItem(key, JSON.stringify(items));
      return { saved: true, storage: "browser" };
    }
    return { items, storage: "browser" };
  }
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof Blob))
    headers.set("Content-Type", "application/json");
  if (state.session?.csrf) headers.set("X-CSRF-Token", state.session.csrf);
  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new Error("network");
  }
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      body.error?.message || body.error?.code || "unknown",
    );
    error.status = response.status;
    if (response.status === 401 && state.session && url !== "/api/v1/session")
      startWorkspace();
    throw error;
  }
  return body;
}
function toast(message, error = false) {
  clearTimeout(toastTimer);
  const el = $("#toast");
  el.className = "toast" + (error ? " error" : "");
  el.innerHTML =
    icon(error ? "alert" : "check") + `<span>${esc(message)}</span>`;
  el.hidden = false;
  toastTimer = setTimeout(() => (el.hidden = true), error ? 8500 : 5000);
}
function showApp() {
  $("#boot-loading").hidden = true;
  $("#app-shell").hidden = false;
  $("#today").textContent = new Intl.DateTimeFormat("vi-VN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date());
  navigate();
}
function closeMenu() {
  $("#sidebar").classList.remove("open");
  $("#sidebar-backdrop").hidden = true;
  $("#menu-toggle").setAttribute("aria-expanded", "false");
}
$("#menu-toggle").addEventListener("click", () => {
  const open = !$("#sidebar").classList.contains("open");
  $("#sidebar").classList.toggle("open", open);
  $("#sidebar-backdrop").hidden = !open;
  $("#menu-toggle").setAttribute("aria-expanded", String(open));
});
$("#sidebar-backdrop").addEventListener("click", closeMenu);
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeMenu();
});
window.addEventListener("hashchange", navigate);
function navigate() {
  if (!state.session) return;
  const page = location.hash.slice(1).split("?")[0] || "business";
  state.page = labels[page] ? page : "business";
  if (
    state.session.deployment === "vercel_demo" &&
    ["overview", "sources", "activity"].includes(state.page)
  )
    state.page = "setup";
  $$("[data-nav]").forEach((el) => {
    const current = el.dataset.nav === state.page;
    el.classList.toggle("active", current);
    if (current) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  $("#page-label").textContent = labels[state.page];
  document.title = `${labels[state.page]} · CDIP`;
  closeMenu();
  loadPage(false);
  main.focus({ preventScroll: true });
}
const empty = (title, description, action = "") =>
  `<div class="empty-state"><div class="empty-icon">${icon("sources")}</div><h3>${title}</h3><p>${description}</p>${action}</div>`;
const addButton = (text = "Thêm nguồn dữ liệu") =>
  admin()
    ? `<button class="button primary" data-action="add">${icon("plus")}${text}</button>`
    : "";
const title = (heading, subtitle, actions = "") =>
  `<div class="page-title"><div><h1>${heading}</h1><p>${subtitle}</p></div><div class="title-actions">${actions}</div></div>`;
const refreshButton = () =>
  `<button class="button secondary" data-action="refresh" aria-label="Làm mới thông tin">${icon("refresh")}<span>Làm mới</span></button>`;
async function loadPage(background = false) {
  const serial = ++state.loadSerial,
    page = state.page;
  if (!background)
    main.innerHTML =
      '<div class="loading-state" role="status"><span class="spinner"></span>Đang tải thông tin…</div>';
  try {
    let payload;
    if (businessPages[page]) payload = await loadBusinessData(page, api);
    if (page === "overview")
      payload = await Promise.all([
        api("/api/v1/overview"),
        api("/api/v1/sources?limit=4"),
        api("/api/v1/pipelines/runs?limit=4"),
      ]);
    if (page === "sources")
      payload = await api(
        `/api/v1/sources?${new URLSearchParams({ limit: "10", offset: String(state.sourceOffset), q: state.sourceQuery, ...(state.sourceKind ? { kind: state.sourceKind } : {}) })}`,
      );
    if (page === "activity")
      payload = await api(
        `/api/v1/pipelines/runs?${new URLSearchParams({ limit: "10", offset: String(state.runOffset), ...(state.runStatus ? { status: state.runStatus } : {}), ...(state.runSource ? { source_id: state.runSource } : {}) })}`,
      );
    if (serial !== state.loadSerial || !state.session) return;
    if (businessPages[page]) {
      renderBusiness(page, payload, {
        cloudDemo: state.session.deployment === "vercel_demo",
        main,
        title,
        api,
        reload: () => loadPage(),
        openDialog,
        toast,
        friendly,
      });
    } else if (page === "overview") {
      const [overview, sources, runs] = payload;
      state.overview = overview;
      state.sources = sources.items;
      state.sourceStates = sources.states;
      state.runs = runs.items;
      state.sourceNames = runs.source_names;
      renderOverview();
    } else if (page === "sources") {
      state.sources = payload.items;
      state.sourceStates = payload.states;
      state.sourceTotal = payload.total;
      renderSources();
    } else if (page === "activity") {
      state.runs = payload.items;
      state.runTotal = payload.total;
      state.sourceNames = payload.source_names;
      renderActivity();
    } else renderDemoGuide({ main, title });
    $("#connection-note").hidden = true;
    $("#last-refreshed").textContent =
      `Thông tin mới nhất lúc ${new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Ho_Chi_Minh" }).format(new Date())} · Giờ Việt Nam`;
  } catch (e) {
    if (!state.session || serial !== state.loadSerial) return;
    if (!background)
      main.innerHTML = empty(
        "Chưa tải được thông tin",
        esc(friendly(e)),
        '<button class="button primary" data-action="refresh">Thử lại</button>',
      );
    else {
      $("#connection-note").hidden = false;
      $("#connection-note").textContent =
        "Chưa lấy được thông tin mới. Dữ liệu bên dưới là lần tải gần nhất. Hãy thử làm mới.";
    }
  }
}
function sourceName(s) {
  return `<div class="source-name">${symbol(s.kind)}<div><button data-action="source" data-id="${esc(s.id)}"><strong>${esc(s.name)}</strong></button><small>${kinds[s.kind]}${sampleSource(s) ? '<span class="tag">Dữ liệu mẫu</span>' : ""}</small></div></div>`;
}
function overviewSourceRow(s) {
  const c = state.sourceStates[s.id],
    status = sourceStatus(s, c);
  return `<tr><td>${sourceName(s)}</td><td class="hide-mobile">${badge(status)}<small class="muted" title="${esc(formatTime(c.last_success_at))}">${relative(c.last_success_at)}</small></td><td><button class="button secondary small" data-action="${admin() && s.enabled ? "sync" : "source"}" data-id="${esc(s.id)}" ${["running", "queued"].includes(status) && admin() && s.enabled ? "disabled" : ""}>${admin() && s.enabled ? "Cập nhật" : "Xem nguồn"}</button></td></tr>`;
}
function activityRows(runs) {
  return runs
    .map(
      (r) =>
        `<div class="activity-row"><span class="activity-dot ${r.status}">${icon(r.status === "succeeded" ? "check" : r.status === "failed" ? "alert" : "clock")}</span><div class="activity-description"><button class="text-link" data-action="run" data-id="${esc(r.id)}"><strong>${esc(state.sourceNames[r.source_id] || "Nguồn dữ liệu")}</strong></button><p>${statusNames[r.status]}${r.status === "succeeded" ? ` · ${nf.format(r.rows_inserted)} phiên bản mới` : ""}</p></div><span class="activity-time" title="${esc(formatTime(r.created_at))}">${relative(r.created_at)}</span></div>`,
    )
    .join("");
}
function metric(label, value, note, name, cls = "") {
  return `<article class="metric ${cls}"><div class="metric-label">${label}${icon(name)}</div><div class="metric-number">${nf.format(value || 0)}</div><p class="metric-note">${note}</p></article>`;
}
function renderOverview() {
  const o = state.overview;
  main.innerHTML =
    title(
      "Mọi dữ liệu, một nơi quản lý",
      "Theo dõi nguồn dữ liệu và các lần cập nhật của bạn.",
      refreshButton() + addButton(),
    ) +
    `<div class="metric-grid">${metric("Nguồn dữ liệu", o.source_count, `${o.active_sources} nguồn đang bật`, "sources")}${metric("Đã có dữ liệu", o.updated_sources, "Nguồn đã cập nhật thành công", "check")}${metric("Phiên bản đã lưu", o.raw_versions, "Bao gồm lịch sử thay đổi", "database")}${metric("Cần chú ý", o.attention_count, "Nguồn gặp lỗi hoặc cập nhật chậm", "alert", o.attention_count ? "attention" : "")}</div>` +
    `<section class="health-banner ${o.attention_count ? "warning" : ""}"><div class="health-icon">${icon(o.attention_count ? "alert" : "check")}</div><div><h2>${o.attention_count ? "Có nguồn dữ liệu cần kiểm tra" : o.source_count ? "Chưa ghi nhận nguồn cần chú ý" : "Bắt đầu với nguồn dữ liệu đầu tiên"}</h2><p>${o.attention_count ? "Mở nguồn bên dưới để xem trạng thái và thử cập nhật lại." : o.source_count ? "Kiểm tra lần cập nhật gần nhất trước khi sử dụng dữ liệu." : "Bạn có thể thử bằng một tệp CSV. Chỉ mất vài bước."}</p></div><button class="button secondary small" data-action="go-sources">Xem nguồn dữ liệu ${icon("arrow")}</button></section>` +
    (o.sample_source_count > 0
      ? `<div class="sample-note">${icon("info")}Có dữ liệu mẫu trong không gian này. Các con số bên trên chưa đại diện cho hoạt động kinh doanh thực tế.</div>`
      : "") +
    `<div class="overview-grid"><div class="main-column">${o.attention_count ? `<section class="panel"><div class="panel-head"><h2>Cần bạn xem lại</h2></div><div class="panel-body">${o.attention.map((a) => `<p><button class="text-link" data-action="source" data-id="${esc(a.source_id)}">${esc(a.name)} · ${statusNames[a.reason]} ${icon("arrow")}</button></p>`).join("")}</div></section>` : ""}<section class="panel"><div class="panel-head"><div><h2>Nguồn dữ liệu của bạn</h2><p>Cập nhật tự động theo lịch đã đặt</p></div><a class="text-link" href="#sources">Xem tất cả ${icon("arrow")}</a></div>${state.sources.length ? `<div class="table-wrap"><table class="overview-sources"><thead><tr><th>Nguồn dữ liệu</th><th class="hide-mobile">Trạng thái</th><th><span class="sr-only">Thao tác</span></th></tr></thead><tbody>${state.sources.map(overviewSourceRow).join("")}</tbody></table></div>` : empty("Chưa có nguồn dữ liệu", "Thêm tệp CSV hoặc kết nối Google Sheets để bắt đầu.", addButton())}</section><section class="panel"><div class="panel-head"><div><h2>Hoạt động gần đây</h2><p>Biết dữ liệu đã được cập nhật đến đâu</p></div><a class="text-link" href="#activity">Xem lịch sử ${icon("arrow")}</a></div>${state.runs.length ? `<div class="activity-list">${activityRows(state.runs)}</div>` : empty("Chưa có lần cập nhật", "Lịch sử sẽ xuất hiện sau khi bạn thêm nguồn dữ liệu.")}</section></div><aside class="side-column"><section class="help-panel"><span class="eyebrow">BẮT ĐẦU THẬT ĐƠN GIẢN</span><h2>Dữ liệu sẵn sàng<br>qua 3 bước</h2><p>Không cần viết mã hay cài thêm công cụ.</p>${[
      ["Thêm nguồn", "Tải tệp CSV hoặc kết nối bảng tính."],
      ["Kiểm tra thông tin", "Xem trước và chọn mã riêng cho mỗi dòng."],
      ["Theo dõi cập nhật", "Hệ thống lưu kết quả vào lịch sử."],
    ]
      .map(
        (s, i) =>
          `<div class="mini-step"><span class="step-number">${i + 1}</span><div><strong>${s[0]}</strong><p>${s[1]}</p></div></div>`,
      )
      .join(
        "",
      )}<a class="button secondary" href="#guide">Xem hướng dẫn ${icon("arrow")}</a></section><section class="info-panel"><div class="info-title">${icon("shield")}Lưu lại mỗi thay đổi</div><p>Dữ liệu được giữ kèm lịch sử. “Phiên bản đã lưu” có thể gồm nhiều lần thay đổi của cùng một dòng, không phải số đơn hàng hay doanh thu.</p></section></aside></div>`;
}
function pagination(offset, total, scope) {
  return `<div class="panel-foot"><span>${total ? `${offset + 1}–${Math.min(offset + 10, total)} trong ${nf.format(total)}` : "0 kết quả"}</span><div class="pagination"><button class="button secondary small" data-action="page" data-scope="${scope}" data-offset="${Math.max(0, offset - 10)}" ${offset === 0 ? "disabled" : ""}>Trước</button><button class="button secondary small" data-action="page" data-scope="${scope}" data-offset="${offset + 10}" ${offset + 10 >= total ? "disabled" : ""}>Sau</button></div></div>`;
}
function renderSources() {
  main.innerHTML =
    title(
      "Nguồn dữ liệu",
      "Thêm, cập nhật và quản lý từng nguồn tại đây.",
      refreshButton() + addButton(),
    ) +
    `<section class="panel"><form id="source-filter" class="filters"><label class="sr-only" for="source-search">Tìm tên nguồn</label><div class="search-box">${icon("search")}<input id="source-search" name="q" placeholder="Tìm theo tên nguồn…" value="${esc(state.sourceQuery)}" maxlength="120"></div><label class="sr-only" for="source-kind">Loại nguồn</label><select id="source-kind" name="kind"><option value="">Tất cả loại nguồn</option>${Object.entries(
      kinds,
    )
      .map(
        ([k, v]) =>
          `<option value="${k}" ${state.sourceKind === k ? "selected" : ""}>${v}</option>`,
      )
      .join(
        "",
      )}</select><button class="button secondary" type="submit">Tìm kiếm</button>${state.sourceQuery || state.sourceKind ? '<button class="text-link" type="button" data-action="clear-filters">Bỏ bộ lọc</button>' : ""}</form>${
      state.sources.length
        ? `<div class="table-wrap"><table class="source-table"><thead><tr><th>Nguồn dữ liệu</th><th>Trạng thái</th><th>Cập nhật gần nhất</th><th>Lịch tự động</th><th><span class="sr-only">Thao tác</span></th></tr></thead><tbody>${state.sources
            .map((s) => {
              const c = state.sourceStates[s.id],
                status = sourceStatus(s, c);
              return `<tr><td>${sourceName(s)}</td><td>${badge(status)}</td><td>${esc(formatTime(c.last_success_at))}</td><td>${s.enabled ? intervalText(s.sync_interval_seconds) : "Đã tạm dừng"}</td><td><div class="row-actions"><button class="button secondary small" data-action="source" data-id="${esc(s.id)}">Chi tiết</button>${admin() && s.enabled ? `<button class="button quiet small" data-action="sync" data-id="${esc(s.id)}" ${["queued", "running"].includes(status) ? "disabled" : ""}>Cập nhật</button>` : ""}</div></td></tr>`;
            })
            .join("")}</tbody></table></div>`
        : empty(
            state.sourceQuery || state.sourceKind
              ? "Không tìm thấy nguồn phù hợp"
              : "Chưa có nguồn dữ liệu",
            state.sourceQuery || state.sourceKind
              ? "Thử tên khác hoặc bỏ bộ lọc."
              : "Thêm nguồn đầu tiên để tập hợp dữ liệu vào một nơi.",
            state.sourceQuery || state.sourceKind ? "" : addButton(),
          )
    }${pagination(state.sourceOffset, state.sourceTotal, "source")}</section>`;
  $("#source-filter").onsubmit = (e) => {
    e.preventDefault();
    state.sourceQuery = $("#source-search").value.trim();
    state.sourceKind = $("#source-kind").value;
    state.sourceOffset = 0;
    loadPage();
  };
}
function renderActivity() {
  main.innerHTML =
    title(
      "Lịch sử cập nhật",
      "Kiểm tra kết quả mỗi lần hệ thống lấy dữ liệu.",
      refreshButton(),
    ) +
    `<section class="panel"><form id="run-filter" class="filters"><label for="run-status">Trạng thái</label><select id="run-status"><option value="">Tất cả trạng thái</option>${["succeeded", "running", "queued", "failed"].map((s) => `<option value="${s}" ${s === state.runStatus ? "selected" : ""}>${statusNames[s]}</option>`).join("")}</select><label for="run-source">Nguồn</label><select id="run-source"><option value="">Tất cả nguồn</option>${Object.entries(
      state.sourceNames,
    )
      .map(
        ([id, name]) =>
          `<option value="${esc(id)}" ${id === state.runSource ? "selected" : ""}>${esc(name)}</option>`,
      )
      .join(
        "",
      )}</select><button class="button secondary" type="submit">Áp dụng</button></form>${state.runs.length ? `<div class="table-wrap"><table class="activity-table"><thead><tr><th>Nguồn dữ liệu</th><th>Trạng thái</th><th>Thời gian yêu cầu</th><th>Phiên bản mới</th><th></th></tr></thead><tbody>${state.runs.map((r) => `<tr><td><strong>${esc(state.sourceNames[r.source_id] || "Nguồn dữ liệu")}</strong><small class="muted">${runKinds[r.kind] || "Cập nhật dữ liệu"}</small></td><td>${badge(r.status)}</td><td>${esc(formatTime(r.created_at))}</td><td class="numbers">${nf.format(r.rows_inserted || 0)}</td><td><button class="button secondary small" data-action="run" data-id="${esc(r.id)}">Xem kết quả</button></td></tr>`).join("")}</tbody></table></div>` : empty("Chưa có kết quả", "Các lần cập nhật phù hợp với bộ lọc sẽ xuất hiện ở đây.")}${pagination(state.runOffset, state.runTotal, "run")}</section>`;
  $("#run-filter").onsubmit = (e) => {
    e.preventDefault();
    state.runStatus = $("#run-status").value;
    state.runSource = $("#run-source").value;
    state.runOffset = 0;
    loadPage();
  };
}
function renderGuide() {
  main.innerHTML =
    title(
      "Bắt đầu thật đơn giản",
      "Chọn việc bạn muốn làm và làm theo từng bước.",
    ) +
    `<div class="guide-cards">${[
      [
        "1",
        "Thêm dữ liệu",
        "Vào Nguồn dữ liệu → Thêm nguồn dữ liệu. Chọn tệp CSV hoặc Google Sheets.",
      ],
      [
        "2",
        "Kiểm tra trước khi nhập",
        "Đặt tên dễ nhớ và chọn cột mã riêng cho mỗi dòng, chẳng hạn mã đơn hàng.",
      ],
      [
        "3",
        "Xem kết quả cập nhật",
        "Mở Lịch sử cập nhật. Trạng thái “Đã cập nhật” cho biết hệ thống đã hoàn tất.",
      ],
    ]
      .map(
        (s) =>
          `<article class="guide-card"><span class="step-number">${s[0]}</span><h3>${s[1]}</h3><p>${s[2]}</p></article>`,
      )
      .join(
        "",
      )}</div><div class="guide-layout"><section class="panel"><div class="panel-head"><h2>Những điều thường gặp</h2></div><div class="guide-list">${[
      [
        "Tôi có tệp Excel, cần làm gì?",
        "Mở tệp trong Excel, chọn Lưu thành (Save As) → CSV UTF-8. Mỗi tệp chứa một trang tính. Dòng đầu tiên là tên cột; dữ liệu bắt đầu từ dòng thứ hai. Tối đa 10 MB, 100.000 dòng và 50 cột.",
      ],
      [
        "“Cột mã riêng” là gì?",
        "Là cột phân biệt từng dòng, ví dụ ma_don_hang hoặc ma_nhan_vien. Mỗi dòng cần một mã khác nhau và không để trống. Tránh chọn họ tên vì có thể trùng.",
      ],
      [
        "Tệp CSV có tự cập nhật khi tôi sửa trên máy không?",
        "Không. Hệ thống lưu bản sao tại thời điểm tải lên. Khi có tệp mới, thêm một nguồn với tên khác để phân biệt. Muốn theo dõi thay đổi tự động, hãy dùng Google Sheets hoặc nhờ người phụ trách kỹ thuật kết nối nguồn trực tiếp.",
      ],
      [
        "Tôi kết nối Google Sheets như thế nào?",
        "Người phụ trách kỹ thuật thiết lập tài khoản kết nối một lần. Sau đó bạn dán liên kết trang tính, nhập vùng dữ liệu và cột mã riêng. Chia sẻ quyền xem trang tính cho tài khoản kết nối do người phụ trách kỹ thuật cung cấp.",
      ],
      [
        "“Đang chờ” có phải là lỗi không?",
        "Không. Yêu cầu đã được tiếp nhận và đang chờ xử lý. Bạn có thể đóng cửa sổ này; hệ thống tiếp tục cập nhật. Mở lịch sử để xem kết quả mới nhất.",
      ],
      [
        "Nguồn báo “Cần kiểm tra”, tôi nên làm gì?",
        "Mở nguồn để xem hướng dẫn. Kiểm tra quyền truy cập, đường dẫn hoặc tệp rồi chọn Cập nhật ngay. Nếu lỗi lặp lại, gửi mã lần cập nhật trong mục Thông tin hỗ trợ cho người phụ trách kỹ thuật.",
      ],
      [
        "Tạm dừng có xóa dữ liệu không?",
        "Không. Tạm dừng ngăn các lần cập nhật mới. Dữ liệu và lịch sử đã lưu vẫn được giữ; một lần cập nhật đang chạy có thể tiếp tục đến khi hoàn tất.",
      ],
      [
        "Tại sao số phiên bản nhiều hơn số dòng?",
        "Mỗi thay đổi có thể tạo thêm một phiên bản lịch sử. Đây là số phiên bản đã lưu, không phải số đơn hàng, khách hàng hay doanh thu.",
      ],
      [
        "Ai có thể sử dụng không gian này?",
        "Mọi người trong nội bộ dùng chung các nguồn dữ liệu và lịch sử. Bạn có thể thêm nguồn, tải tệp hoặc thay đổi lịch cập nhật mà không cần tạo tài khoản.",
      ],
    ]
      .map(([q, a]) => `<details><summary>${q}</summary><p>${a}</p></details>`)
      .join(
        "",
      )}</div></section><aside class="side-column"><section class="help-panel"><span class="eyebrow">THỬ MỘT LẦN LÀ QUEN</span><h2>Bắt đầu bằng tệp mẫu</h2><p>Tệp gồm ba nhân viên giả lập để bạn thử cách nhập dữ liệu.</p><a class="button secondary" href="/assets/mau-nhan-vien.csv" download>Tải tệp CSV mẫu ${icon("file")}</a></section><section class="info-panel"><div class="info-title">${icon("clock")}Hiểu các trạng thái</div><p>Đang chờ → Đang cập nhật → Đã cập nhật.</p><p>“Cần kiểm tra” là lần cập nhật gặp lỗi. “Cập nhật chậm” là nguồn lâu chưa có lần cập nhật thành công.</p></section></aside></div>`;
}
function openDialog(heading, description, body, footer = "") {
  if (!dialog.open) dialogReturnFocus = document.activeElement;
  dialog.innerHTML = `<div class="modal-head"><div><h2 id="dialog-title" tabindex="-1">${esc(heading)}</h2><p>${esc(description)}</p></div><button class="icon-button" aria-label="Đóng" data-action="close">${icon("close")}</button></div><div class="modal-body">${body}<div id="dialog-error" class="form-error" role="alert" hidden></div></div><div class="modal-foot">${footer || '<button class="button secondary" data-action="close">Đóng</button>'}</div>`;
  if (!dialog.open) dialog.showModal();
  $("#dialog-title").focus();
}
dialog.addEventListener("close", () => {
  wizard = {};
  if (dialogReturnFocus?.isConnected) dialogReturnFocus.focus();
});
function dialogError(e) {
  const el = $("#dialog-error");
  if (el) {
    el.textContent = friendly(e);
    el.hidden = false;
    el.scrollIntoView({ block: "nearest" });
  } else toast(friendly(e), true);
}
function addSource() {
  wizard = {};
  openDialog(
    "Thêm nguồn dữ liệu",
    "Chọn nơi đang lưu dữ liệu của bạn.",
    `<div class="source-options">${[
      [
        "csv-start",
        "csv",
        "Tải tệp CSV",
        "Dễ bắt đầu · Có thể xuất tệp từ Excel",
      ],
      [
        "sheets-start",
        "sheets",
        "Kết nối Google Sheets",
        "Tự cập nhật khi bảng tính thay đổi",
      ],
      [
        "other",
        "rest",
        "Kết nối ứng dụng khác",
        "Dành cho kết nối đã được đội kỹ thuật thiết lập",
      ],
    ]
      .map(
        ([action, kind, label, desc]) =>
          `<button class="source-option" data-action="${action}">${symbol(kind)}<div><strong>${label}</strong><p>${desc}</p></div>${icon("chevron")}</button>`,
      )
      .join("")}</div>`,
  );
}
function stepper(step) {
  return `<div class="stepper">${["Chọn tệp", "Kiểm tra", "Hoàn tất"].map((s, i) => `${i ? "<i></i>" : ""}<span class="${step === i + 1 ? "current" : ""}"><b>${i + 1}</b>${s}</span>`).join("")}</div>`;
}
function csvStart() {
  wizard = {};
  openDialog(
    "Nhập dữ liệu từ tệp CSV",
    "Bước 1 · Chọn tệp trên máy tính của bạn.",
    `${stepper(1)}<div class="file-drop">${icon("upload")}<label for="csv-file">Chọn tệp CSV</label><p>Tối đa 10 MB · 100.000 dòng · 50 cột</p><input id="csv-file" type="file" accept=".csv,text/csv"></div><p class="field-hint">Nếu đang dùng Excel, chọn Lưu thành → CSV UTF-8. Dòng đầu tiên cần chứa tên các cột.</p><a class="text-link" href="/assets/mau-nhan-vien.csv" download>Tải tệp mẫu để thử ${icon("file")}</a>`,
    `<button class="button secondary" data-action="add">Quay lại</button><button class="button primary" data-action="csv-preview">Xem trước dữ liệu ${icon("arrow")}</button>`,
  );
}
async function csvPreview(button) {
  const file = $("#csv-file").files[0];
  if (!file) {
    $("#dialog-error").textContent = "Chọn một tệp CSV trước khi tiếp tục.";
    $("#dialog-error").hidden = false;
    return;
  }
  if (file.size > 10485760) {
    dialogError({ message: "body_too_large" });
    return;
  }
  button.disabled = true;
  try {
    const preview = await api("/api/v1/imports/csv/preview", {
      method: "POST",
      body: file,
    });
    if (!dialog.open) return;
    wizard = { file, preview };
    csvReview();
  } catch (e) {
    dialogError(e);
  } finally {
    button.disabled = false;
  }
}
function csvReview() {
  const { file, preview: p } = wizard;
  openDialog(
    "Kiểm tra trước khi nhập",
    "Bước 2 · Đặt tên nguồn và chọn cột phân biệt từng dòng.",
    `${stepper(2)}<div class="notice">${icon("file")}<span>${esc(file.name)} · ${nf.format(p.row_count)} dòng dữ liệu · Hiển thị tối đa 5 dòng đầu.</span></div><form id="csv-form"><div class="field"><label for="csv-name">Tên nguồn dữ liệu</label><input id="csv-name" required maxlength="120" value="${esc(file.name.replace(/\.csv$/i, ""))}" placeholder="Ví dụ: Đơn hàng tháng 10"></div><div class="field"><label for="csv-key">Cột mã riêng cho mỗi dòng</label><select id="csv-key">${p.headers.map((h) => `<option ${h === p.suggested_key ? "selected" : ""}>${esc(h)}</option>`).join("")}</select><span class="field-hint">Ví dụ mã đơn hàng hoặc mã nhân viên. Mã không được trùng hoặc để trống.</span></div></form><div class="preview-table"><table><thead><tr>${p.headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${p.sample.map((row) => `<tr>${row.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div><div class="notice warning">${icon("info")}Hệ thống lưu bản sao của tệp này. Sửa tệp trên máy tính sẽ không tự thay đổi dữ liệu đã tải lên.</div>`,
    `<button class="button secondary" data-action="csv-start">Chọn tệp khác</button><button id="csv-submit" class="button primary" type="submit" form="csv-form">Nhập ${nf.format(p.row_count)} dòng ${icon("arrow")}</button>`,
  );
  $("#csv-form").onsubmit = async (e) => {
    e.preventDefault();
    const b = $("#csv-submit"),
      name = $("#csv-name").value.trim();
    if (!name) {
      $("#csv-name").focus();
      return;
    }
    b.disabled = true;
    try {
      const result = await api(
        `/api/v1/imports/csv?${new URLSearchParams({ name, key_field: $("#csv-key").value })}`,
        { method: "POST", body: file },
      );
      receipt(name, result);
      loadPage(true);
    } catch (error) {
      dialogError(error);
      b.disabled = false;
    }
  };
}
function receipt(name, result) {
  openDialog(
    "Đã tiếp nhận dữ liệu",
    "Bạn có thể tiếp tục công việc trong khi hệ thống xử lý.",
    `${stepper(3)}<div class="success-body"><div class="success-art">${icon("check")}</div><h3>${esc(name)}</h3><p>${result.row_count ? `${nf.format(result.row_count)} dòng đã được tiếp nhận. ` : ""}Yêu cầu đang chờ xử lý. Xem lịch sử để biết khi nào dữ liệu đã cập nhật xong.</p></div>`,
    `<button class="button secondary" data-action="go-sources">Xem nguồn dữ liệu</button><button class="button primary" data-action="source-activity" data-id="${esc(result.source_id)}">Theo dõi cập nhật ${icon("arrow")}</button>`,
  );
}
async function sheetsStart() {
  openDialog(
    "Kết nối Google Sheets",
    "Đang kiểm tra kết nối có sẵn…",
    '<div class="loading-state"><span class="spinner"></span>Đang kiểm tra</div>',
  );
  try {
    const accounts = await api("/api/v1/connections");
    if (!dialog.open) return;
    if (!accounts.google.length) {
      openDialog(
        "Chuẩn bị kết nối Google Sheets",
        "Cần thiết lập kết nối một lần trước khi sử dụng.",
        `<div class="notice">${icon("info")}Nhờ người phụ trách kỹ thuật thiết lập tài khoản Google cho hệ thống và cung cấp địa chỉ email để chia sẻ trang tính.</div><p class="field-hint">Bạn vẫn có thể bắt đầu ngay: trong Google Sheets, chọn Tệp → Tải xuống → Giá trị được phân tách bằng dấu phẩy (.csv), sau đó tải tệp lên.</p>`,
        `<button class="button secondary" data-action="add">Quay lại</button><button class="button primary" data-action="csv-start">Dùng tệp CSV trước</button>`,
      );
      return;
    }
    openDialog(
      "Kết nối Google Sheets",
      "Trang tính cần được chia sẻ quyền xem cho tài khoản kết nối.",
      `<form id="sheets-form"><div class="field"><label for="sheet-name">Tên nguồn dữ liệu</label><input id="sheet-name" required maxlength="120" placeholder="Ví dụ: Danh sách sản phẩm"></div><div class="field"><label for="sheet-url">Liên kết Google Sheets</label><input id="sheet-url" required type="url" placeholder="https://docs.google.com/spreadsheets/d/…"></div><div class="field"><label for="sheet-range">Trang và vùng dữ liệu</label><input id="sheet-range" required value="Sheet1!A:Z"><span class="field-hint">Ví dụ: Sheet1!A:Z. Dòng đầu tiên phải là tên cột.</span></div><div class="field"><label for="sheet-key">Tên cột mã riêng</label><input id="sheet-key" required placeholder="Ví dụ: ma_san_pham"></div><details class="technical"><summary>Thiết lập kết nối có sẵn</summary><div class="field"><label for="sheet-account">Kết nối</label><select id="sheet-account">${accounts.google.map((ref, i) => `<option value="${esc(ref)}">Kết nối Google ${i + 1} · ${esc(ref.replace("env:CDIP_SECRET_GOOGLE", "")) || "Mặc định"}</option>`).join("")}</select></div><div class="field"><label for="sheet-auth">Kiểu xác thực</label><select id="sheet-auth"><option value="service_account">Tài khoản dịch vụ</option><option value="oauth_token">Mã truy cập OAuth</option></select></div></details></form>`,
      `<button class="button secondary" data-action="add">Quay lại</button><button id="sheets-submit" class="button primary" type="submit" form="sheets-form">Kiểm tra và kết nối</button>`,
    );
    $("#sheets-form").onsubmit = async (e) => {
      e.preventDefault();
      const match = $("#sheet-url").value.match(
        /^https:\/\/docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/,
      );
      if (!match) {
        $("#dialog-error").hidden = false;
        $("#dialog-error").textContent =
          "Dán liên kết trang tính từ docs.google.com/spreadsheets.";
        return;
      }
      const name = $("#sheet-name").value.trim(),
        config = {
          kind: "sheets",
          spreadsheet_id: match[1],
          ranges: [$("#sheet-range").value.trim()],
          key_field: $("#sheet-key").value.trim(),
          secret_ref: $("#sheet-account").value,
          auth: $("#sheet-auth").value,
          entity: "imported_records",
        };
      const b = $("#sheets-submit");
      b.disabled = true;
      try {
        await api("/api/v1/connections/sheets/test", {
          method: "POST",
          body: JSON.stringify(config),
        });
        const source = await api("/api/v1/sources", {
          method: "POST",
          body: JSON.stringify({ name, config, sync_interval_seconds: 300 }),
        });
        try {
          await api(`/api/v1/sources/${encodeURIComponent(source.id)}/sync`, {
            method: "POST",
          });
          receipt(name, { source_id: source.id });
        } catch {
          openDialog(
            "Nguồn đã được tạo",
            "Chưa gửi được yêu cầu cập nhật.",
            `<p>Mở nguồn <strong>${esc(name)}</strong> và chọn Cập nhật ngay để thử lại.</p>`,
            `<button class="button primary" data-action="source" data-id="${esc(source.id)}">Mở nguồn</button>`,
          );
        }
        loadPage(true);
      } catch (error) {
        dialogError(error);
        b.disabled = false;
      }
    };
  } catch (e) {
    dialogError(e);
  }
}
function otherConnection() {
  openDialog(
    "Kết nối ứng dụng khác",
    "Nhờ người phụ trách kỹ thuật thiết lập kết nối một lần.",
    `<p>Hệ thống hỗ trợ kết nối ứng dụng qua API và cơ sở dữ liệu PostgreSQL. Khi kết nối được thiết lập, nguồn sẽ xuất hiện tại mục Nguồn dữ liệu để mọi người cùng sử dụng.</p><div class="field notice">${icon("info")}Nếu có tệp xuất từ ứng dụng, bạn có thể dùng tệp CSV ngay.</div>`,
    `<button class="button secondary" data-action="add">Quay lại</button><button class="button primary" data-action="csv-start">Nhập tệp CSV</button>`,
  );
}
async function showSource(id) {
  openDialog(
    "Thông tin nguồn",
    "Đang tải thông tin…",
    '<span class="spinner"></span>',
  );
  try {
    const [data, history] = await Promise.all([
      api(`/api/v1/sources/${encodeURIComponent(id)}`),
      api(`/api/v1/pipelines/runs?source_id=${encodeURIComponent(id)}&limit=1`),
    ]);
    if (!dialog.open) return;
    const s = data.source,
      c = data.sync_state || {},
      r = history.items[0],
      status = sourceStatus(s, { ...c, latest_run: r });
    const scheduleOptions = [60, 300, 900, 3600, 21600, 86400];
    if (!scheduleOptions.includes(s.sync_interval_seconds))
      scheduleOptions.push(s.sync_interval_seconds);
    openDialog(
      s.name,
      kinds[s.kind] + (sampleSource(s) ? " · Dữ liệu mẫu" : ""),
      `${badge(status)}<dl class="detail-grid"><div><dt>Cập nhật thành công gần nhất</dt><dd>${esc(formatTime(c.last_success_at))}</dd></div><div><dt>Lịch cập nhật</dt><dd>${s.enabled ? intervalText(s.sync_interval_seconds) : "Đã tạm dừng"}</dd></div></dl>${status === "failed" ? `<div class="notice warning">${icon("alert")}Lần cập nhật gần nhất chưa hoàn tất. Kiểm tra quyền truy cập hoặc dữ liệu nguồn rồi thử cập nhật lại.</div>` : ""}${s.kind === "csv" ? `<div class="notice">${icon("info")}Đây là bản sao của tệp CSV đã tải lên. Thay đổi tệp trên máy tính không tự cập nhật bản sao này.</div>` : ""}<button class="text-link" data-action="source-activity" data-id="${esc(id)}">Xem lịch sử của nguồn ${icon("arrow")}</button>${
        admin()
          ? `<form id="schedule-form"><div class="field"><label for="schedule">Tự kiểm tra nguồn</label><select id="schedule">${scheduleOptions
              .sort((a, b) => a - b)
              .map(
                (v) =>
                  `<option value="${v}" ${v === s.sync_interval_seconds ? "selected" : ""}>${intervalText(v)}</option>`,
              )
              .join(
                "",
              )}</select><span class="field-hint">Lịch chạy khi nguồn đang bật. Thay đổi được áp dụng cho các lần cập nhật tiếp theo.</span></div><button class="button secondary small" type="submit">Lưu lịch cập nhật</button></form><details class="technical"><summary>Thao tác khác</summary><p class="field-hint">Tạm dừng giữ nguyên dữ liệu và lịch sử đã lưu. Lần cập nhật đang chạy có thể tiếp tục.</p><button class="button secondary small" data-action="toggle" data-id="${esc(id)}" data-enabled="${!s.enabled}">${s.enabled ? "Tạm dừng nguồn" : "Bật lại nguồn"}</button>${s.enabled ? `<p class="field-hint">Đọc lại toàn bộ dùng khi cần kiểm tra lại dữ liệu cũ; có thể mất nhiều thời gian.</p><button class="button secondary small" data-action="backfill-confirm" data-id="${esc(id)}">Đọc lại toàn bộ dữ liệu</button>` : ""}</details>`
          : ""
      }`,
      `<button class="button secondary" data-action="close">Đóng</button>${admin() && s.enabled ? `<button class="button primary" data-action="sync" data-id="${esc(id)}" ${["running", "queued"].includes(status) ? "disabled" : ""}>${["running", "queued"].includes(status) ? statusNames[status] : "Cập nhật ngay"}</button>` : ""}`,
    );
    const form = $("#schedule-form");
    if (form)
      form.onsubmit = async (e) => {
        e.preventDefault();
        const b = $("button", form);
        b.disabled = true;
        try {
          await api(`/api/v1/sources/${encodeURIComponent(id)}`, {
            method: "PATCH",
            body: JSON.stringify({
              sync_interval_seconds: Number($("#schedule").value),
            }),
          });
          toast("Đã lưu lịch cập nhật.");
          await showSource(id);
          loadPage(true);
        } catch (error) {
          dialogError(error);
          b.disabled = false;
        }
      };
  } catch (e) {
    dialogError(e);
  }
}
async function showRun(id) {
  openDialog(
    "Kết quả cập nhật",
    "Đang tải thông tin…",
    '<span class="spinner"></span>',
  );
  try {
    const r = await api(`/api/v1/pipelines/runs/${encodeURIComponent(id)}`);
    if (!dialog.open) return;
    openDialog(
      "Kết quả cập nhật",
      state.sourceNames[r.source_id] || "Chi tiết một lần cập nhật",
      `${badge(r.status)}<dl class="detail-grid"><div><dt>Thời gian yêu cầu</dt><dd>${esc(formatTime(r.created_at))}</dd></div><div><dt>Loại cập nhật</dt><dd>${runKinds[r.kind] || "Cập nhật dữ liệu"}</dd></div><div><dt>Số dòng đã đọc</dt><dd>${nf.format(r.rows_fetched || 0)}</dd></div><div><dt>Phiên bản mới đã lưu</dt><dd>${nf.format(r.rows_inserted || 0)}</dd></div></dl><div class="notice ${r.status === "failed" ? "warning" : ""}">${icon(r.status === "failed" ? "alert" : "info")}${r.status === "failed" ? "Lần cập nhật này gặp lỗi. Kiểm tra quyền truy cập và cấu trúc dữ liệu nguồn. Nếu lỗi tiếp diễn, gửi mã hỗ trợ bên dưới cho người phụ trách kỹ thuật." : r.status === "succeeded" ? "Đã hoàn tất lần cập nhật. Không có phiên bản mới cũng là bình thường nếu dữ liệu không thay đổi." : "Yêu cầu đang được xử lý. Bạn có thể đóng cửa sổ này rồi làm mới lịch sử sau ít phút."}</div><details class="technical"><summary>Thông tin hỗ trợ</summary><p class="field-hint">Mã lần cập nhật: <code>${esc(r.id)}</code></p>${r.error_code ? `<p class="field-hint">Mã lỗi: <code>${esc(r.error_code)}</code></p>` : ""}</details>`,
      `<button class="button secondary" data-action="close">Đóng</button><button class="button primary" data-action="source" data-id="${esc(r.source_id)}">Xem nguồn dữ liệu</button>`,
    );
  } catch (e) {
    dialogError(e);
  }
}
async function syncSource(id, button, backfill = false) {
  button.disabled = true;
  try {
    await api(
      backfill
        ? `/api/v1/pipelines/${encodeURIComponent(id)}/backfill`
        : `/api/v1/sources/${encodeURIComponent(id)}/sync`,
      { method: "POST" },
    );
    if (dialog.open) dialog.close();
    toast("Đã gửi yêu cầu. Xem kết quả tại Lịch sử cập nhật.");
    loadPage(true);
  } catch (e) {
    dialog.open ? dialogError(e) : toast(friendly(e), true);
  } finally {
    button.disabled = false;
  }
}
function go(page) {
  if (dialog.open) dialog.close();
  if (location.hash === `#${page}`) navigate();
  else location.hash = page;
}
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-action]");
  if (!b || b.disabled) return;
  const { action, id } = b.dataset;
  switch (action) {
    case "refresh":
      loadPage();
      break;
    case "add":
      addSource();
      break;
    case "close":
      dialog.close();
      break;
    case "csv-start":
      csvStart();
      break;
    case "csv-preview":
      await csvPreview(b);
      break;
    case "sheets-start":
      await sheetsStart();
      break;
    case "other":
      otherConnection();
      break;
    case "go-guide":
      go("guide");
      break;
    case "go-sources":
      go("sources");
      break;
    case "source":
      await showSource(id);
      break;
    case "run":
      await showRun(id);
      break;
    case "sync":
      await syncSource(id, b);
      break;
    case "source-activity":
      state.runSource = id;
      state.runStatus = "";
      state.runOffset = 0;
      go("activity");
      break;
    case "clear-filters":
      state.sourceQuery = "";
      state.sourceKind = "";
      state.sourceOffset = 0;
      loadPage();
      break;
    case "page":
      state[b.dataset.scope === "source" ? "sourceOffset" : "runOffset"] =
        Number(b.dataset.offset);
      loadPage();
      break;
    case "toggle":
      b.disabled = true;
      try {
        await api(`/api/v1/sources/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body: JSON.stringify({ enabled: b.dataset.enabled === "true" }),
        });
        toast(
          b.dataset.enabled === "true"
            ? "Đã bật lại nguồn."
            : "Đã tạm dừng nguồn.",
        );
        await showSource(id);
        loadPage(true);
      } catch (error) {
        dialogError(error);
        b.disabled = false;
      }
      break;
    case "backfill-confirm":
      openDialog(
        "Đọc lại toàn bộ dữ liệu?",
        "Chỉ dùng khi cần lấy lại dữ liệu từ đầu.",
        `<div class="notice warning">${icon("info")}Thao tác có thể mất nhiều thời gian với nguồn lớn. Lịch sử đã lưu vẫn được giữ; các phiên bản trùng sẽ được bỏ qua.</div>`,
        `<button class="button secondary" data-action="source" data-id="${esc(id)}">Quay lại</button><button class="button primary" data-action="backfill" data-id="${esc(id)}">Bắt đầu đọc lại</button>`,
      );
      break;
    case "backfill":
      await syncSource(id, b, true);
      break;
    case "retry-workspace":
      startWorkspace();
      break;
  }
});
async function startWorkspace() {
  try {
    state.session = await api("/api/v1/session");
    showApp();
  } catch {
    $("#boot-loading").innerHTML =
      `<div class="empty-state"><h2>Chưa mở được không gian làm việc</h2><p>Kiểm tra kết nối với hệ thống rồi thử lại.</p><button class="button primary" data-action="retry-workspace">Thử lại</button></div>`;
    $("#boot-loading").hidden = false;
  }
}
setInterval(() => {
  if (
    state.session &&
    ["overview", "business"].includes(state.page) &&
    !dialog.open &&
    !document.hidden &&
    !(
      main.contains(document.activeElement) &&
      document.activeElement.matches("input,select,button,a,summary")
    )
  )
    loadPage(true);
}, 20000);
startWorkspace();
