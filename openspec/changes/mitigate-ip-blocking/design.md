## Context

Crawler TopCV đã hoạt động được ở mức chức năng, nhưng khi tăng tần suất request hoặc crawl liên tục, nguồn đích có thể phản hồi theo kiểu rate-limit, challenge, hoặc chặn IP. Vấn đề này không chỉ nằm ở số lượng request mà còn liên quan đến fingerprint trình duyệt, nhịp request đều đặn quá mức, retry lặp lại khi lỗi, và việc dồn nhiều request liên tiếp trên cùng một IP.

Thiết kế cần hướng tới giảm xác suất bị block thay vì cố gắng "vượt chặn". Vì đây là crawler ứng dụng thực tế, thay đổi cần ưu tiên tính an toàn vận hành, cấu hình được, và minh bạch khi gặp block để người vận hành có thể giảm tải hoặc thay đổi proxy/browser strategy.

## Goals / Non-Goals

**Goals:**
- Bổ sung cơ chế throttle an toàn hơn bằng delay ngẫu nhiên, concurrency thấp, và backoff tăng dần khi gặp tín hiệu bị chặn.
- Cho phép cấu hình proxy và browser type để giảm phụ thuộc vào một đường request hoặc fingerprint cố định.
- Chuẩn hóa việc phát hiện dấu hiệu bị block qua status code, timeout, hoặc nội dung phản hồi bất thường.
- Ghi log rõ ràng để phân biệt lỗi trang bình thường với lỗi nghi ngờ block/rate-limit.

**Non-Goals:**
- Không bảo đảm tránh block tuyệt đối trên mọi website hoặc mọi quy mô crawl.
- Không xây dựng hệ thống proxy rotation phân tán hoặc pool proxy phức tạp ở phiên bản đầu.
- Không thêm cơ chế né captcha, bypass challenge, hoặc hành vi vượt giới hạn bảo vệ của website.

## Decisions

### 1. Thêm `safe crawl controls` như một lớp cấu hình rõ ràng

Crawler sẽ có nhóm cấu hình chuyên biệt cho điều tiết request gồm `base_delay`, `delay_jitter`, `max_concurrent`, `retry_count`, `backoff_multiplier`, và giới hạn dừng sớm khi số tín hiệu block vượt ngưỡng. Điều này tốt hơn việc rải logic sleep/retry rời rạc trong code vì người dùng có thể điều chỉnh chiến lược mà không sửa logic lõi.

Phương án thay thế là chỉ giảm delay mặc định. Tôi không chọn vì vấn đề block không chỉ do delay cố định mà còn do nhịp request dễ đoán và retry quá sát nhau.

### 2. Tách `block detection` khỏi `network failure`

Thiết kế sẽ phân loại riêng các lỗi như `403`, `429`, nội dung phản hồi nghi ngờ challenge, hoặc timeout lặp lại sau nhiều request thành tín hiệu `block-suspected`. Các lỗi còn lại vẫn được giữ như lỗi request thông thường. Việc tách lớp này giúp crawler biết khi nào nên giảm tốc mạnh hoặc dừng sớm.

Phương án thay thế là gom mọi lỗi vào một nhóm `request failed`. Tôi không chọn vì khi đó crawler không thể phản ứng khác nhau giữa lỗi ngẫu nhiên và lỗi nghi ngờ bị chặn.

### 3. Hỗ trợ proxy và browser type như tùy chọn đầu vào chuẩn

Thay vì hardcode browser Chromium hoặc proxy trong code, crawler sẽ nhận cấu hình proxy và browser type qua CLI/config. Điều này giúp người vận hành thử chiến lược khác nhau theo site mà không cần sửa code mỗi lần.

Phương án thay thế là chỉ hỗ trợ một browser mặc định và một proxy tĩnh. Tôi không chọn vì nhu cầu thay đổi fingerprint và đường request là một phần của bài toán vận hành.

### 4. Dừng sớm khi nghi ngờ block thay vì tiếp tục đẩy request

Nếu số lượng tín hiệu block vượt ngưỡng cấu hình, crawler sẽ dừng sớm hoặc bỏ qua batch còn lại thay vì tiếp tục retry hàng loạt. Cách này giảm nguy cơ bị chặn lâu hơn hoặc làm xấu fingerprint/uy tín của IP.

Phương án thay thế là vẫn crawl tiếp với retry nhẹ. Tôi không chọn vì khi đã xuất hiện chuỗi block liên tiếp, tiếp tục crawl thường không mang lại thêm dữ liệu đáng kể mà chỉ làm tăng rủi ro.

## Risks / Trade-offs

- [Crawl chậm hơn đáng kể] -> Giảm thiểu bằng cấu hình an toàn có thể điều chỉnh theo quy mô crawl.
- [Nhầm lẫn giữa lỗi site và lỗi block] -> Giảm thiểu bằng phân loại tín hiệu rõ hơn và log nguyên nhân theo từng request.
- [Proxy kém chất lượng gây nhiều lỗi hơn] -> Giảm thiểu bằng coi proxy là tùy chọn cấu hình, không là mặc định bắt buộc.
- [Firefox/proxy khác hành vi so với Chromium] -> Giảm thiểu bằng đưa browser type thành cấu hình rõ ràng và kiểm thử trên tập seed nhỏ trước khi crawl lớn.

## Migration Plan

1. Mở rộng config và CLI để nhận các tham số throttle, jitter, proxy, browser type, và ngưỡng dừng sớm.
2. Bổ sung lớp phát hiện tín hiệu block và phản ứng backoff/dừng sớm trong crawler loop.
3. Cập nhật logging và output summary để hiển thị số lần nghi ngờ bị block.
4. Kiểm thử trên seed nhỏ với các cấu hình chậm/an toàn trước khi áp dụng cho các phiên crawl dài hơn.

Không có migration dữ liệu cũ. Nếu thay đổi gây crawl quá chậm hoặc không như mong muốn, có thể rollback bằng cách quay lại cấu hình cũ hoặc tắt lớp điều tiết mới.

## Open Questions

- Có nên cho phép cấu hình danh sách nhiều proxy ngay ở phiên bản đầu hay chỉ một proxy endpoint?
- Ngưỡng nào là hợp lý để dừng sớm khi gặp nhiều tín hiệu `block-suspected` liên tiếp?
- Có nên randomize user-agent/fingerprint ở mỗi run hay chỉ cho phép browser type và proxy thay đổi thủ công?
