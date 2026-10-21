# Phân tích lệnh thua và thử cải thiện S1

Kết luận: biến thể `hold15` cải thiện kết quả trên giai đoạn đã xem
04/09/2024–16/10/2026: win rate **48,33%**, NAV **+7,64%**, drawdown **−5,59%**.
Tuy nhiên nó không vượt bản gốc về lợi nhuận trên validation sớm và khi tăng
slippage. **Giữ S1 hiện tại làm mặc định; hold15 là ứng viên nghiên cứu.**

## Các lệnh thua hiện tại

45 vị thế đóng hết: 17 thắng, 28 thua. Phần bán của các vị thế còn mở không
được đưa vào mẫu này. Tổng PnL 28 lệnh thua −5.105.982,50 VND; 17 lệnh thắng
+7.369.525 VND. Đây là PnL các vị thế đã đóng, khác lợi nhuận NAV toàn danh mục.

- 21/28 lệnh thua (75%) chạm STOP; 7/28 thoát dưới EMA50.
- 8 lệnh thua giữ tối đa 5 phiên; 9 lệnh giữ 6–15 phiên; 11 lệnh trên 15 phiên.
  Rút thời hạn giữ không thể giải quyết mọi lệnh thua nhanh.
- Khi vào lệnh ở RISK_ON: 13 thắng/30 vị thế = 43,33%; NEUTRAL: 4/15 = 26,67%.
  Đây là tương quan trên mẫu, không chứng minh bộ lọc RISK_ON sẽ tăng lợi nhuận.
- RSI trung bình nhóm thua 67,83, nhóm thắng 73,21. Không có bằng chứng đơn
  giản rằng loại tất cả RSI >70 sẽ cải thiện S1 momentum.
- Cả 17 lệnh thắng đều thoát theo thời hạn giữ. Thoát xu hướng nhanh hơn có
  thể cắt mất lệnh thắng; cần kiểm tra, không mặc định EMA20 tốt hơn EMA50.

| Lệnh thua lớn | Mua | Bán | PnL VND | Thoát |
| --- | --- | --- | ---: | --- |
| NVL | 05/05/2026 | 08/05/2026 | −283.605 | STOP |
| HUT | 20/08/2025 | 25/08/2025 | −277.285 | STOP |
| DIG | 26/09/2025 | 02/10/2025 | −274.497,50 | STOP |
| VND | 11/08/2025 | 25/08/2025 | −268.970 | STOP |
| PVD | 15/01/2026 | 26/01/2026 | −266.162,50 | STOP |

## Thiết kế thử nghiệm

Cùng snapshot 100 mã, vốn 50 triệu cho mỗi lượt, phí mua/bán 0,15% mỗi chiều,
thuế bán 0,10%, slippage cơ sở 0,10% mỗi chiều, cùng giới hạn danh mục và stop.
Chỉ thử năm biến thể bên cạnh baseline, không dò hàng trăm ngưỡng:

1. `risk_on`: chỉ nhận tín hiệu S1 khi thị trường RISK_ON.
2. `confirmed`: thêm close tăng so với phiên trước, nến raw tăng, close > EMA20.
3. `ema20_exit`: đổi ngưỡng thoát xu hướng từ EMA50 sang EMA20.
4. `hold15`: giữ nguyên điều kiện vào/stop/EMA50, giảm maxHold từ 30 xuống 15.
5. `risk_on_ema20`: kết hợp bộ lọc RISK_ON với thoát EMA20.

Các bộ lọc áp dụng sau xếp hạng S1 gốc, không xếp hạng lại những mã còn lại.
Tín hiệu và EMA thoát chỉ dùng dữ liệu phiên trước; khớp phiên sau. Không thêm
take-profit hoặc thay risk budget để làm đẹp win rate. Bản mặc định không đổi.

**Quy ước hiện tại của engine:** time exit khi `idx - bought > maxHold`.
Do đó config 30/15 thường bán sau khoảng cách 31/16 phiên kể từ phiên mua,
khi đủ điều kiện khớp và chứng khoán khả dụng. Nghiên cứu giữ nguyên quy ước
này để so sánh với baseline; không sửa ngầm hành vi engine. Cổ phiếu thưởng
bị khóa/lô lẻ có thể tồn tại lâu hơn thời hạn đó.

Validation sớm: **15/02/2024–28/06/2024**; bỏ khoảng tháng 7–8 trước giai đoạn
so sánh **04/09/2024–16/10/2026**. Mỗi lượt bắt đầu lại với vốn 50 triệu.
Chọn bằng validation: ít nhất 8 vị thế đóng hết, win rate cao hơn baseline,
lợi nhuận không thấp hơn và drawdown không xấu hơn; nếu nhiều ứng viên thì
chọn lợi nhuận cao nhất, hòa chọn tên. Nếu không đạt, giữ baseline. Protocol
và quyết định chọn được ghi ra file trước khi chạy so sánh giai đoạn sau.

**Không gọi giai đoạn sau là holdout chưa thấy:** kết quả và lệnh thua của
giai đoạn này đã được xem, đồng thời ảnh hưởng việc hình thành giả thuyết.
Việc tách validation giúp hạn chế chọn tùy ý nhưng không xóa thiên lệch đó.

## Kết quả so sánh trên 04/09/2024–16/10/2026

| Biến thể | Thắng / đóng hết | Win rate | Lợi nhuận NAV | Drawdown lớn nhất |
| --- | ---: | ---: | ---: | ---: |
| S1 hiện tại | 17/45 | 37,78% | +5,83% | −6,62% |
| Chỉ RISK_ON | 14/45 | 31,11% | −2,44% | −8,75% |
| Xác nhận nến tăng + EMA20 | 15/46 | 32,61% | −1,20% | −6,16% |
| Thoát EMA20 | 18/61 | 29,51% | +2,46% | −8,13% |
| **maxHold 15** | **29/60** | **48,33%** | **+7,64%** | **−5,59%** |
| RISK_ON + thoát EMA20 | 15/52 | 28,85% | +2,44% | −7,16% |

Hold15 tăng win rate **10,56 điểm phần trăm**, lợi nhuận **1,81 điểm phần
trăm**, giảm độ sâu drawdown **1,03 điểm phần trăm**, đồng thời tăng 45 lên
60 vị thế đóng hết. Đây là danh mục chạy lại, không phải chọn bỏ các lệnh
thua của baseline: thời điểm thoát làm thay đổi tiền khả dụng và lệnh tiếp theo.

| Phần năm trong kỳ | S1 hiện tại | hold15 |
| --- | ---: | ---: |
| 2024 từ 04/09 | −0,27% | +0,86% |
| 2025 | +9,42% | +9,62% |
| 2026 đến 16/10 | −3,01% | −2,64% |

## Vì sao chưa thay mặc định

Trên validation sớm, baseline đạt **40% (6/15), +3,23%, drawdown −4,47%**.
Hold15 đạt **45,83% (11/24), +1,27%, drawdown −4,35%**: win rate cao hơn nhưng
lợi nhuận thấp hơn. Các ứng viên khác cũng không đạt tất cả tiêu chí, nên
quyết định chọn bằng validation là **baseline**. Công bố hold15 ở trên vì nó
đáng nghiên cứu trên mẫu đã thấy, không coi đây là cấu hình được validation chọn.

Khi tăng slippage lên **0,30% mỗi chiều**, giữ nguyên các phí khác:

| Cấu hình | Thắng / đóng hết | Win rate | Lợi nhuận | Drawdown |
| --- | ---: | ---: | ---: | ---: |
| S1 hiện tại | 18/47 | 38,30% | +3,59% | −5,26% |
| hold15 | 31/67 | 46,27% | +2,06% | −5,98% |

Lợi thế lợi nhuận của hold15 không còn. Số lệnh thay đổi vì slippage ảnh hưởng
khả năng khớp, làm tròn lô, tiền khả dụng và đường đi danh mục; đây không phải
phép trừ chi phí cố định trên cùng một tập lệnh. Toàn bộ sáu cấu hình đều được
chạy stress và lưu, không chỉ công bố cấu hình thắng khi tăng chi phí.

Kết quả vẫn chịu giới hạn của [dữ liệu thật sơ bộ](REAL_S1_BACKTEST_2026-10-21.md):
24 quan sát mã–phiên thiếu, dữ liệu ngành không lịch sử, thiếu xác minh ngày
về và thuế cổ phiếu thưởng, lô lẻ chưa khớp, mô hình thực thi từ dữ liệu ngày.
Baseline cuối kỳ giữ LPB/SHB/MSB; hold15 giữ LPB/CEO/MSB. NAV bao gồm phần
còn giữ; win rate chỉ tính vị thế đóng hết. Không tự kích hoạt chiến lược mới.

## Kiểm thử, bằng chứng và tái lập

- 32/32 kiểm thử Python đạt trên WSL native PostgreSQL, Ruff/mypy đạt.
- Thêm kiểm thử thoát EMA20 dùng phiên trước, không thay hành vi mặc định,
  dữ liệu tương lai không thay giao dịch đã đóng.
- Hai lần chạy khớp hash cho cả 12 lượt validation/comparison.
- Toàn bộ ledger baseline khớp bản S1 đã công bố, không chỉ ba chỉ số headline.
- Mỗi lượt đối soát NAV từng phiên và tiền không âm.
- [Bằng chứng tổng hợp JSON](verification/s1-experiments.json) chứa mọi cấu
  hình, chỉ số, cảnh báo, dataset/engine/result hash và quy tắc chọn.
- Ledger chi tiết và phân tích từng lệnh lưu local tại thư mục được chỉ bởi
  `.runtime/vndirect-s1-20261016/latest-s1-study.txt`; không đưa raw thị trường lên Git.

```powershell
$env:PYTHONPATH='apps/quant-worker'
& apps/quant-worker/.venv/Scripts/python.exe -m quant.s1_experiments .runtime/vndirect-s1-20261016
```

Lượt chạy tạo thư mục mới, không ghi đè báo cáo trước. Giao diện vẫn DEMO;
nghiên cứu này chạy offline, không đổi cấu hình scanner/backtest mặc định.
