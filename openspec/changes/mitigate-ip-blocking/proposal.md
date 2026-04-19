## Why

Crawler hiện có thể bị `topcv.vn` chặn IP khi gửi request quá dày hoặc có hành vi giống bot trong một khoảng thời gian ngắn. Cần chuẩn hóa thay đổi này ngay để crawler vận hành an toàn hơn, giảm lỗi rate-limit, và cho phép cấu hình chiến lược crawl phù hợp với từng mức độ nhạy cảm của nguồn dữ liệu.

## What Changes

- Bổ sung cơ chế điều tiết request an toàn hơn gồm delay ngẫu nhiên, concurrency thấp, và backoff khi gặp dấu hiệu bị chặn hoặc quá tải.
- Bổ sung khả năng cấu hình proxy và chọn browser type phù hợp để giảm phụ thuộc vào một fingerprint hoặc một IP cố định.
- Chuẩn hóa phát hiện các tín hiệu block như `403`, `429`, timeout bất thường, hoặc nội dung trang cho thấy bị challenge/rate-limit.
- Quy định rõ hành vi của crawler khi gặp chặn IP: giảm tốc, retry có kiểm soát, ghi log rõ nguyên nhân, và có thể dừng sớm để tránh làm tình trạng xấu hơn.

## Capabilities

### New Capabilities
- `anti-block-crawl-controls`: Điều khiển tốc độ crawl, jitter, backoff, proxy, và browser strategy để giảm nguy cơ bị chặn IP khi crawl lặp lại.

### Modified Capabilities

None.

## Impact

- Ảnh hưởng đến cấu hình crawler, CLI options, logic request scheduling, và cách xử lý lỗi mạng hoặc phản hồi rate-limit.
- Có thể làm thay đổi tốc độ crawl mặc định theo hướng chậm và thận trọng hơn.
- Tạo nền tảng để sau này hỗ trợ rotation proxy, adaptive throttling, hoặc thay đổi browser fingerprint theo site.
