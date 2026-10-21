# So sánh S1–S4 trên cùng dữ liệu thật

Chạy ngày 21/10/2026. Cùng snapshot 100 mã HOSE/HNX, khoảng 04/09/2024 đến
16/10/2026 (528 phiên), vốn riêng 50 triệu VND cho mỗi cấu hình; cùng phí,
slippage, giới hạn thanh khoản và rủi ro như [lượt S1](REAL_S1_BACKTEST_2026-10-21.md).
Không chia vốn giữa các chiến lược, không tối ưu tham số theo kết quả.

| Chiến lược | Giữ tối đa (phiên) | Đóng hết | Thắng / thua | Win rate | Lợi nhuận NAV | Drawdown lớn nhất |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 30 | 45 | 17 / 28 | 37,78% | +5,83% | −6,62% |
| S2 | 30 | 69 | 18 / 51 | 26,09% | −6,78% | −8,97% |
| S3 | 30 | 101 | 22 / 79 | 21,78% | +1,24% | −13,60% |
| S4 | 5 | 15 | 7 / 8 | 46,67% | +0,79% | −0,72% |
| S4 | 10 | 15 | 6 / 9 | 40,00% | +0,30% | −1,05% |

S4 dùng đúng hai thời hạn 5/10 phiên theo spec; vẫn là chiến lược EXPERIMENTAL.
Lượt thăm dò S4 30 phiên không hợp lệ theo spec, bị loại khỏi bảng. Runner
hiện chặn cấu hình đó. S1–S3 giữ cấu hình 30 phiên; không thay logic chiến lược.

S1 đạt lợi nhuận cao nhất nhóm trong mẫu này. S4-5 có win rate cao nhất và
drawdown nhỏ nhất nhưng chỉ 15 vị thế đóng hết, chưa đủ để kết luận ổn định.
S3 giao dịch nhiều nhất, win rate thấp nhất và drawdown lớn nhất. VNINDEX giá
cùng kỳ tăng 34,18%, cao hơn cả năm cấu hình; benchmark không gồm cổ tức.

Win rate = vị thế có tổng PnL dương / vị thế đã đóng hết, gộp các lần bán
cùng mã và ngày vào. Không tính phần bán của vị thế còn mở vào mẫu này.
Lợi nhuận NAV bao gồm lãi/lỗ chưa thực hiện, cổ tức và phần còn giữ; vì vậy
win rate thấp không đồng nghĩa lợi nhuận NAV âm. Số lần bán lần lượt là
48, 73, 102 cho S1/S2/S3; đây là mẫu khác với số vị thế đóng hết.

## Giới hạn và kiểm tra

Đây là **REAL_RESEARCH_PROVISIONAL**, chịu toàn bộ giới hạn trong báo cáo S1:
24 quan sát mã–phiên thiếu, dữ liệu public, phân ngành hiện tại, giả định phí/
thuế và thanh toán, chưa xử lý đầy đủ ngày về/thuế cổ phiếu thưởng và lô lẻ.
Phần còn giữ có thể chiếm giới hạn vị thế và giảm số lệnh tiếp theo. S2/S3
còn phát sinh cảnh báo đánh dấu giá cũ khi thiếu bar; kết quả không phải mô
phỏng giao dịch đã được broker xác nhận. Giao diện vẫn DEMO.

Đã xác nhận cùng dataset hash, thời gian và cấu hình chung cho cả năm lượt.
S1 có reproducibility hash khớp chính xác kết quả đã công bố. Mọi lượt đều
đối soát NAV theo ngày và kiểm tra tiền không âm. Kiểm thử Windows: 30 ca
đạt, 1 ca tích hợp DB bỏ qua; Ruff/mypy đạt. Engine mô phỏng không thay đổi
trong lượt so sánh này. Chưa chạy lặp lại S2–S4 để kiểm tra tính tái lập.

Thông số đầy đủ, run ID, hash, cảnh báo và số liệu chưa làm tròn lưu trong
[bằng chứng JSON](verification/real-strategy-comparison.json). Raw thị trường
và ledger chi tiết ở `.runtime/vndirect-s1-20261016/runs/`, không đưa lên Git.

Chạy lại từ thư mục gốc repo, dùng snapshot đã tải:

```powershell
$env:PYTHONPATH='apps/quant-worker'
foreach ($s in @('S1','S2','S3')) {
  & apps/quant-worker/.venv/Scripts/python.exe -m quant.vndirect_research .runtime/vndirect-s1-20261016 --strategy $s
}
foreach ($h in @(5,10)) {
  & apps/quant-worker/.venv/Scripts/python.exe -m quant.vndirect_research .runtime/vndirect-s1-20261016 --strategy S4 --max-hold $h
}
```
