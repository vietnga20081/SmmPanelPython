# SMM Panel — Phase 1: Authentication

## Kiến trúc
FastAPI + SQLAlchemy (SQLite, WAL) + Jinja2 + Bootstrap 5 + HTMX. Không Docker,
không Redis, không Celery, không microservice — monolithic, tối ưu cho VPS cấu
hình thấp.

```
Route -> Service -> Repository -> Database
```

## Đã hoàn thành trong Phase 1
- Session Login (cookie ký bởi `itsdangerous`, `httponly`, `secure` khi production).
- Remember Login (token ngẫu nhiên, chỉ lưu hash SHA-256 trong DB).
- Password Hash (bcrypt qua passlib).
- CSRF Protection (token theo session, dependency `verify_csrf` áp cho mọi route
  POST render từ form).
- Rate Limit Login (khóa tạm sau N lần sai trong X phút, cấu hình qua `.env`).
- Phân quyền theo Role: `admin`, `staff`, `client` (`app/core/dependencies.py`).
- Structured logging (JSON, rotate theo ngày) cho `app`, `audit`, `login`,
  `payment`, `api`.
- SQLite tối ưu: WAL, synchronous=NORMAL, foreign_keys=ON, cache_size, mmap,
  busy_timeout — áp dụng tự động qua event listener khi mỗi connection mở.
- JWT utility (`create_access_token` / `decode_access_token`) đã sẵn sàng cho
  Phase API sau này.

## Chạy thử
```bash
cd smm_panel
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # sửa SECRET_KEY, JWT_SECRET_KEY trước khi deploy thật
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Truy cập `http://127.0.0.1:8000/login`.

Tài khoản admin mặc định được tạo tự động lần chạy đầu tiên:
- username: `admin`
- password: `ChangeMe123!`

**Đổi mật khẩu này ngay sau khi đăng nhập lần đầu trên môi trường thật.**

## Ghi chú triển khai production
- Đặt `DEBUG=false` (mặc định) để cookie session/remember-me bắt buộc `Secure`
  (chỉ gửi qua HTTPS) — cần chạy sau Nginx/reverse proxy có TLS.
- `SECRET_KEY` và `JWT_SECRET_KEY` phải là chuỗi ngẫu nhiên dài, khác nhau,
  không commit vào git.
- File DB nằm tại `DATABASE_PATH` (mặc định `./data/smm_panel.db`), nhớ backup
  định kỳ (`VACUUM` qua `app.core.database.vacuum_sqlite()` nên chạy off-peak).

## Cấu trúc module (chuẩn cho các Phase sau)
Mỗi module business (`users`, `orders`, `services`, `providers`, ...) sẽ theo
đúng khuôn của `app/modules/auth/`: `models.py`, `repository.py`, `service.py`,
`schemas.py`, `routes.py`, `validators.py`.

## Provider tham khảo (từ tài liệu API bạn cung cấp)
Tài liệu `KingSmm.vn` mô tả API chuẩn kiểu SMM-panel-v2 (`services`, `add`,
`status`, `status` nhiều đơn, `cancel`, `balance`, `refill`, `refill_status`).
Đây chính xác là chuẩn mà `BaseProvider` ở Provider Engine (Phase sau) cần hỗ
trợ — mỗi provider (KingSmm, PerfectPanel, JustAnotherPanel, ...) chỉ cần
implement lại `BaseProvider` với endpoint/action tương ứng.

## Tiếp theo
Đợi xác nhận để làm **Phase 2 — Dashboard**.

---

## Phase 2 — Dashboard (đã hoàn thành)

- Layout dùng chung `layout_app.html` (sidebar + topbar), tái sử dụng cho mọi
  trang đã đăng nhập sau này (Order, Service, Wallet, ...).
- Sidebar hiển thị menu theo role; các mục thuộc module chưa xây (Orders,
  Providers, Wallet, ...) hiện dạng disabled kèm badge "Sắp ra mắt" — chỉ là
  khung UI, chưa có logic, sẽ bật dần ở các Phase sau.
- `GET /dashboard` (đã thay route stub Phase 1):
  - **Admin/Staff** → `dashboard/admin.html`: tổng số user, số đang hoạt
    động/vô hiệu hóa, user mới trong 7 ngày, breakdown theo role, bảng user
    đăng ký gần đây.
  - **Client** → `dashboard/client.html`: số dư, vai trò, trạng thái tài
    khoản, ngày tham gia.
- Module `dashboard` theo đúng khuôn Repository → Service → Route, chỉ đọc
  dữ liệu (không ghi), không phụ thuộc module nào chưa tồn tại.
- Topbar có dropdown user + nút đăng xuất (CSRF-protected, dùng lại
  `verify_csrf` dependency từ Phase 1).

Đợi xác nhận để làm **Phase 3**.

---

## Áp dụng giao diện Gentelella v4 (Colorlib)

Đã thay toàn bộ giao diện Bootstrap5 tự viết bằng **Gentelella v4** (bản Vite,
"no Bootstrap, no jQuery" — colorlib/gentelella).

**Quyết định kỹ thuật quan trọng:** không nhúng file `main-v4.js` gốc của họ.
File đó gắn 1 listener toàn cục lên MỌI `<form>` để giả lập submit
(`preventDefault()` + toast + reset) phục vụ mục đích demo tĩnh không backend
— nếu dùng nguyên bản, nó sẽ chặn đứng mọi form thật (login, tạo user,
...) gửi lên FastAPI. Thay vào đó:

- Chỉ lấy **CSS đã build** (`main-v4.css`, ~150KB) → `app/static/gentelella/css/`.
- Tự viết lại phần JS tương tác thuần túy cần thiết (`app/static/gentelella/js/panel.js`,
  ~150 dòng): toggle sidebar (rail/drawer), accordion menu, dark mode, dropdown
  avatar — không đụng gì đến form thật, không có demo/fake data.
- Sidebar là **tự thiết kế** theo đúng module của SMM Panel (Dashboard, Người
  dùng, ...) — không dùng nguyên bộ menu demo 60 trang của họ.
- Font Inter tải qua Google Fonts CDN (giữ nguyên như bản gốc).

Không cần Node.js/npm trên server production — toàn bộ đã là file tĩnh
(css/js) copy sẵn vào `app/static/`.

## Phase 3 — Users module (đã hoàn thành)

- `GET /admin/users` — danh sách + tìm kiếm (username/email) + lọc theo
  role/status + phân trang (10/trang), chỉ **admin**.
- `GET|POST /admin/users/new` — tạo user (validate trùng username/email,
  độ mạnh mật khẩu dùng lại từ auth module).
- `GET|POST /admin/users/{id}/edit` — sửa email/role/trạng thái hoạt động.
- `POST /admin/users/{id}/reset-password` — đặt lại mật khẩu cho user khác.
- `POST /admin/users/{id}/toggle-active` — khóa/mở khóa nhanh từ danh sách.
- **Cơ chế bảo vệ**: admin không thể tự bỏ quyền admin hoặc tự khóa chính
  mình; hệ thống luôn phải còn ít nhất 1 admin đang hoạt động (chặn hành
  động khiến số admin hoạt động về 0), áp dụng cho cả sửa thủ công lẫn nút
  toggle nhanh.
- Module `users` không định nghĩa lại bảng `User` (dùng chung với module
  `auth`) — tránh trùng lặp bảng, đúng tinh thần "một entity, nhiều module
  cùng thao tác qua repository riêng của từng module".

Đợi xác nhận để làm **Phase 4**.

---

## Phase 4 — Provider Engine (đã hoàn thành)

**Kiến trúc 2 lớp, tách biệt rõ ràng:**

- `app/providers/` — **plugin engine thuần túy**, không đụng DB:
  - `base.py` — `BaseProvider` abstract class: `get_balance`, `list_services`,
    `add_order`, `get_status`, `get_multi_status`, `cancel`, `refill`,
    `get_refill_status`. Mọi lỗi chuẩn hóa về `ProviderAPIError`.
  - `generic_smm.py` — plugin cho chuẩn **"SMM Panel API v2"** (POST 1
    endpoint, body `key`+`action`) — đúng theo tài liệu KingSmm.vn bạn gửi
    (`https://kingsmm.vn/api/v2`, actions: `services`, `add`, `status`,
    `cancel`, `balance`, `refill`, `refill_status`). Chuẩn này dùng chung bởi
    rất nhiều provider khác (PerfectPanel-compatible) — chỉ cần đổi
    `api_url`/`api_key`, không cần code riêng.
  - `registry.py` — map `driver` (string lưu trong DB) → class plugin. Thêm
    provider loại mới = thêm 1 file + 1 dòng registry, không sửa code khác.

- `app/modules/providers/` — **module DB-backed** theo đúng khuôn Repository
  → Service → Route: lưu tài khoản provider (tên, driver, URL, API key),
  CRUD qua `/admin/providers`, và nút **Test** gọi action `balance` thật qua
  Provider Engine để xác nhận kết nối + cache số dư.

- Route đã test: list, tạo, sửa, xóa, khóa/mở khóa, test connection (đã test
  cả tình huống provider trả lỗi/mạng chặn — xử lý gracefully, không crash
  app), chặn trùng tên, chặn URL sai định dạng, chỉ **admin** truy cập được.

**Lưu ý bảo mật:** API key hiện lưu dạng plaintext trong SQLite để hệ thống
gọi được API thay bạn — đảm bảo chỉ admin có quyền truy cập server/DB. Có
thể nâng cấp mã hóa tại chỗ (Fernet dùng `SECRET_KEY`) ở phase sau nếu cần.

Đợi xác nhận để làm **Phase 5** (đề xuất: **Services** — danh mục dịch vụ
map tới `service_id` của từng provider, giá nhập/giá bán/markup — làm nền
cho Order Engine).

---

## Phase 5 — Services: Sync + phân loại Platform → Category → Service

**Kiến trúc 3 tầng:**
- `Platform` (Facebook, TikTok, Instagram, YouTube, Telegram, Threads,
  X/Twitter, Shopee, Lazada, Spotify, LinkedIn, Reddit, Pinterest, Twitch,
  Discord, Kwai, Bigo, Zalo, Google, Website, Khác) — seed sẵn khi khởi động.
- `Category` (Like, Comment, Follow, Subscribe, Member, View, Share,
  Livestream, Watch Time, Story, Review, Traffic, Plays, Message, Khác) —
  tạo tự động theo platform khi cần (get-or-create), không cần seed trước.
- `Service` — bản ghi catalog thật, đồng bộ 1-1 với `provider_service_ref`
  của từng Provider (`unique(provider_id, provider_service_ref)`).

**`app/modules/services/classifier.py`** — bộ phân loại rule-based thuần
Python, không gọi AI/DB:
- Chuẩn hóa text (bỏ dấu tiếng Việt, hạ chữ thường), rồi so khớp từ khóa
  theo **thứ tự ưu tiên** (vd. kiểm tra "livestream" trước "view", vì
  "LiveStream Viewers" chứa cả hai — sai thứ tự sẽ phân loại nhầm thành View).
- Input: category gốc + tên dịch vụ + mô tả từ provider (gộp lại rồi so
  khớp) — đúng yêu cầu "dựa vào tên danh mục, tên dịch vụ, mô tả dịch vụ".
- Đã test bằng dữ liệu thật lấy từ tài liệu KingSmm.vn bạn gửi (Facebook
  Like, TikTok LiveStream Viewers, Youtube Watchtime, Group Member Facebook,
  Shopee Review, Website Traffic, Google Maps Review, Twitter Retweets, ...)
  — toàn bộ phân loại đúng.

**Đồng bộ (`POST /admin/services/sync`):**
- Gọi `provider.list_services()` qua Provider Engine (Phase 4), với mỗi
  service: phân loại Platform + Category, rồi **upsert** vào bảng `services`
  (tạo mới nếu chưa có, cập nhật giá nhập/min/max/refill/... nếu đã có).
- Giá bán (`sell_price`) **không bao giờ bị ghi đè khi sync** — chỉ admin
  chỉnh tay qua trang Sửa. Dịch vụ mới sync về mặc định `is_active=False`
  (chưa bán) để admin review giá trước khi mở bán.
- Một service lỗi (thiếu id, dữ liệu hỏng...) không làm hỏng cả lượt đồng
  bộ — đếm riêng `failed`, các service khác vẫn xử lý bình thường.

**Khóa phân loại thủ công:** nếu admin tự đổi Platform/Category ở trang Sửa,
service đó được đánh dấu `platform_locked`/`category_locked` — các lần đồng
bộ sau sẽ **giữ nguyên** lựa chọn thủ công thay vì phân loại lại (đã test:
đổi Facebook → Instagram thủ công, re-sync xong vẫn là Instagram).

**Routes:** `GET /admin/services` (danh sách + lọc platform/category/
provider/trạng thái + KPI theo platform), `POST /admin/services/sync`,
`GET|POST /admin/services/{id}/edit`, `POST /admin/services/{id}/toggle-active`
— tất cả chỉ admin (đã test 403 với client).

Đợi xác nhận để làm **Phase 6** (đề xuất: **Order Engine** — giờ đã có đủ
Provider + Service để client đặt hàng thật: Order/Refill/Cancel/Partial/
Drip-feed/Subscriptions như spec gốc yêu cầu).

---

## Bổ sung Phase 5: Markup % theo Provider + Chỉnh sửa hàng loạt

**Markup % (`providers.markup_percent`):**
- Cài đặt ngay trong trang Sửa Provider (`/admin/providers/{id}/edit`).
- Khi đồng bộ: `sell_price = provider_rate × (1 + markup% / 100)`, tự động
  tính cho **dịch vụ mới** và **cập nhật lại mỗi lần sync** cho dịch vụ cũ
  — miễn là giá đó chưa bị khóa (`price_locked`).
- `price_locked` hoạt động giống hệt `platform_locked`/`category_locked` ở
  Phase 5: sửa giá tay (trang Sửa dịch vụ) hoặc áp dụng markup hàng loạt sẽ
  tự động khóa giá đó khỏi bị ghi đè ở lần sync sau. Dịch vụ đã khóa giá
  hiện icon 🔒 trong bảng danh sách.

**Chỉnh sửa hàng loạt (trang `/admin/services`):**
- Checkbox từng dòng + "Chọn tất cả" ở đầu bảng, đếm số đã chọn realtime.
- 3 thao tác hàng loạt cho các dịch vụ đã chọn:
  1. **Áp dụng markup %** — tính lại giá bán theo % nhập trực tiếp (không
     cần sửa markup của provider), khóa giá các dịch vụ đó.
  2. **Áp dụng trạng thái** — bật/tắt bán hàng loạt.
  3. **Áp dụng danh mục** — gán lại Platform + Category hàng loạt, khóa
     phân loại tự động cho các dịch vụ đó.
- Kỹ thuật: toàn bộ bảng + toolbar nằm trong **một form duy nhất**
  (`/admin/services/bulk`); nút toggle riêng từng dòng dùng thuộc tính HTML5
  `formaction` để trỏ sang route khác mà không cần lồng `<form>` (vốn không
  hợp lệ trong HTML) — vẫn dùng chung 1 CSRF token của form cha.
- Đã test: markup hàng loạt chỉ ảnh hưở; dịch vụ không được chọn giữ nguyên;
  giá đã khóa không bị ghi đè khi re-sync; chưa chọn dịch vụ nào → báo lỗi
  rõ ràng thay vì áp dụng nhầm lên toàn bộ.

**Migration nhẹ cho SQLite** (`app/core/schema_migrations.py`): vì
`Base.metadata.create_all()` không tự thêm cột mới vào bảng đã tồn tại, 2
cột mới (`providers.markup_percent`, `services.price_locked`) được thêm qua
`ALTER TABLE` tự động, idempotent, chạy mỗi lần khởi động — deploy trên
aaPanel chỉ cần copy đè file + restart, không cần chạy lệnh migrate thủ công.
