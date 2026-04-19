## Context

Workspace hiện chưa có implementation hay đặc tả sẵn cho việc crawl `topcv.vn`. Nhu cầu trước mắt là dùng Crawl4AI để thu thập dữ liệu tuyển dụng theo cách có thể lặp lại, giới hạn được phạm vi crawl, và xuất ra dữ liệu có cấu trúc để phục vụ phân tích hoặc nạp tiếp sang pipeline khác.

`topcv.vn` có thể chứa nội dung render động, phân trang, và nhiều liên kết ngoài phạm vi cần crawl. Vì vậy thiết kế phải ưu tiên kiểm soát seed URL, chọn lọc trang chi tiết tuyển dụng hợp lệ, và chuẩn hóa tập trường dữ liệu tối thiểu để tránh một crawler "crawl mọi thứ" nhưng dữ liệu đầu ra thiếu nhất quán.

## Goals / Non-Goals

**Goals:**
- Tạo một crawler dựa trên Crawl4AI cho phép bắt đầu từ một hoặc nhiều URL danh sách việc làm của `topcv.vn`.
- Thu thập được cả metadata từ trang danh sách và thông tin chi tiết từ trang job detail.
- Chuẩn hóa đầu ra thành bản ghi có cấu trúc, hỗ trợ deduplicate theo URL hoặc job identifier.
- Xử lý được các lỗi phổ biến như timeout, trang detail lỗi, hoặc thiếu một số trường không bắt buộc mà không làm hỏng toàn bộ phiên crawl.

**Non-Goals:**
- Không bao phủ toàn bộ mọi loại trang trên `topcv.vn` như blog, hồ sơ công ty, hay landing page marketing.
- Không giải quyết ở giai đoạn này việc crawl có xác thực người dùng.
- Không cam kết tích hợp ngay với database, scheduler, hay hệ thống giám sát ngoài file đầu ra cục bộ.

## Decisions

### 1. Tách crawl thành hai lớp: listing discovery và job detail extraction

Crawler sẽ bắt đầu từ seed URL trang danh sách việc làm, thu thập các liên kết job detail hợp lệ, sau đó truy cập từng trang chi tiết để trích xuất dữ liệu chuẩn hóa. Cách này dễ kiểm soát phạm vi hơn so với crawl toàn site theo link graph.

Phương án thay thế là crawl đệ quy từ một seed và lọc theo pattern URL. Tôi không chọn cách này vì dễ tạo nhiều request ngoài phạm vi tuyển dụng và khó kiểm soát chất lượng dữ liệu.

### 2. Chuẩn hóa output schema ở mức "job record" trước khi viết code

Mỗi bản ghi job sẽ ưu tiên các trường: `url`, `title`, `company_name`, `location`, `salary`, `job_level`, `employment_type`, `posted_at`, `deadline`, `job_description`, `requirements`, `benefits`, `crawl_time`, và `source`. Những trường không đọc được vẫn giữ key với giá trị rỗng hoặc `null` thay vì bỏ hẳn.

Phương án thay thế là chỉ lưu HTML/markdown thô rồi xử lý sau. Tôi không chọn cách này vì user đang yêu cầu crawl data chứ không chỉ thu snapshot trang, và việc thiếu schema sẽ làm bước downstream tốn công hơn.

### 3. Giới hạn phạm vi bằng domain + URL pattern + pagination budget

Crawler chỉ theo domain `www.topcv.vn` và chỉ nhận các URL khớp với trang listing hoặc job detail đã định nghĩa. Thiết kế cũng cần giới hạn số trang listing hoặc tổng số job trong mỗi phiên để tránh crawl không kiểm soát.

Phương án thay thế là chỉ giới hạn theo domain. Tôi không chọn vì một domain-wide crawl trên `topcv.vn` sẽ đi vào nhiều nội dung không liên quan.

### 4. Tolerant extraction thay vì fail-fast toàn bộ run

Nếu một trang detail lỗi hoặc thiếu trường, crawler sẽ ghi log lỗi cho bản ghi đó và tiếp tục với các URL còn lại. Chỉ các lỗi ở mức bootstrap như seed URL không truy cập được hoặc selector/prompt extraction hỏng toàn cục mới làm run thất bại.

Phương án thay thế là dừng ngay ở lỗi đầu tiên để đơn giản hóa xử lý. Tôi không chọn vì dữ liệu tuyển dụng thường có dị biệt HTML giữa các tin, fail-fast sẽ làm giảm hiệu quả thu thập.

## Risks / Trade-offs

- [Cấu trúc HTML thay đổi hoặc render động] -> Giảm thiểu bằng cách giữ extraction logic tách biệt, có selector dự phòng, và ghi rõ trường nào bị thiếu trong log.
- [Bị chặn do request quá dày] -> Giảm thiểu bằng cách cấu hình concurrency thấp, delay giữa request, và retry có backoff.
- [Trùng lặp job giữa nhiều trang listing] -> Giảm thiểu bằng deduplicate theo URL canonical hoặc identifier từ trang chi tiết.
- [Một số trường dữ liệu không có mặt trên mọi tin] -> Giảm thiểu bằng schema cho phép `null` ở trường không bắt buộc nhưng vẫn giữ các trường lõi bắt buộc.

## Migration Plan

1. Tạo module crawler và cấu hình seed URL trong workspace.
2. Cài extraction cho listing và detail theo schema đã chốt.
3. Chạy thử trên tập URL nhỏ để xác nhận phạm vi và chất lượng dữ liệu.
4. Mở rộng giới hạn trang hoặc số job sau khi đã kiểm tra kết quả đầu ra.

Không có migration dữ liệu cũ vì đây là capability mới hoàn toàn. Nếu rollout thất bại, chỉ cần dừng sử dụng crawler mới và xóa dữ liệu thử nghiệm.

## Open Questions

- `topcv.vn` có yêu cầu JavaScript rendering đầy đủ cho tất cả listing/detail quan trọng hay chỉ cho một số trang?
- User muốn đầu ra mặc định là JSON, JSONL, CSV, hay nhiều định dạng cùng lúc?
- Có cần lọc trước theo từ khóa, địa điểm, hoặc ngành nghề ngay ở phiên bản đầu hay chỉ crawl theo seed URL được cung cấp?
