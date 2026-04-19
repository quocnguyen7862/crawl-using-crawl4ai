## 1. Extend crawl configuration

- [x] 1.1 Thêm các trường cấu hình cho pacing an toàn như `base_delay`, `delay_jitter`, `backoff_multiplier`, và `block_threshold`.
- [x] 1.2 Thêm cấu hình proxy và browser type vào model config hiện có.
- [x] 1.3 Mở rộng CLI để người dùng truyền các cấu hình anti-block từ command line.

## 2. Implement safer request behavior

- [x] 2.1 Cài delay ngẫu nhiên giữa các request thay cho khoảng nghỉ cố định hoàn toàn.
- [x] 2.2 Cài logic backoff tăng dần khi gặp tín hiệu nghi ngờ bị block hoặc rate-limit.
- [x] 2.3 Cài cơ chế dừng sớm hoặc short-circuit crawl khi số tín hiệu block vượt ngưỡng cấu hình.

## 3. Detect and report blocking signals

- [x] 3.1 Phân loại riêng các tín hiệu `403`, `429`, timeout lặp lại, hoặc response bất thường thành `block-suspected`.
- [x] 3.2 Ghi log rõ ràng để phân biệt lỗi request thông thường với lỗi nghi ngờ bị block.
- [x] 3.3 Bổ sung thống kê block-related vào crawl summary hoặc output cuối run.

## 4. Support alternate routing and browser strategy

- [x] 4.1 Truyền cấu hình proxy vào BrowserConfig của Crawl4AI khi người dùng cung cấp proxy.
- [x] 4.2 Cho phép chọn browser type như `chromium` hoặc `firefox` từ cấu hình/CLI.
- [x] 4.3 Xác nhận crawler vẫn hoạt động khi không cấu hình proxy hoặc browser override.

## 5. Validate anti-block behavior

- [x] 5.1 Viết hoặc cập nhật test cho jitter, backoff, block detection, và early-stop behavior.
- [x] 5.2 Chạy thử crawler với cấu hình bảo thủ để xác nhận request pacing mới hoạt động đúng.
- [x] 5.3 Cập nhật README với hướng dẫn crawl an toàn hơn, ví dụ giảm concurrency, tăng delay, và dùng proxy/browser type khi cần.
