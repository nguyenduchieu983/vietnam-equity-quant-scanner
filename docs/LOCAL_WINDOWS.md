# Chạy local trên Windows

Theo yêu cầu hiện tại, ưu tiên xem và kiểm thử trên máy Windows; chưa triển khai VPS.

Mô hình đang dùng:
- Frontend Vite: Node 22 trên Windows, `http://127.0.0.1:5173`.
- API NestJS và Python worker: process native trong WSL `Ubuntu-22.04`.
- PostgreSQL/Redis: service native WSL. Database riêng `quant_m0`.
- Không có broker thật. M0 chỉ có dữ liệu fixture DEMO.

Máy này đã được chuẩn bị runtime Linux cô lập dưới `.runtime/`:
`node-v22.19.0-linux-x64/bin/node` và `linux-venv/bin/python` (Python 3.12).
Không đổi Node/Python hệ thống cũ của WSL.

Tại thư mục dự án, chạy PowerShell:

```powershell
.\infra\scripts\dev-start-windows.ps1
# Sau lần build đầu, có thể bỏ build khi chỉ xem bản hiện tại:
.\infra\scripts\dev-start-windows.ps1 -SkipBuild

# Dừng đúng process dự án; không dừng DB/Redis dùng chung:
.\infra\scripts\dev-stop-windows.ps1
```

Đăng nhập bằng giá trị `SMOKE_ADMIN_PASSWORD` trong `.env` tại máy này.
Token chỉ ở bộ nhớ trình duyệt; reload trang sẽ cần đăng nhập lại.
Dark/light lưu riêng trong localStorage.

Launcher giữ một process WSL nền, không mở thêm cửa sổ; dừng bằng script stop ở trên.
Service local này chưa được cấu hình tự mở sau khi Windows reboot.
Yêu cầu auto-start production Linux được theo dõi riêng tại AC17.

Đây là launcher cho môi trường local đã chuẩn bị, không phải bộ cài Windows sạch.
Máy khác cần WSL, database/Redis native, Node 22 và Python 3.12 trước.
Có thể chỉ định `QUANT_LOCAL_NODE` và `QUANT_LOCAL_PYTHON` trong `.env` để dùng
runtime Linux đã cài tại đường dẫn khác. Dependencies Python cài từ
`requirements-dev.lock` với `--require-hashes`; Node cài `npm ci`.

Logs: `.runtime/api.log`, `.runtime/worker.log`,
`.runtime/web-windows.log`, `.runtime/web-windows-error.log`.

Giao diện chưa phải sản phẩm M4: scanner chưa có engine; biểu đồ mã,
Strategy Lab và Paper Portfolio ghi rõ milestone chưa triển khai.
