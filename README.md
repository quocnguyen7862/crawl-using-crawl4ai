# TopCV Crawl4AI Crawler

Crawler này thu thập danh sách việc làm và trang chi tiết tuyển dụng từ `topcv.vn` bằng Crawl4AI, sau đó xuất dữ liệu theo schema chuẩn hóa.

## Yêu cầu môi trường

- Python `3.11` hoặc `3.12`
- `crawl4ai>=0.7.4`

Lưu ý:
- Workspace ban đầu dùng Python `3.10`, không cài được `crawl4ai`.
- Python `3.14` hiện cũng không phù hợp trên máy này vì dependency `lxml` chưa build được wheel tương thích trong quá trình cài đặt.
- Nên dùng Python `3.11.x` hoặc `3.12.x` để chạy crawler thật với Crawl4AI.

## Cài đặt

```bash
py -3.12 -m pip install -r requirements.txt
```

## Activate `.venv`

Nếu muốn dùng virtual environment trước khi chạy lệnh:

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
python -m pip --version
```

Nếu PowerShell chặn script, có thể dùng trực tiếp interpreter trong env mà không cần activate:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

Khi deactivate:

```powershell
deactivate
```

## Dùng file `.env`

Project hiện hỗ trợ tự đọc file `.env` khi chạy CLI.

Tạo file `.env` từ file mẫu:

```powershell
Copy-Item .env.example .env
```

Sau đó sửa `.env` và điền các giá trị bạn muốn, ví dụ:

```env
CRAWL4_AI_BASE_DIRECTORY=D:\MyPj\Crawl4AI\.crawl4ai-home
PYTHONIOENCODING=utf-8
TOPCV_SEED_URLS=https://www.topcv.vn/viec-lam
TOPCV_MAX_JOBS=100
TOPCV_BATCH_SIZE=20
TOPCV_BATCH_COOLDOWN=30
TOPCV_MAX_CONCURRENT=1
TOPCV_DELAY=8
TOPCV_DELAY_JITTER=3
TOPCV_BROWSER_TYPE=firefox
TOPCV_PROXY_SERVER=http://brd.superproxy.io:33335
TOPCV_PROXY_USERNAME=your_brightdata_username
TOPCV_PROXY_PASSWORD=your_brightdata_password
TOPCV_OUTPUT=output/topcv_jobs_from_env.jsonl
TOPCV_SHOW_ERRORS=true
```

Khi đã có `.env`, bạn có thể chạy ngắn gọn:

```powershell
.\.venv\Scripts\python.exe -m src.topcv_crawler.cli
```

Bạn vẫn có thể override bằng CLI khi cần. Giá trị truyền ở command line sẽ ưu tiên hơn giá trị trong `.env`.

## Chạy crawler

```bash
py -3.12 -m src.topcv_crawler.cli ^
  --seed-url "https://www.topcv.vn/viec-lam" ^
  --max-listing-pages 2 ^
  --max-jobs 30 ^
  --batch-size 10 ^
  --batch-cooldown 5 ^
  --max-concurrent 1 ^
  --delay 5 ^
  --delay-jitter 1.5 ^
  --backoff-multiplier 2.0 ^
  --block-threshold 3 ^
  --format jsonl ^
  --output output/topcv_jobs.jsonl ^
  --show-errors
```

## Giải thích tham số CLI

### Input và phạm vi crawl

- `--seed-url`: URL listing khởi đầu của TopCV. Có thể truyền nhiều lần để crawl từ nhiều seed.
- `--max-listing-pages`: số trang listing tối đa sẽ duyệt cho mỗi seed.
- `--max-jobs`: số job detail tối đa cần crawl trong một run.

### Batch processing

- `--batch-size`: số job detail xử lý trong mỗi batch.
- `--batch-cooldown`: số giây nghỉ giữa hai batch liên tiếp.

Ví dụ `--max-jobs 100 --batch-size 20 --batch-cooldown 15` nghĩa là crawler lấy tối đa 100 job, xử lý 20 job mỗi batch, rồi nghỉ 15 giây giữa các batch.

### Tốc độ crawl

- `--max-concurrent`: số request detail chạy song song.
- `--delay`: số giây nghỉ cơ bản giữa các request.
- `--delay-jitter`: số giây ngẫu nhiên cộng thêm vào `delay` để tránh nhịp request quá đều.

Ví dụ `--delay 5 --delay-jitter 2` nghĩa là mỗi request sẽ nghỉ khoảng từ 5 đến 7 giây.

### Anti-block controls

- `--retry`: số lần retry cho mỗi request khi gặp lỗi.
- `--backoff-multiplier`: hệ số tăng delay khi gặp tín hiệu nghi ngờ bị block.
- `--block-threshold`: số lần gặp tín hiệu `block-suspected` trước khi crawler dừng sớm.

Ví dụ `--backoff-multiplier 2.5 --block-threshold 2` nghĩa là khi xuất hiện block signal, crawler sẽ tăng delay mạnh hơn và dừng sớm nếu gặp 2 lần.

### Browser và proxy

- `--browser-type`: chọn browser engine của Crawl4AI, hiện hỗ trợ `chromium` hoặc `firefox`.
- `--proxy-server`: proxy endpoint, ví dụ `http://host:port`.
- `--proxy-username`: username cho proxy nếu có.
- `--proxy-password`: password cho proxy nếu có.
- `--wait-for`: điều kiện chờ của Crawl4AI, dùng khi trang cần render thêm trước khi scrape.
- `--timeout-ms`: timeout mỗi trang theo milliseconds.

### Output

- `--format`: `json` hoặc `jsonl`.
- `--output`: đường dẫn file output.
- `--show-errors`: in thêm danh sách lỗi cuối run nếu có.

### Biến môi trường quan trọng

Nếu không dùng `.env`, trước khi chạy crawler thật nên đặt:

```powershell
$env:CRAWL4_AI_BASE_DIRECTORY="D:\MyPj\Crawl4AI\.crawl4ai-home"
$env:PYTHONIOENCODING="utf-8"
```

- `CRAWL4_AI_BASE_DIRECTORY`: ép Crawl4AI lưu cache/runtime trong workspace thay vì home directory của user.
- `PYTHONIOENCODING=utf-8`: giảm lỗi encoding khi in log Unicode trên Windows.

### Mapping giữa `.env` và CLI

- `TOPCV_SEED_URLS` tương đương nhiều lần `--seed-url`, ngăn cách bằng dấu phẩy
- `TOPCV_MAX_JOBS` tương đương `--max-jobs`
- `TOPCV_BATCH_SIZE` tương đương `--batch-size`
- `TOPCV_BATCH_COOLDOWN` tương đương `--batch-cooldown`
- `TOPCV_MAX_CONCURRENT` tương đương `--max-concurrent`
- `TOPCV_DELAY` tương đương `--delay`
- `TOPCV_DELAY_JITTER` tương đương `--delay-jitter`
- `TOPCV_BACKOFF_MULTIPLIER` tương đương `--backoff-multiplier`
- `TOPCV_BLOCK_THRESHOLD` tương đương `--block-threshold`
- `TOPCV_BROWSER_TYPE` tương đương `--browser-type`
- `TOPCV_PROXY_SERVER` tương đương `--proxy-server`
- `TOPCV_PROXY_USERNAME` tương đương `--proxy-username`
- `TOPCV_PROXY_PASSWORD` tương đương `--proxy-password`
- `TOPCV_OUTPUT` tương đương `--output`
- `TOPCV_OUTPUT_FORMAT` tương đương `--format`
- `TOPCV_SHOW_ERRORS=true|false` tương đương `--show-errors`

## Chạy an toàn hơn để giảm block IP

Với các site dễ rate-limit như `topcv.vn`, nên ưu tiên:

- `--max-concurrent 1`
- `--delay 4` đến `8`
- `--delay-jitter 1` đến `3`
- `--retry 1`
- `--block-threshold` nhỏ để dừng sớm nếu bắt đầu bị chặn

Ví dụ:

```bash
$env:CRAWL4_AI_BASE_DIRECTORY="D:\MyPj\Crawl4AI\.crawl4ai-home"
py -3.12 -m src.topcv_crawler.cli ^
  --seed-url "https://www.topcv.vn/viec-lam" ^
  --max-listing-pages 1 ^
  --max-jobs 10 ^
  --max-concurrent 1 ^
  --delay 6 ^
  --delay-jitter 2 ^
  --backoff-multiplier 2.5 ^
  --block-threshold 2 ^
  --browser-type firefox ^
  --proxy-server "http://proxy-host:port" ^
  --format jsonl ^
  --output output/topcv_jobs.jsonl ^
  --show-errors
```

Nếu không dùng proxy hoặc Firefox, cứ bỏ hai cờ đó đi. Crawler sẽ vẫn chạy với mặc định `chromium`.

## Crawl theo N job và chia batch

Để crawl `N` job nhưng xử lý theo batch nhỏ hơn, dùng:

- `--max-jobs N`
- `--batch-size M`
- `--batch-cooldown S`

Ví dụ crawl `1000` job, xử lý theo batch `100` job:

```bash
$env:CRAWL4_AI_BASE_DIRECTORY="D:\MyPj\Crawl4AI\.crawl4ai-home"
py -3.12 -m src.topcv_crawler.cli ^
  --seed-url "https://www.topcv.vn/viec-lam" ^
  --max-listing-pages 50 ^
  --max-jobs 1000 ^
  --batch-size 100 ^
  --batch-cooldown 20 ^
  --max-concurrent 1 ^
  --delay 8 ^
  --delay-jitter 3 ^
  --backoff-multiplier 2.5 ^
  --block-threshold 2 ^
  --format jsonl ^
  --output output/topcv_jobs_1000.jsonl ^
  --show-errors
```

Với cách này, crawler vẫn lấy tối đa `1000` job nhưng sẽ xử lý tuần tự từng batch `100` job để giảm nguy cơ bị block IP.

## Output schema

Mỗi bản ghi job có các trường:

- `url`
- `title`
- `company_name`
- `location`
- `salary`
- `job_level`
- `employment_type`
- `posted_at`
- `deadline`
- `job_description`
- `requirements`
- `benefits`
- `crawl_time`
- `source`

## Kiểm thử cục bộ

Các test hiện dùng fake crawler và fixture HTML/markdown để kiểm tra:

- discovery từ listing
- lọc URL chi tiết hợp lệ
- extract job detail và chuẩn hóa dữ liệu
- deduplicate
- hành vi tiếp tục khi một trang lỗi
- bootstrap failure
- block detection, jitter, và early-stop behavior

Chạy test:

```bash
py -3.14 -m unittest discover -s tests -v
```
