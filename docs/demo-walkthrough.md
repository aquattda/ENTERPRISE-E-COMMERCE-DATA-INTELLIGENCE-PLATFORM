# Kịch bản trình diễn trong 5 phút

Mở https://cdip-business-demo.vercel.app trên trình duyệt. Không cần API công ty, không cần đăng nhập.
Chọn **Dữ liệu demo**. Dữ liệu giả lập gồm 18 đơn trên Shopee, TikTok Shop, Online, Offline,
trong khoảng 01–14/10/2026; phí minh họa không phải biểu phí thực tế của các sàn.

## Cách giới thiệu

“Tôi đã xây dựng bản mẫu chạy được để minh họa việc gom dữ liệu, tính lãi/lỗ và đối soát.
Hiện đang dùng dữ liệu giả lập. Khi nhận API, dữ liệu và quy tắc của công ty, tôi sẽ nối nguồn
thật và kiểm thử số liệu với các báo cáo đang sử dụng.”

## Thao tác

1. **Tổng quan kinh doanh:** xem doanh thu 3.133.000 đ; lãi 799.000 đ của 14 dòng đã đủ dữ liệu.
   Còn 4 dòng chưa xác nhận. Không cộng phần thiếu thành lợi nhuận thực tế toàn công ty.
2. **Lãi/lỗ đơn hàng:** mở “Xem các khoản” của một đơn bị lỗ, giải thích doanh thu, giá vốn,
   voucher, quảng cáo, affiliate, vận chuyển và phí sàn. DEMO-0009 hoàn hàng nhập lại kho;
   DEMO-0010 hàng hoàn hỏng vẫn mất giá vốn. DEMO-0007 còn thiếu giá vốn.
3. **Sản phẩm / SKU:** so sánh BINH-750 có lãi với TUI-VAI bị lỗ. Chọn “Thử giá bán”, thay
   chi phí quảng cáo/giá vốn; xem giá hòa vốn và giá đạt biên lãi mong muốn. Đây là mô phỏng
   theo giả định nhập vào, không tự sửa giá trên sàn.
4. **Đối soát tiền sàn:** DEMO-0008 lệch 3.500 đ giữa tiền dự kiến và thực trả. Đơn này chưa
   được xác nhận lãi thực tế. DEMO-0012 có chi phí quảng cáo phân bổ, cũng chưa xác nhận.
5. **Quảng cáo & khuyến mãi:** xem doanh thu gán nguồn, chi phí quảng cáo, ROAS và lãi/lỗ.
   Xuất CSV mở bằng Excel/Google Sheets. Chuyển **Dữ liệu công ty** để cho thấy hai nguồn tách biệt.

## Đã chạy được

Bản Vercel chỉ có dữ liệu giả lập; bảng giá vốn thử nhập lưu trong trình duyệt, không dùng chung.
Mã đồng bộ/backend nền dưới đây được giữ trong repository để phát triển tiếp, không chạy trên host.

- Sáu mục nghiệp vụ bằng tiếng Việt, lọc ngày/kênh, xem chi tiết và xuất CSV.
- Công thức Decimal dùng chung cho demo và dữ liệu chuẩn hóa; khoản chưa biết không coi là 0.
- Bảng giá vốn theo SKU/cửa hàng/ngày hiệu lực; lưu lịch sử chỉnh sửa.
- Thu thập tự động qua connector REST, CSV, Google Sheets, PostgreSQL với cấu hình phù hợp;
  lịch chạy, lưu dữ liệu gốc và chống trùng đã có. Kết nối Google/nguồn thật chưa được kiểm chứng.
- Các tình huống lãi, lỗ, thiếu giá vốn, hoàn hàng, lệch quyết toán và chi phí phân bổ.

## Khi nhận thông tin công ty

- Nhận quyền API và các báo cáo mẫu; xác định cửa hàng, SKU, ngày ghi nhận và quy tắc giá vốn.
- Viết adapter Shopee/TikTok Shop tương ứng với quyền được cấp, xử lý xác thực và cấu trúc báo cáo.
- Chuẩn hóa vào `profit_line_v1`, đối chiếu một kỳ bán hàng trước khi vận hành thật.
- Bổ sung nguồn chi tiêu chưa gắn đơn, chi phí chung và đối soát chuyển khoản nếu cần báo cáo
  lợi nhuận ròng toàn công ty. Bản demo chưa làm phần này.

## Excel / Power BI

Nút xuất hiện tạo CSV UTF-8, không phải file XLSX. Có thể nhập CSV vào Excel hoặc Google Sheets.
Mẫu [demo-power-query.pq](https://cdip-business-demo.vercel.app/assets/demo-power-query.pq) đọc API dữ liệu giả lập tại
`https://cdip-business-demo.vercel.app/api/v1/demo/business/report`. Trong Excel Power Query hoặc Power BI Desktop,
tạo Blank Query và dán mã vào Advanced Editor; chọn Anonymous cho API demo. Dùng bản truy vấn tải từ trang hướng dẫn trên Vercel; bản đó trỏ tới URL host công khai. Mẫu này chưa được thực thi trong Excel/Power BI;
chưa có file PBIX, Google Sheets tự đồng bộ hay lịch refresh trên cloud.

Giao diện có hướng dẫn tại https://cdip-business-demo.vercel.app/#guide. Xem hợp đồng dữ liệu tại
[business-contract.md](business-contract.md).