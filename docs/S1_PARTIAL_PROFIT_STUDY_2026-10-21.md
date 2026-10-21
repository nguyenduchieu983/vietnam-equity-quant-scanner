# S1: chốt một phần tại 1R, trailing phần còn lại

Ứng viên nổi bật trên giai đoạn đã xem 2024–2026 là **chốt một phần tại 1R,
trailing 2 ATR, maxHold 15**: win rate **50,79%**, lợi nhuận **+6,30%**, drawdown
**−4,91%** ở slippage 0,10%; khi slippage 0,30%: **50,82%, +6,74%, −3,40%**.
Tuy nhiên validation yếu hơn đối chứng nên **chưa thay S1 mặc định**.

## Cơ chế và giới hạn lô

- Giữ nguyên tín hiệu vào, vốn 50 triệu, risk budget và sizing. R = giá khớp
  mua thực tế trừ stop ban đầu.
- Tại 1R, dự kiến bán 50% số lượng vào lệnh, làm tròn xuống lô 100, để lại
  tối thiểu 100 cổ phiếu. Ví dụ 200 bán 100, 300 bán 100, 500 bán 200.
- Nếu chỉ mua 100 cổ phiếu, không giả lập bán 50 cổ phiếu: sau khi chạm 1R
  trong một phiên đủ điều kiện, giữ toàn bộ và kích hoạt trailing từ phiên
  kế tiếp. **Đây là mô hình kết hợp chốt một phần và trailing toàn vị thế
  nhỏ**, không phải mọi giao dịch đều được chia đôi.
- Trailing chỉ bắt đầu từ phiên sau lần khớp chốt một phần đầu tiên. Stop
  mới = max(stop cũ, close phiên trước − 2 hoặc 3 ATR14), đổi sang giá raw;
  không dùng high của phiên đang khớp để dời stop trong chính phiên đó.
- Khối lượng chốt đã lên kế hoạch được lưu cố định, trừ dần khi khớp; không
  tiếp tục bán nửa phần còn lại mỗi lần chạm 1R. Nếu bị giới hạn khối lượng,
  phần kế hoạch chưa bán được tiếp tục xét ở phiên sau.
- Vẫn giữ thoát dưới EMA50, stop cũ và maxHold; không để phần còn lại chạy
  vô thời hạn. Quy ước cũ `held > maxHold` giữ nguyên, nên nhãn 15/30 thường
  tương ứng khoảng cách 16/31 phiên nếu không bị hạn chế khớp.
- Stop được ưu tiên khi một bar chạm cả stop lẫn target. Chỉ bán lượng khả
  dụng; tiền bán về theo settlement hiện tại. Split/bonus điều chỉnh giá và
  kế hoạch số lượng, không tự mở khóa cổ phiếu thưởng. Phí, thuế và giá vốn
  được phân bổ theo lượng bán, không tính lặp.
- Win rate gộp PnL các lần bán của cùng mã/ngày vào và chỉ tính khi đóng hết.
  Bán nửa có lãi nhưng còn giữ nửa kia không được ghi nhận là một lệnh thắng
  hoàn chỉnh. NAV vẫn tính phần giữ và các khoản phải thu.

## Dữ liệu và chọn cấu hình

Cùng snapshot 100 mã thật. Validation **15/02/2024–28/06/2024**, so sánh
**04/09/2024–16/10/2026**. Phí mua/bán 0,15% mỗi chiều, thuế bán 0,10%,
slippage 0,10% hoặc 0,30% mỗi chiều. Vốn mỗi lượt khởi đầu lại 50 triệu.

Thử 4 biến thể: trailing 2/3 ATR kết hợp maxHold 15/30, cùng 2 đối chứng
baseline/hold15, tổng **24 kịch bản**. Protocol được ghi trước khi chạy.
Tiêu chí giữ nguyên vòng trước: cả hai mức chi phí validation phải có ít
nhất 8 vị thế đóng hết, win rate cao hơn baseline và không thấp hơn hold15,
lợi nhuận/drawdown không kém cả hai. Không đạt thì giữ baseline; quyết định
chọn được lưu trước khi chạy giai đoạn sau. Không biến thể nào đạt.

Đây là nghiên cứu dùng lại validation và lịch sử đã thấy. Đến vòng này đã
thử tổng 22 biến thể mới; kết quả đẹp trên lịch sử không phải kiểm định trên
mẫu chưa thấy, và không tự động kích hoạt chiến lược mới.

## Khả năng áp dụng thực tế của partial + 2 ATR + hold15

| Kịch bản | Vị thế có bán một phần | Chạm 1R nhưng phải giữ toàn bộ do lô nhỏ |
| --- | ---: | ---: |
| Validation, 0,10% | 1 | 11 |
| Validation, 0,30% | 1 | 9 |
| 2024–2026, 0,10% | 11 | 17 |
| 2024–2026, 0,30% | 9 | 21 |

Đếm trên tất cả vị thế của lượt chạy, có thể gồm vị thế còn mở, không dùng
làm mẫu số win rate. Với vốn/risk budget hiện tại, nhiều lệnh chỉ 100 cổ
phiếu. Vì vậy không thể quy toàn bộ thay đổi hiệu suất cho việc chốt 50%:
một phần đến từ trailing toàn vị thế sau 1R và đường đi danh mục mới.

Trên validation, ứng viên 2 ATR/15 chỉ đạt **+0,41%, drawdown −5,14%** ở
chi phí cơ sở, thấp hơn baseline **+3,23%, −4,47%** và hold15 **+1,27%, −4,35%**.
Ở slippage cao, ứng viên chỉ **+0,23%, win rate 38,10%**. Đây là lý do chưa
đủ bằng chứng thay mặc định dù giai đoạn sau đạt trên 50% win rate.

Slippage cao có thể cho lợi nhuận cao hơn do thay đổi số lượng/lệnh khớp,
tiền khả dụng và các giao dịch tiếp theo. Không hiểu đây là cùng ledger bị
trừ thêm chi phí, hay khẳng định chi phí cao tạo lợi thế.

## Toàn bộ kết quả

### validation_base

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 6/15 | 40.00% | +3.23% | -4.47% |
| hold15 | 11/24 | 45.83% | +1.27% | -4.35% |
| partial1_trail2_hold30 | 8/19 | 42.11% | -0.88% | -6.75% |
| partial1_trail2_hold15 | 11/24 | 45.83% | +0.41% | -5.14% |
| partial1_trail3_hold30 | 5/16 | 31.25% | +0.38% | -5.44% |
| partial1_trail3_hold15 | 11/24 | 45.83% | +1.71% | -3.93% |

### validation_stress

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 6/15 | 40.00% | +0.74% | -5.19% |
| hold15 | 8/20 | 40.00% | +0.26% | -5.23% |
| partial1_trail2_hold30 | 8/17 | 47.06% | +0.96% | -4.88% |
| partial1_trail2_hold15 | 8/21 | 38.10% | +0.23% | -5.27% |
| partial1_trail3_hold30 | 5/16 | 31.25% | -1.83% | -6.27% |
| partial1_trail3_hold15 | 8/20 | 40.00% | +0.03% | -5.48% |

### comparison_base

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 17/45 | 37.78% | +5.83% | -6.62% |
| hold15 | 29/60 | 48.33% | +7.64% | -5.59% |
| partial1_trail2_hold30 | 24/57 | 42.11% | +3.14% | -6.38% |
| partial1_trail2_hold15 | 32/63 | 50.79% | +6.30% | -4.91% |
| partial1_trail3_hold30 | 18/51 | 35.29% | +4.06% | -5.64% |
| partial1_trail3_hold15 | 29/60 | 48.33% | +6.27% | -5.57% |

### comparison_stress

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 18/47 | 38.30% | +3.59% | -5.26% |
| hold15 | 31/67 | 46.27% | +2.06% | -5.98% |
| partial1_trail2_hold30 | 28/63 | 44.44% | +3.96% | -6.25% |
| partial1_trail2_hold15 | 31/61 | 50.82% | +6.74% | -3.40% |
| partial1_trail3_hold30 | 18/55 | 32.73% | -1.27% | -6.55% |
| partial1_trail3_hold15 | 32/67 | 47.76% | +2.94% | -4.84% |


## Kiểm tra và tái lập

39/39 kiểm thử Python đạt trên WSL native PostgreSQL; Ruff/mypy đạt. Các ca
mới kiểm tra chia lệnh đúng lô, không trailing trước khi chốt, không chốt
lặp nửa phần còn lại, bảo toàn ngân sách chốt qua volume cap và split,
phân bổ giá vốn/phí đúng, NAV khớp và không tính partial còn mở là lệnh thắng.

24 lượt chạy lặp lại cùng phiên bản engine khớp hash; 8 ledger đối chứng
baseline/hold15 khớp nguyên vẹn vòng trước. Mỗi lượt đối soát NAV, tiền không
âm. Raw thị trường và ledger vẫn giữ local, giao diện vẫn DEMO.

[JSON đầy đủ](verification/s1-partial.json) lưu tham số, thống kê partial,
số lệnh, hash và cảnh báo. Giới hạn dữ liệu public, 24 quan sát mã–phiên
thiếu, thuế/khả dụng cổ phiếu thưởng và mô phỏng từ OHLC ngày vẫn áp dụng.

```powershell
$env:PYTHONPATH='apps/quant-worker'
& apps/quant-worker/.venv/Scripts/python.exe -m quant.s1_robustness .runtime/vndirect-s1-20261016 --partial
```

Đầu ra nằm ở thư mục mới mỗi lần chạy, được chỉ bởi
`.runtime/vndirect-s1-20261016/latest-s1-partial.txt`.
