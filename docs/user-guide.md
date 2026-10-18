> Cập nhật 16/10/2026: bản chạy hiện tại là [demo Vercel](https://cdip-business-demo.vercel.app).
> Xem [vận hành hiện tại](operations.md). Các phần database, nguồn dữ liệu và lưu dùng chung bên dưới mô tả backend được giữ lại để phát triển sau, không chạy trên Vercel.

> Giao diện mặc định hiện mở báo cáo kinh doanh. Xem [kịch bản demo](demo-walkthrough.md).
> Các thao tác nguồn dữ liệu bên dưới nằm tại **Kết nối dữ liệu & bảng giá vốn → Quản lý nguồn** hoặc `/#sources`.

# Hướng dẫn sử dụng nội bộ

Mở **http://localhost:8000/** trên máy chạy hệ thống. Ứng dụng vào thẳng không gian
làm việc chung, không cần tạo tài khoản, nhập mật khẩu hay chọn quyền.

## Bốn mục chính

| Mục | Dùng khi nào |
|---|---|
| Tổng quan | Xem nguồn nào có dữ liệu, nguồn cần chú ý và hoạt động gần đây. |
| Nguồn dữ liệu | Thêm nguồn, tìm kiếm, cập nhật ngay, đổi lịch hoặc tạm dừng. |
| Lịch sử cập nhật | Xem mỗi lần cập nhật đang chờ, đang chạy, đã xong hay gặp lỗi. |
| Hướng dẫn sử dụng | Xem các bước thao tác, câu hỏi thường gặp và tải tệp mẫu. |

## Nhập tệp CSV từ Excel

1. Trong Excel chọn **Lưu thành → CSV UTF-8**. Dòng đầu tiên là tên các cột.
2. Chọn **Thêm nguồn dữ liệu → Tải tệp CSV**.
3. Chọn tệp và bấm **Xem trước dữ liệu**.
4. Đặt tên dễ nhớ, chọn cột mã riêng cho từng dòng (ví dụ mã đơn hàng).
5. Bấm **Nhập … dòng**, sau đó **Theo dõi cập nhật**.

Tệp tối đa 10 MB, 100.000 dòng và 50 cột. Cột mã riêng không được trùng hoặc để trống.
Thông báo “Đã tiếp nhận” chỉ xác nhận đã xếp hàng; trạng thái **Đã cập nhật** trong lịch sử
mới xác nhận xử lý hoàn tất. Nếu dữ liệu không đổi, số phiên bản mới có thể bằng 0.

Tệp tải lên là bản sao. Sửa tệp trên máy không tự đổi bản sao đã nhập. Với tệp mới, thêm
nguồn có tên khác; muốn cập nhật liên tục, dùng Google Sheets hoặc kết nối trực tiếp.

## Kết nối Google Sheets

Người phụ trách kỹ thuật thiết lập thông tin kết nối Google một lần cho API và worker.
Ứng dụng chỉ đưa ra các kết nối đã sẵn sàng, không yêu cầu người dùng nhập khóa bí mật.
Sau đó chọn **Google Sheets**, nhập liên kết, vùng dữ liệu (ví dụ `Sheet1!A:Z`) và tên cột
mã riêng. Trang tính phải được chia sẻ quyền xem cho tài khoản kết nối.
Nếu chưa có kết nối, giao diện hướng dẫn tải trang tính thành CSV để sử dụng ngay.

## Theo dõi và xử lý

- **Đang chờ / Đang cập nhật:** hệ thống vẫn xử lý khi bạn đóng cửa sổ.
- **Cần kiểm tra:** mở kết quả, kiểm tra nguồn rồi cập nhật lại. Mã hỗ trợ nằm trong
  phần Thông tin hỗ trợ để gửi cho người phụ trách kỹ thuật nếu cần.
- **Cập nhật chậm:** lâu chưa có lần thành công; xem lịch sử trước khi sử dụng dữ liệu.
- **Tạm dừng:** giữ dữ liệu và lịch sử, ngăn các lần chạy mới; lần đang chạy có thể tiếp tục.

Thời gian hiển thị theo giờ Việt Nam. “Phiên bản đã lưu” bao gồm lịch sử thay đổi,
không phải số đơn hàng hay doanh thu. Các nguồn giả lập được đánh dấu **Dữ liệu mẫu**.

Mọi người dùng chung nguồn và lịch sử, nên thay đổi lịch/tạm dừng sẽ áp dụng cho cả đội.
Ứng dụng hiện chạy trên máy cục bộ; cấu hình truy cập trong mạng nội bộ là công việc triển khai riêng.