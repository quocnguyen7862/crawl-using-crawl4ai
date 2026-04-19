## Why

`topcv.vn` là nguồn dữ liệu tuyển dụng lớn tại Việt Nam, nhưng hiện workspace chưa có quy trình chuẩn để thu thập danh sách việc làm và chi tiết tin tuyển dụng bằng Crawl4AI. Cần chuẩn hóa thay đổi này ngay từ đầu để việc triển khai crawler, cấu trúc dữ liệu đầu ra, và giới hạn crawl được xác định rõ trước khi bắt tay vào code.

## What Changes

- Bổ sung một workflow crawl bằng Crawl4AI cho `topcv.vn` để thu thập danh sách việc làm và dữ liệu chi tiết từ trang tuyển dụng.
- Xác định rõ đầu vào crawl gồm URL khởi tạo, phạm vi crawl, và các trường dữ liệu tối thiểu phải trích xuất từ mỗi tin tuyển dụng.
- Quy định đầu ra có cấu trúc để dữ liệu crawl có thể được lưu, kiểm tra, và tái sử dụng cho các bước phân tích hoặc nhập kho dữ liệu sau này.
- Thiết lập các ràng buộc vận hành cơ bản như phân trang, chống trùng lặp URL, và xử lý lỗi khi một trang chi tiết không đọc được.

## Capabilities

### New Capabilities
- `topcv-job-crawling`: Crawl danh sách việc làm và trang chi tiết tuyển dụng từ `topcv.vn`, sau đó xuất dữ liệu có cấu trúc với các trường bắt buộc.

### Modified Capabilities

None.

## Impact

- Ảnh hưởng đến mã crawler mới dùng Crawl4AI, cấu hình URL seed, logic trích xuất dữ liệu, và định dạng file đầu ra.
- Phụ thuộc vào khả năng truy cập HTML hoặc nội dung render từ `topcv.vn`, cùng với cơ chế rate limiting và retry của Crawl4AI.
- Tạo nền tảng để sau này mở rộng sang lọc theo ngành nghề, địa điểm, hoặc lập lịch crawl định kỳ.
