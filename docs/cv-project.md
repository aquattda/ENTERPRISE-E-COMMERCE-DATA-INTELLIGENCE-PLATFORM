# Nội dung đưa vào CV

**CDIP – Website kết nối và lấy dữ liệu đa nguồn** | Dự án cá nhân | 10/2026

**Công nghệ:** Python, FastAPI, JavaScript, HTML/CSS, REST API, Vercel, Pytest, Playwright.

- Xây dựng giao diện kết nối API website và Google Sheets, hỗ trợ xác thực Bearer token/API key, xem dữ liệu dạng bảng/JSON và xuất CSV/JSON.
- Phát triển connector đọc thông tin cửa hàng, đơn hàng Shopee/TikTok Shop; xử lý chữ ký HMAC-SHA256, phân trang và lỗi xác thực.
- Bảo vệ thông tin kết nối: không lưu token trong mẫu nguồn; kiểm soát truy cập mạng nội bộ (SSRF), giới hạn phản hồi và xử lý dữ liệu hiển thị/xuất tệp an toàn.
- Triển khai trên Vercel; xây dựng 25 kiểm thử cho lớp kết nối và kiểm thử giao diện bằng Playwright; xác minh lấy dữ liệu từ API công khai và Google Sheets thực tế.

**Demo:** https://cdip-business-demo.vercel.app

**GitHub:** https://github.com/aquattda/ENTERPRISE-E-COMMERCE-DATA-INTELLIGENCE-PLATFORM

## Lưu ý khi trao đổi phỏng vấn

Shopee/TikTok Shop đã được kiểm thử logic ký request và phản hồi giả lập, chưa nghiệm thu với API/token doanh nghiệp thật.
Google Sheets riêng tư đã kiểm thử bằng fixture; kiểm thử trực tiếp hiện dùng bảng công khai.
Hiện lấy dữ liệu theo yêu cầu; chưa có OAuth một chạm, tự gia hạn token, đồng bộ theo lịch hoặc kho dữ liệu dùng chung.
Không trình bày dự án như hệ thống đã vận hành production cho doanh nghiệp hoặc tự nhận có kết quả tiết kiệm chi phí/thời gian chưa đo.