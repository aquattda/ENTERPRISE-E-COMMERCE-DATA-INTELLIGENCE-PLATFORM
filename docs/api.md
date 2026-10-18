# API của trang kết nối dữ liệu

Base URL: https://cdip-business-demo.vercel.app

| Route | Chức năng |
| --- | --- |
| GET / | Giao diện kết nối nguồn |
| GET /assets/* | JS/CSS giao diện |
| GET /api/v1/health | Kiểm tra dịch vụ |
| GET /api/sources/example | 3 bản ghi mẫu, có cờ example=true |
| POST /api/sources/read | Gửi thông tin nguồn và lấy một phản hồi |

POST yêu cầu Content-Type application/json và X-CDIP-Request:1; nếu có Origin thì phải cùng host.
Body dùng kind=website/sheets/shopee/tiktok. Schema chi tiết tại [openapi.json](openapi.json).
Token và app_secret chỉ tồn tại trong bộ nhớ request; không gửi vào URL API của ứng dụng.

Kết quả có rows, raw, row_count, http_status, elapsed_ms, bytes, next_cursor và window_end.
Một phản hồi tối đa1MB/5.000 dòng. next_cursor/window_end dùng cho trang đơn hàng tiếp theo.
raw là nội dung nguồn sau khi che credential; không phải byte nguyên bản. Phản hồi lỗi không echo input.
Các trường invalid trả422; nguồn lỗi/không hợp lệ trả400; sai Origin/header403; request quá32KB trả413.
Không còn route báo cáo kinh doanh, lưu giá vốn, upload hoặc CRUD nguồn trên Vercel.

Chi tiết hỗ trợ/giới hạn: [source-connections.md](source-connections.md).