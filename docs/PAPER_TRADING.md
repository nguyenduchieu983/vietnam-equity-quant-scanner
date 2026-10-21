# Paper S1 song song trên Windows

Mở http://localhost:5173 để xem bàn giao dịch hằng ngày; ledger và phê duyệt
thủ công ở `/portfolio/ledger`. Đăng nhập bằng mật khẩu local trong `.env`.
Workflow đăng nhập Windows có thể tự cập nhật và phê duyệt paper theo ủy quyền
đã cài: [Daily Desk](DAILY_DESK.md). Các bước thủ công bên dưới vẫn dùng được.
Hai tài khoản độc lập, mỗi tài khoản 50 triệu VND, dùng cùng snapshot và cùng
phiên được phê duyệt:

- **S1**: điều kiện S1 gốc, maxHold 30.
- **S1_PARTIAL**: điều kiện vào S1 gốc, chốt 50% tại 1R theo lô 100,
  phần còn lại trailing 2 ATR sau lần chốt đầu, maxHold 15.

Stop ban đầu, EMA50, thanh khoản, settlement và giới hạn rủi ro vẫn áp dụng.
Trailing dùng dữ liệu phiên trước và chỉ dời lên. Vị thế chỉ 100 cổ phiếu không
được chia thành lô giả 50: sau chạm 1R sẽ bật trailing cho cả vị thế từ phiên sau.
MaxHold giữ đúng engine đã nghiên cứu: thoát khi số phiên từ mua **lớn hơn** 15
(hoặc 30), và còn phụ thuộc cổ phiếu đã về, thanh khoản, lô lẻ.
Phí mua/bán 0,15%, thuế bán 0,10%, slippage 0,10% mỗi chiều.

## Forward và replay

**FORWARD** bắt đầu bằng tiền mặt, đóng băng tín hiệu EOD gần nhất lúc tạo.
Chỉ mô phỏng phiên mới từ ngày khởi tạo trở đi; không gán lợi nhuận lịch sử cho
tài khoản forward. Hiện snapshot đến 20/10/2026, chờ snapshot EOD tiếp theo.

**REPLAY** là tài khoản riêng để xem lại dữ liệu thật và kiểm tra vận hành.
Cặp nghiệm thu chạy 34 phiên từ 03/09 đến 20/10/2026. S1: NAV 49.732.380 VND,
lợi nhuận -0,54%, drawdown -1,84%, 0/3 vị thế thắng. Partial: NAV 50.146.342,50
VND, lợi nhuận +0,29%, drawdown -1,01%, 1/3 vị thế thắng. Mẫu rất nhỏ; đây
không phải kết quả paper forward. Winrate gộp toàn bộ lần bán và cổ tức của
mỗi vị thế đã đóng hết, không đếm mỗi lần chốt một phần thành một lệnh thắng.

Nguồn VNDIRECT public, cohort 100 mã cố định theo thanh khoản tháng 12/2023;
metadata và corporate actions vẫn có hạn chế lịch sử. Dữ liệu raw nằm trong
`.runtime`, không commit. Paper dùng bảng snapshot riêng. Dashboard, Scanner,
trang mã và Strategy Lab hiện đã nối vào kho real với DATA_MODE=real.
Không có kết nối đặt lệnh broker.

## Cập nhật mỗi ngày

Khởi động môi trường đã chuẩn bị theo [LOCAL_WINDOWS.md](LOCAL_WINDOWS.md),
sau đó chạy PowerShell từ thư mục repo (sau 17h giờ Việt Nam):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/dev-start-windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/paper-refresh-windows.ps1
```

Có thể chỉ định `-Cutoff 2026-10-21`. Script tải snapshot, kiểm hash/chất lượng,
nạp PostgreSQL; không tự chạy ledger. Trên giao diện bấm **Làm mới**, chọn cặp
FORWARD mới nhất, **Xem trước & mô phỏng phiên mới**, rồi **Phê duyệt & chạy cả hai**.
Một phê duyệt chạy cả hai tài khoản trong cùng transaction. Khi chưa có EOD mới,
nút phê duyệt bị khóa. Downloader hiện tải snapshot đầy đủ, chưa phải incremental
feed; lần đầu có thể mất vài phút, retry có giới hạn và cache theo ngày cutoff.

Linux native: `bash infra/scripts/paper-refresh.sh YYYY-MM-DD` với runtime và
`.env` theo runbook. Script không cài cron; thao tác phê duyệt hiện là thủ công.
Các service production dùng PM2/systemd theo runbook hiện có. Restart ứng dụng
Windows/WSL đã kiểm tra; không coi đó là nghiệm thu reboot máy chủ production.

## Ledger và phục hồi

PostgreSQL lưu cash, tiền chờ về, cổ phiếu chờ bán, partial budget, trailing stop,
peak NAV, tín hiệu/features đóng băng của phiên trước và hash engine. Ngày trả
cổ tức được giữ theo ngày thực; cổ phiếu thưởng chưa rõ ngày được bán tiếp tục
bị khóa khi nối thêm lịch. Không tự diễn giải thông tin mới thành quyền bán.

Session, approval và snapshot chặn UPDATE/DELETE. Approval lặp lại trả cùng job;
khóa cặp và khóa phiên chống ghi trùng. Worker dùng lease/heartbeat, checkpoint
durable; lỗi giữa batch rollback cả hai tài khoản. Thiếu bar của vị thế đang giữ,
corporate action chưa rõ hoặc engine thay đổi sẽ chặn chạy tiếp để kiểm tra.
Khi thay engine, tạo cặp mới; giữ cặp cũ để đối chiếu, không sửa lịch sử.
Các cặp kiểm thử engine cũ vẫn hiện trong danh sách; dùng cặp mới nhất.

Giao diện có NAV/benchmark, chỉ số so sánh, vị thế, sổ giao dịch, lệnh không khớp,
tín hiệu phiên sau, nhật ký phê duyệt và xuất ledger JSON. Chưa có trình nhập lệnh
paper tùy ý hoặc scheduler tự phê duyệt; đây là paper EOD cho hai chiến lược cố định.

## Kiểm chứng

- 43 Python tests, gồm checkpoint/resume, partial, settlement và nối lịch.
- Ruff, mypy, TypeScript/Vite build, ESLint và 2 API unit tests.
- `node infra/scripts/smoke-paper.mjs init`, restart dịch vụ,
  `node infra/scripts/smoke-paper.mjs continue`: auth, idempotency, hai tài khoản,
  forward rỗng, chạy tiếp sau restart, NAV reconciliation.
- `PYTHONPATH=apps/quant-worker .runtime/linux-venv/bin/python infra/scripts/verify-paper-ledger.py`
  trên WSL: đối chiếu replay với engine chạy liền mạch, kiểm chặn sửa/xóa ledger.
  Benchmark dùng close trước phiên đầu; đối chiếu bỏ riêng khác biệt mốc benchmark.
  Thứ tự các lần bán độc lập trong cùng phiên có thể đổi do JSONB sắp xếp key.
- `node tests/e2e/paper-browser.mjs`: forward, dialog phê duyệt, replay, biểu đồ,
  xuất JSON, dark/light, mobile và lỗi JavaScript.

Các script smoke dùng snapshot/mốc ngày nghiệm thu 20/10/2026, không phải tác vụ
chạy hàng ngày. Kết quả aggregate: [verification](verification/paper-2026-10-21.json).
