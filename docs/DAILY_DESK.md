# Bàn giao dịch hằng ngày trên Windows

Mở **http://localhost:5173**. Trang mặc định `/portfolio` là danh mục và kế hoạch;
ledger, replay và phê duyệt thủ công chuyển sang `/portfolio/ledger`.
Đăng nhập quản trị bằng mật khẩu local như trước (không bỏ authentication).

## Tự khởi động đã cài cho tài khoản Windows hiện tại

`install-login-start.ps1` đăng ký duy nhất giá trị `VietnamEquityQuantScanner`
trong HKCU Windows Run. Sau đăng nhập Windows, PowerShell chạy ẩn:

1. Khởi động frontend Windows và API/worker/PostgreSQL/Redis native WSL.
2. Localhost sẵn sàng trước khi tải dữ liệu. Không tự bật cửa sổ trình duyệt.
3. Cập nhật EOD: trước 17h dùng cutoff hôm trước; sau 17h dùng ngày hiện tại.
4. Publish real workspace, scan S1–S4, xử lý các phiên mới cho **cặp FORWARD
   mới nhất**, cả S1 gốc và partial 1R / trailing 2 ATR / maxHold15.

Đây là ủy quyền thường trực cho **giao dịch giả lập** trong workflow đăng nhập,
được người dùng yêu cầu. Script dùng cùng API phê duyệt có authentication và
audit như giao diện; không có broker. Nếu chưa có phiên mới, không ghi ledger.
Mutex tránh chạy trùng startup; API/worker giữ idempotency và transaction cũ.
Lỗi fetch dừng bước paper; ứng dụng vẫn hiện snapshot cũ với ngày rõ ràng.

Log: `.runtime/login-start.log`, `api.log`, `worker.log`. Không ghi mật khẩu/token.
Đây là trigger khi đăng nhập, **không phải dịch vụ trước đăng nhập hoặc lịch
intraday**. Nếu máy giữ phiên Windows qua nhiều ngày, chạy lại workflow thủ công.
Máy cần mạng để cập nhật; dữ liệu public không bảo đảm realtime/SLA.

```powershell
# Cài lại khi chuyển thư mục repo / đổi tài khoản Windows
powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/install-login-start.ps1
# Chạy lại toàn bộ workflow
powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/login-start-windows.ps1
# Chỉ bật app, không cập nhật hay chạy paper
powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/login-start-windows.ps1 -SkipRefresh
# Gỡ tự khởi động
powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/install-login-start.ps1 -Uninstall
```

## Thông tin trên màn hình

- Hai NAV, lợi nhuận, drawdown và winrate theo vị thế đóng hết; mặc định forward.
- Danh mục đang giữ: số lượng, giá vốn, giá EOD, P&L chưa thực hiện, stop và 1R.
- Kế hoạch từ **decision đã đóng băng**, không dùng scan mới hơn để sửa tín hiệu cũ.
- Mua: mô hình mở cửa phiên kế tiếp, không gọi là market/limit gửi sàn.
  Số lượng **ước tính** từ giá đóng cửa + slippage, vốn khả dụng, giới hạn ngành,
  số vị thế, số lệnh mới và risk budget. Engine Decimal vẫn quyết định khớp thực
  tế theo giá mở cửa, tick, thanh khoản, trần/sàn và settlement khi có EOD.
- Bán: điều kiện EMA/thời gian hoặc stop/1R; số cổ phiếu chưa về và bonus chưa rõ
  ngày giao dịch không được đưa vào số lượng có thể bán. Các lệnh điều kiện là
  kế hoạch, không phải xác nhận khớp hay thanh khoản có sẵn.
- Ngày phiên mới chỉ hiện khi nằm trong lịch snapshot; không tự suy đoán lịch nghỉ.
- Click mã hoặc nhập mã mở chart TradingView Lightweight Charts (nến điều chỉnh,
  volume, EMA20/50/200 và đường vào/stop/target nếu có), cùng checklist EOD.
  Điều kiện pass/fail tính từ frozen features; thiếu dữ liệu hiện dấu chưa biết.
  Không có tín hiệu mua khi RISK_OFF là kết quả hợp lệ, không tạo lệnh giả để lấp bảng.

## Kiểm thử

Build/TypeScript, ESLint; unit plan giới hạn vốn/ngành/số lệnh, RISK_OFF, dữ liệu
thiếu và cổ phiếu bị khóa. Browser kiểm localhost → desk, hai danh mục, chart/
checklist thật, dark/light và viewport 390px. Workflow đã chạy từ lúc app dừng,
refresh snapshot thật và no-op paper khi chưa có EOD mới. Registry đã đọc lại
để xác nhận cài đúng. Chưa thực hiện logout/reboot Windows thật trong phiên này.

Chiến lược và ledger engine không đổi: [paper guide](PAPER_TRADING.md).
