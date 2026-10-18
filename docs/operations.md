# Vận hành trang kết nối nguồn

Ứng dụng: https://cdip-business-demo.vercel.app
Vercel project: cdip-business-demo, nhóm luong-tuans-projects-a65355dc.
Phạm vi hiện tại từ17/10/2026: chỉ kết nối/lấy dữ liệu sàn, API website và Google Sheets.
Các route báo cáo/giá vốn/mô phỏng giá đã được bỏ khỏi host.

## Cập nhật

Chạy `python scripts/prepare_vercel.py`, vào `deploy/vercel` rồi chạy
`npx --yes vercel@64.3.1 --prod --yes`. Không tự deploy từ Git. Script đóng gói danh sách file
cho phép và loại bỏ artifact analytics cũ, giữ `.vercel` identity. Không đóng gói secrets/data.

## Vận hành

API chính: POST `/api/sources/read`, GET `/api/sources/example`, GET `/api/v1/health`.
Không có database, lịch nền, tài khoản hoặc server API key. Secret do người dùng nhập mỗi lần,
chỉ giữ trong bộ nhớ request; mẫu nguồn lưu browser-local, bỏ secret và query/fragment URL.
Dữ liệu lấy ra không được lưu server. Chi tiết nguồn, giới hạn và kiểm thử tại
[source-connections.md](source-connections.md). Khóa/token không gửi trong chat.

Kết nối private/sàn yêu cầu quyền nguồn hợp lệ; OAuth tự động, refresh, đồng bộ theo lịch chưa có.
Tài liệu business-contract/demo-walkthrough và lịch sử kiểm thử nghiệp vụ là phạm vi cũ, không phải
hướng dẫn vận hành hiện tại. UI/API phân tích đã không còn được đưa lên bản deploy mới.

## Bản sao dữ liệu trước khi gỡ môi trường cũ

Đường dẫn cục bộ: `.local/pre-uninstall-backup/` (bị loại khỏi Git và gói deploy).

- `cdip.sql`: SQL dump hoàn chỉnh của dữ liệu dự án, khoảng4,2MB.
- `retail-postgres-data.tar.gz`: dữ liệu PostgreSQL của dự án retail cũ, khoảng232MB; sao chép
  khi database đã dừng. Đây là bản sao thư mục dữ liệu, cần PostgreSQL cùng major version để phục hồi.
- `cdip-uploads.tar.gz`: thư mục tệp tải lên cũ (không có tệp người dùng).

Đã đọc kiểm tra toàn bộ gzip, danh mục tar và dấu hoàn tất SQL dump. Chưa thực hiện restore drill
cho các bản sao mới này. Không tự xóa các bản sao; chúng bảo toàn dữ liệu ngoài dự án hiện tại.

## Thay đổi môi trường ngày16/10/2026

Theo yêu cầu người dùng: đã gỡ Docker Desktop qua uninstaller chính thức, xóa phần còn sót trong
AppData/.docker/thư mục cài đặt. Không còn container/image/volume/cache/đĩa ảo Docker và distro Docker WSL.
Không gỡ tính năng WSL của Windows. Đã xóa Compose, Dockerfile, .dockerignore và script init container
khỏi dự án; CI hiện chỉ chạy unit tests, không khởi tạo dịch vụ container.

Dung lượng trống ổC trước thao tác:2,48GiB; sau thao tác:19,76GiB (chênh lệch ròng khoảng17,28GiB).
Con số là tại thời điểm đo và có thể đổi do các ứng dụng khác trên máy.

Tài liệu kiểm thử/kiến trúc cũ ghi kết quả lịch sử của backend trước khi chuyển host; không phải
hướng dẫn khởi chạy hiện tại. README và tài liệu này là nguồn hướng dẫn vận hành hiện hành.
Final measurement after deployment verification: C free18.30GiB versus2.48GiB at start (net15.82GiB).
Disk free space fluctuated during work; all verified Docker directories remain absent.

Update 2026-10-17: At the user's explicit request, the old retail project backup
`.local/pre-uninstall-backup/retail-postgres-data.tar.gz` was deleted.
Previous references to its retention are historical; it no longer exists.
