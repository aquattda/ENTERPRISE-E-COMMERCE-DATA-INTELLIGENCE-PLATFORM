# CDIP — Kết nối và lấy dữ liệu

**Mở trang web: https://cdip-business-demo.vercel.app**

Trang web tập trung vào một việc: **chọn nguồn → nhập thông tin kết nối → lấy dữ liệu → xem và tải tệp**.
Không có dashboard doanh thu, lãi/lỗ hoặc quản lý tài khoản. Không cần Docker hay phần mềm chạy nền.

## Nguồn hỗ trợ

| Nguồn | Cách dùng |
| --- | --- |
| API website | URL HTTPS trả JSON/CSV; không xác thực, Bearer token hoặc API key trong header |
| Google Sheets | Liên kết bảng công khai/CSV đã công bố; bảng riêng tư dùng Google Access token có quyền đọc |
| Shopee | Partner ID, Partner key, Shop ID, Access token; lấy thông tin shop hoặc danh sách đơn |
| TikTok Shop | App key, App secret, Access token; lấy danh sách shop rồi dùng Shop cipher để lấy đơn |

Có dạng bảng, JSON gốc, tải JSON/CSV và lưu mẫu nguồn trên trình duyệt. Mẫu không lưu token, khóa bí mật
hoặc tham số URL. Phản hồi chỉ nằm trong bộ nhớ của lần gọi và tab đang mở, không ghi vào database.

Mỗi lần lấy một phản hồi: tối đa 1 MB / 5.000 dòng; bảng xem trước 100 dòng. Sàn lấy20 đơn/trang,
có nút Trang tiếp theo và giữ nguyên khoảng thời gian khi chuyển trang. Website dùng tham số
phân trang theo tài liệu nguồn. Khóa/token nhập lại khi mở mẫu. Các trường dữ liệu nhạy cảm chứa
access_token/refresh_token/app_secret/partner_key được che trong phản hồi hiển thị/xuất.

Đã kiểm tra API website công khai và bảng tính mẫu công khai của Google từ Vercel.
Shopee/TikTok và Google Sheets riêng tư chưa được kiểm chứng bằng thông tin API thật của công ty.
Chưa có OAuth một chạm, tự gia hạn token, dịch vụ đồng bộ nền hoặc lưu dữ liệu dùng chung.
Website phải cung cấp endpoint API; trang này không tự phát hiện hoặc tạo API từ trang bán hàng.

## Dùng thử

Mở trang và chọn **Thử API mẫu** để xem luồng mà chưa cần thông tin công ty.
Để kiểm tra một API thật, chọn API website và nhập:
`https://jsonplaceholder.typicode.com/todos?_limit=3`.

## Phát triển và cập nhật host

```powershell
.venv/Scripts/python.exe -m uvicorn apps.vercel.main:app --host 127.0.0.1 --port 8010
.venv/Scripts/python.exe -m pytest tests/unit -q
.venv/Scripts/python.exe scripts/prepare_vercel.py
Set-Location deploy/vercel
npx --yes vercel@64.3.1 --prod --yes
```

Entry point: `apps/vercel/main.py`; logic lấy nguồn: `apps/vercel/sources.py`; UI: `apps/vercel/static/`.
Script đóng gói chỉ đưa các file này lên host, không đưa phần phân tích, database, dữ liệu hoặc `.env`.
Gói mã khoảng65KB. Mã backend/phân tích cũ giữ trong repository nhưng không nằm trong ứng dụng triển khai.
Xem [docs/source-connections.md](docs/source-connections.md) và [docs/operations.md](docs/operations.md).