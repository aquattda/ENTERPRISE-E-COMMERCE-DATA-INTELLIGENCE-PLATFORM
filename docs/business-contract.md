> Cập nhật 16/10/2026: bản chạy hiện tại là [demo Vercel](https://cdip-business-demo.vercel.app).
> Xem [vận hành hiện tại](operations.md). Các phần database, nguồn dữ liệu và lưu dùng chung bên dưới mô tả backend được giữ lại để phát triển sau, không chạy trên Vercel.

# Hợp đồng dữ liệu báo cáo lãi/lỗ

Đây là báo cáo lợi nhuận đóng góp của các dòng đơn đã ghi nhận, chưa phải lợi nhuận ròng công ty.
Mã chuẩn: `src/commerce_data/analytics/contracts.py`; công thức: `analytics/profit.py`.
Demo dùng cùng bộ tính với dữ liệu công ty, nhưng sinh độc lập và không ghi vào database.

## Đơn vị dữ liệu

Một dòng = một SKU trong một đơn, định danh bằng kênh, cửa hàng, đơn, dòng và tiền tệ.
Chỉ entity `profit_line_v1` đi vào báo cáo. Connector thông thường phải cấu hình entity và
`field_mapping` theo chiều trường chuẩn → trường dữ liệu gốc; dữ liệu phải có đủ ngữ nghĩa
của hợp đồng. Mapping tên cột không thay thế adapter xác thực, phân bổ hoặc tính quyết toán.
Không tự coi nguồn demo ingestion 10.000 đơn là dữ liệu kinh doanh chuẩn.

- `business_date`: ngày ghi nhận nghiệp vụ đã chuẩn hóa theo quy tắc công ty; lọc hai đầu bao gồm.
- `gross_sales`: giá trị hàng trước giảm giá người bán; không nhân số lượng thêm lần nữa.
- `seller_discount`: giảm giá do người bán chịu, không cộng voucher tài trợ bởi sàn vào đây.
- `refund_amount`: tiền hàng thực hoàn theo cùng cơ sở doanh thu, không trừ trùng giảm giá.
- `shipping_income`, `other_income`: khoản thu thuộc người bán, tách khỏi tiền hàng.
- `quantity_dispatched`, `quantity_restocked`: số lượng xuất và thực nhập lại kho. Hàng hoàn hỏng
  không được nhập lại chỉ để đảo giá vốn.
- Chi phí: platform_fee, payment_fee, shipping_cost, return_shipping_cost, voucher_fee,
  ad_cost, affiliate_cost, packaging_cost, tax_cost, other_cost. Phí dương là chi; âm là hoàn phí.
- Giá vốn đơn vị: `unit_cost` trực tiếp; nếu thiếu, tra bảng theo SKU/tiền tệ/cửa hàng/ngày.
  Ưu tiên cửa hàng cụ thể; `*` là mặc định. Chọn ngày hiệu lực gần nhất không sau ngày bán.
  Bảng giá vốn lưu các bản bổ sung, bản mới nhất của cùng khóa thay thế khi đọc báo cáo.
- `expected_payout` và `actual_payout`: khoản quyết toán tương ứng dòng, đã được adapter phân
  tách đúng cơ sở. Không chép tổng quyết toán đơn vào từng SKU, không trừ phí hai lần.

## Công thức và điều kiện xác nhận

Doanh thu thuần = gross_sales − seller_discount − refund_amount + shipping_income + other_income.
Giá vốn = (quantity_dispatched − quantity_restocked) × unit_cost.
Lãi đóng góp = doanh thu thuần − giá vốn − tổng 10 khoản chi phí.
Chênh lệch đối soát = actual_payout − expected_payout, hiện yêu cầu khớp chính xác (không dung sai).
Tính bằng Decimal; tiền tệ được tách riêng, không quy đổi ngầm.

Khoản chưa biết là null, không phải 0. Chỉ gán 0 khi nguồn xác nhận không có khoản đó.
`profit_provisional` trừ các khoản đã biết, phải đọc cùng danh sách thiếu. `profit_actual` chỉ có khi
đủ dữ liệu, đơn đã đóng, hoàn tiền/quyết toán đã chốt, allocation=direct và quyết toán khớp.
Chi phí phân bổ (allocated) hoặc chưa xác định (unresolved) không được xác nhận thực tế theo SKU.
Đơn hủy vẫn có thể phát sinh phí. Hoàn tiền không tự làm giảm giá vốn.

Tổng nhóm chỉ xác nhận khi mọi dòng trong nhóm đã đủ dữ liệu. `verified_profit` chỉ là tổng phần
đã đủ dữ liệu kèm số dòng; không thay thế tổng thực tế khi còn dòng thiếu. Doanh thu chiến dịch là
số gán nguồn, không chứng minh doanh thu tăng thêm do quảng cáo. ROAS = doanh thu gán nguồn / ad_cost;
không tính khi chi quảng cáo bằng 0 hoặc thiếu.

## Đọc dữ liệu và giới hạn hiện tại

- Lấy phiên bản mới nhất theo khóa nguồn/entity/shop/key, sau đó mới loại tombstone. Giữ `record_id`
  để truy về raw. REST ưu tiên thời điểm nguồn; CSV/Sheets snapshot dùng thời điểm nhận.
- Lần đồng bộ gần nhất chưa thành công khiến dòng chưa xác nhận. Dòng sai hợp đồng/trùng định danh
  giữa nhiều nguồn bị loại khỏi tính toán và khóa xác nhận toàn bộ tổng trong phạm vi báo cáo.
- Tối đa 50.000 bản ghi chuẩn hiện hành trong phép chiếu; vượt mức báo lỗi, không cắt ngầm.
- Dữ liệu không có campaign/promotion ID không nằm trong nhóm chiến dịch/khuyến mãi.
- Chưa nhập sổ chi quảng cáo độc lập không phát sinh đơn, chi phí chung, kiểm kê và chuyển khoản ngân hàng.
- Chưa có adapter API Shopee/TikTok Shop chuyên biệt, chưa kiểm chứng quyền/API thật.
- CSV có đủ khoản thu/chi, phần lãi, trạng thái, nguồn dữ liệu và chặn công thức trong ô văn bản.
  Power Query chỉ là mẫu dành cho API demo công khai; API công ty vẫn dùng phiên hoặc bearer.

## Triển khai

Migration `0002_cost_book` tạo `ops.sku_cost_book`, runtime chỉ được SELECT/INSERT bảng này.
Báo cáo dùng chung nội bộ, không quản lý tài khoản/phân quyền người dùng. Cookie/CSRF và các role
cơ sở dữ liệu là kiểm soát kỹ thuật. Compose hiện chỉ công bố cổng trên máy cục bộ.