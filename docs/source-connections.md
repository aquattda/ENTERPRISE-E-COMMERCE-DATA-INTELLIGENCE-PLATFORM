# Kết nối nguồn dữ liệu

## Luồng chính

1. Chọn Shopee, TikTok Shop, API website hoặc Google Sheets.
2. Nhập các trường thông tin hiện ra. Không nhập khóa API vào chat; nhập trực tiếp trong biểu mẫu HTTPS.
3. Bấm Kiểm tra & lấy dữ liệu. Lỗi được hiển thị tại biểu mẫu; HTTP200 kèm lỗi nghiệp vụ từ sàn vẫn là lỗi.
4. Xem bảng hoặc JSON. Tải CSV (UTF-8 BOM) hay JSON của phản hồi đang xem.
5. Lưu mẫu nếu cần dùng lại. Mẫu lưu cục bộ: tên, loại nguồn, host/path, tên trường header, app ID/shop ID,
   phạm vi đọc; không lưu token, app secret hoặc query/fragment URL. Khi mở mẫu cần nhập lại phần đã bỏ.

## Phạm vi nguồn

- Website: HTTPS cổng443, GET, JSON/CSV UTF-8. Bearer hoặc header có trong danh sách được hỗ trợ.
  Không tự đăng nhập website, crawl HTML hoặc khám phá endpoint. Redirect bị chặn để không chuyển token.
- Sheets công khai: chuyển link docs.google.com sang CSV theo gid; hỗ trợ link pub đã công bố.
- Sheets riêng tư: Sheets API v4 values.get; Access token phải có scope/quyền đọc phù hợp.
  Không tự gia hạn token; không yêu cầu công khai bảng nội bộ. Dòng đầu làm tiêu đề, cột trùng được đánh số.
- Shopee: production partner.shopeemobile.com; GET /api/v2/shop/get_shop_info và
  /api/v2/order/get_order_list. Ký HMAC-SHA256 theo partner_id/path/timestamp/access_token/shop_id.
- TikTok Shop: production open-api.tiktokglobalshop.com; GET /authorization/202309/shops và
  POST /order/202309/orders/search (chỉ đọc danh sách). Ký path + query theo thứ tự + đúng JSON body;
  access token nằm ở header x-tts-access-token. Không có thao tác sửa đơn hay sản phẩm.
- Sàn đọc20 đơn mỗi trang. Chuyển trang dùng cursor của nguồn, giữ thời điểm kết thúc của trang đầu.
  Nút trang tiếp theo thay phản hồi hiện tại; tải tệp chỉ tải trang đang xem, không tự gộp mọi trang.

Các endpoint không được tuyên bố là phiên bản mới nhất; cần đối chiếu quyền/phiên bản của ứng dụng
thực tế trước khi vận hành. Chưa có quyền sàn thật để chạy nghiệm thu trực tiếp.

## Giới hạn và bảo vệ dữ liệu

- Mỗi phản hồi tối đa1MB và5.000 dòng; preview100 dòng/60 cột, tệp tải có đủ dòng/cột của phản hồi.
- Server không lưu config, token hoặc dữ liệu. Mẫu browser-local không phải nơi lưu bí mật/dữ liệu dùng chung.
- Không log request body/URL đích/token. Lỗi validation không phản chiếu đầu vào. Không có tracking bên thứ ba.
- HTTPS xác minh chứng chỉ; kiểm tra mọi địa chỉ DNS là global rồi ghim IP khi kết nối, TLS theo hostname gốc.
  Không cho localhost/private IP, userinfo, cổng khác443, fragment hoặc chuyển hướng tùy ý.
  Redirect công khai của Sheets chỉ theo docs.google.com hoặc *.googleusercontent.com, kiểm tra lại từng IP.
- Chỉ có GET tùy chọn cho website và một POST cố định đọc đơn TikTok. Không có proxy ghi tùy ý.
- POST vào API yêu cầu header X-CDIP-Request và Origin cùng host nếu trình duyệt gửi Origin.
- CSV chặn ô văn bản công thức. Giá trị access/refresh token, app secret, partner key và token/secret đã nhập
  được che trong kết quả. JSON “gốc” nghĩa là phản hồi nguồn sau che khóa xác thực, không byte-for-byte.
- Đây là công cụ lấy dữ liệu theo yêu cầu. Chưa có kho lưu chung, lịch chạy nền, OAuth/refresh một chạm,
  quản lý người dùng hoặc cam kết sẵn sàng cho dữ liệu doanh nghiệp quy mô lớn.

## Kiểm chứng

96 unit tests pass; trong đó25 trường hợp bảo vệ/kết nối Vercel. Ruff và mypy37 modules pass.
Trình duyệt local/cloud kiểm tra nguồn, mẫu không chứa secret, mẫu API, hiển thị an toàn, CSV và mobile;
những phản hồi lỗi/thành công tùy chỉnh trong UI test được mock. Ngoài ra đã gọi outbound thật từ Vercel
đến JSONPlaceholder (3 dòng) và bảng tính mẫu công khai của Google. Chưa chạy sàn hoặc private Sheets thật.

## Tài liệu API đối chiếu

- [Shopee: hướng dẫn xác thực v2 trên CDN của sàn](https://cdngarenanow-a.akamaihd.net/shopee/seller/seller_cms/c575929f948611337e1249564c2b8ff6/%5BTW%5D%5BOpen%20API%5DAPI%20v1_v2%E6%8E%88%E6%AC%8A%E6%96%B9%E6%B3%95%20%282020_09%29_newnew.pdf), phần ký request; tài liệu cũ, không dùng làm căn cứ biểu phí/expiry mới nhất.
- [TikTok Shop common parameters](https://partner.tiktokshop.com/docv2/page/common-parameters).
- [TikTok Shop ví dụ ký request](https://partner.tiktokshop.com/docv2/page/wfi3nz36).
- [TikTok Get Order List 202309](https://partner.tiktokshop.com/docv2/page/get-order-list-202309).
- [Google Sheets values.get](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get).
- [Google quickstart và bảng tính mẫu](https://developers.google.com/workspace/sheets/api/quickstart/python).