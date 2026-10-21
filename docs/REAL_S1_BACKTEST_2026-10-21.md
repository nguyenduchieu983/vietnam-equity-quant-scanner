# S1 trên dữ liệu thị trường thật — 21/10/2026

**Kết quả nghiên cứu sơ bộ: 17 thắng / 45 vị thế đã đóng hết = 37,78%.**
Giữ nguyên bộ lọc S1 và giới hạn danh mục, không tối ưu theo kết quả này.

| Chỉ tiêu | Kết quả |
| --- | --- |
| Giai đoạn backtest | 04/09/2024–16/10/2026, 528 phiên thực tế |
| Phạm vi | 100 cổ phiếu HOSE/HNX, chọn theo thanh khoản tháng 12/2023 |
| Vốn ban đầu | 50.000.000 VND |
| Vị thế đóng hết | 45: 17 thắng, 28 thua, 0 hòa |
| Win rate vị thế đóng hết | 37,78% |
| Số lần khớp bán | 48; chỉ số hitRate theo lần bán là 39,58% |
| Lợi nhuận danh mục | +5,83311%, NAV cuối 52.916.555 VND |
| CAGR | +2,74%/năm |
| Sụt giảm lớn nhất | −6,62% |
| VNINDEX giá, cùng kỳ từ giá mở phiên đầu | +34,18%; không gồm tái đầu tư cổ tức |
| Bình quân vị thế đóng hết | Khoảng 1,8/tháng |

48 lần bán gồm phần bán của ba vị thế còn cổ phiếu thưởng/lô lẻ: LPB 16,
SHB 13, MSB 24 cổ phiếu. Cả ba không nằm trong mẫu 45 vị thế đóng hết.
NAV vẫn bao gồm giá trị phần còn giữ. Không thể so trực tiếp 37,78% với
100% của 7 lệnh DEMO: DEMO dùng giá giả và chỉ 8 mã.

## Nguồn và phương pháp

Giá raw, giá điều chỉnh, khối lượng/giá trị khớp lệnh, biên giá, sự kiện doanh
nghiệp và VNINDEX lấy từ API public của VNDIRECT:
`https://api-finfo.vndirect.com.vn/v4/` (stock_prices, vnmarket_prices, events,
stocks). Ngành lấy từ snapshot hiện tại của Vietcap:
`https://trading.vietcap.com.vn/api/price/symbols/getAll`.
Manifest lưu URL, thời điểm tải và SHA-256 từng phản hồi; raw chỉ lưu local.

Chọn 100 mã có trung vị giá trị khớp lệnh cao nhất trong tháng 12/2023, tối
thiểu 20 quan sát; cố định danh sách trước kỳ kiểm thử. Không lọc theo lợi
nhuận tương lai; giữ cả mã sau đó rời phạm vi HOSE/HNX. Đây là một tập 100 mã,
không phải toàn bộ thị trường. Lịch sử từ 04/01/2022 dùng làm warmup.

Tín hiệu dùng OHLC điều chỉnh; khớp lệnh dùng giá raw VND, biên giá do nguồn
cung cấp và phiên kế tiếp. Phí mua/bán mỗi chiều 0,15%, thuế bán 0,10%,
slippage 0,10% mỗi chiều; giữ tối đa 30 phiên, thanh khoản tối thiểu 5 tỷ VND.
Quy tắc nghiên cứu: lô 100, rủi ro 0,5% NAV/lệnh, tối đa 5 vị thế và 2 lệnh
mua/ngày; giới hạn mã/ngành/tổng đầu tư 20%/35%/80%, dự trữ tiền 10%.
Quy tắc thanh toán và tick vẫn là giả định nghiên cứu, chưa nghiệm thu broker.

## Giới hạn ảnh hưởng kết quả

- Có 24 quan sát mã–phiên thiếu/không hợp lệ trong kỳ còn đủ điều kiện.
  Không tự điền giá hoặc khối lượng. Toàn lịch sử loại 475 bản ghi: 464
  ngoài phạm vi sàn, 11 OHLC không hợp lệ. Báo cáo JSON giữ chi tiết từng dòng.
- Không có thay đổi hệ số điều chỉnh lớn hơn 0,3% mà thiếu loại sự kiện
  tương ứng. Bốn sự kiện chưa xác minh thời điểm đều trước kỳ test;
  sự kiện lỗi trong kỳ test sẽ chặn chạy.
- Ngày cổ phiếu thưởng về tài khoản chưa xác minh hết: phần không xác định
  bị khóa đến cuối kỳ. Lô lẻ chưa có mô hình khớp riêng; vị thế dư vẫn chiếm
  giới hạn số vị thế, làm giảm khả năng vào lệnh tiếp theo.
- Chưa mô hình hóa thuế khi bán cổ phiếu thưởng; làm tròn xuống phần cổ
  phiếu lẻ. Cổ tức tiền dùng giả định khấu trừ 5%; quyền mua không thực hiện,
  giá trị quyền bằng 0. Kết quả chưa phải lợi nhuận sau mọi loại chi phí.
- Nguồn public chưa được chứng nhận bởi sở; thiếu kho phiên bản dữ liệu và
  phân ngành lịch sử tại từng thời điểm. Không bảo đảm bao phủ mọi mã hủy
  niêm yết. Khớp tại mở cửa và giới hạn khối lượng là mô phỏng với dữ liệu ngày.

Vì vậy phân loại là `REAL_RESEARCH_PROVISIONAL`. Giao diện hiện tại vẫn dùng
DEMO; lượt chạy thật này là công cụ offline độc lập, không đổi nhãn dữ liệu DB.

## Tái lập và kiểm thử

Chạy từ thư mục gốc repo trong PowerShell, với môi trường Python đã cài:

```powershell
node infra/scripts/fetch-vndirect-research.mjs
$env:PYTHONPATH='apps/quant-worker'
& apps/quant-worker/.venv/Scripts/python.exe -m quant.vndirect_research .runtime/vndirect-s1-20261016
```

Downloader giới hạn một request/4 giây, kiểm tra pagination, retry có giới
hạn khi 429/503; tái sử dụng snapshot local. Đầu ra mỗi lần chạy ở thư mục mới
`.runtime/vndirect-s1-20261016/runs/`; `latest-run.txt` trỏ tới lượt gần nhất.
`summary.json` chứa chất lượng, chỉ số, tham số, hash; `result.json` chứa lệnh,
giao dịch và NAV theo ngày. Dữ liệu và đầu ra chi tiết không đưa lên Git.

31/31 kiểm thử Python đạt trên WSL native PostgreSQL, bao gồm tích hợp DB;
Ruff và mypy đạt. Các ca mới kiểm tra raw/adjusted, cổ phiếu thưởng khóa bán,
chống trùng sự kiện và phân bổ cổ tức/đối soát NAV. Hai lần chạy đầy đủ liên
tiếp cho cùng hash kết quả. Mỗi phiên đều đối soát NAV = tiền + phải thu +
giá trị cổ phiếu, không có số dư tiền âm.

- Dataset SHA-256: `aadd9e04f75f9d5e068017aecb3df4614d25e475bde5afea6d9335012a533d85`
- Engine SHA-256: `45515ff7cb9cf8fe28de7bc8231a3b326aa973fc938f350118e7e535ee981ae2`
- Reproducibility SHA-256: `c1148fbf70f00a47cfea643f09824411390f749bece87ba8181ff95103582464`
