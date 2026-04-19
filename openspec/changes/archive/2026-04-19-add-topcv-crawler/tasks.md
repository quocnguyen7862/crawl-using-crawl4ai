## 1. Setup crawler foundation

- [x] 1.1 Tạo cấu trúc module/script cho crawler TopCV trong workspace và khai báo điểm vào chạy crawl.
- [x] 1.2 Khai báo cấu hình đầu vào cho seed URL, giới hạn số trang hoặc số job, và đường dẫn output.
- [x] 1.3 Cấu hình Crawl4AI với các tham số request cơ bản như concurrency, delay, timeout, và retry.

## 2. Implement listing discovery

- [x] 2.1 Cài logic đọc trang listing TopCV và thu thập candidate job detail URL hợp lệ.
- [x] 2.2 Thêm bộ lọc domain và URL pattern để chỉ giữ URL thuộc phạm vi tuyển dụng cần crawl.
- [x] 2.3 Cài giới hạn phân trang hoặc số lượng job để crawler dừng đúng phạm vi đã cấu hình.

## 3. Implement detail extraction and normalization

- [x] 3.1 Cài logic truy cập từng job detail URL và trích xuất các trường dữ liệu bắt buộc theo schema.
- [x] 3.2 Chuẩn hóa bản ghi đầu ra để luôn có các key cố định, kể cả khi một số trường không có dữ liệu.
- [x] 3.3 Thêm cơ chế deduplicate theo URL hoặc job identifier trong cùng một phiên crawl.

## 4. Add resilience and output handling

- [x] 4.1 Ghi nhận lỗi cho từng trang listing/detail thất bại và tiếp tục xử lý các URL còn lại.
- [x] 4.2 Xử lý lỗi bootstrap khi không truy cập được bất kỳ seed URL nào và trả về thông báo lỗi rõ ràng.
- [x] 4.3 Ghi kết quả crawl ra định dạng dữ liệu có cấu trúc đã chọn như JSON hoặc JSONL.

## 5. Validate crawler behavior

- [x] 5.1 Chạy thử crawler với tập seed TopCV nhỏ để xác nhận discovery, extraction, và output schema hoạt động đúng.
- [x] 5.2 Kiểm tra tình huống thiếu dữ liệu, URL trùng lặp, và trang detail lỗi để xác nhận hành vi resilience.
- [x] 5.3 Cập nhật hướng dẫn sử dụng ngắn cho cách chạy crawler, cấu hình seed, và vị trí file đầu ra.
