# S1: chốt lời và dời stop về hòa vốn

**Chốt lời 1R tăng win rate nhưng giảm lợi nhuận và không chịu được chi phí
cao; chưa có biến thể đạt tiêu chí trên cả validation lẫn stress. Giữ S1 gốc
làm mặc định.** Chạy 6 biến thể mới cùng 2 đối chứng ở 4 kịch bản, tổng 32
lượt; lưu toàn bộ kết quả, không chỉ các cấu hình có win rate cao.

## Quy tắc thực thi

- `R` là giá khớp mua thực tế trừ stop ban đầu, cố định tại thời điểm vào lệnh.
- `tp1` / `tp2`: chốt phần có thể bán khi giá chạm entry + 1R / 2R. Mô phỏng
  lệnh thị trường kích hoạt tại ngưỡng, có slippage, thuế, phí và bước giá;
  không giả định lệnh limit chắc chắn khớp đúng ngưỡng.
- `be1`: sau khi **giá đóng cửa phiên trước >= entry + 1R**, nâng stop cho
  phiên sau lên giá hòa vốn ước tính của phần còn giữ: chi phí còn lại trừ
  thu nhập cổ tức đã phân bổ, chia số cổ phiếu và điều chỉnh phí bán, thuế,
  slippage. Không kích hoạt từ high cuối ngày để bán ngược về trước trong
  cùng phiên. Stop không bị hạ khi giá lùi lại.
- BE không bảo đảm PnL bằng 0: gap, bước giá, hạn chế khớp và thiếu mô hình
  đầy đủ thuế cổ phiếu thưởng có thể tạo lỗ. Không gán lỗ nhỏ thành hòa để
  nâng win rate; mọi PnL âm vẫn là thua.
- Khi cả stop và target bị chạm trong cùng bar ngày, ưu tiên stop vì chưa
  biết thứ tự intraday. Thoát EMA50/thời hạn đã được quyết định cũng ưu tiên
  trước target. Đây là giả định thận trọng, không phải dữ liệu tick.
- Chỉ bán chứng khoán đã khả dụng theo quy tắc thanh toán, giới hạn khối
  lượng và lô hiện tại. Corporate actions điều chỉnh target/trigger/stop.
  Không tự bán cổ phiếu thưởng chưa về hoặc giả lập khớp lô lẻ.

Các biến thể kết hợp gồm `tp1_be1`, `tp2_be1`, `tp2_be1_hold15`. Các cấu hình
khác giữ maxHold 30. S1 gốc và hold15 không bật target/BE; không thay điều
kiện vào, risk budget hay xếp hạng. Quy ước cũ `held > maxHold` giữ nguyên,
nên nhãn 15/30 thường bán theo thời hạn ở khoảng cách 16/31 phiên.

## Dữ liệu và lựa chọn

Cùng snapshot 100 mã thật, vốn mỗi lượt 50 triệu VND; phí mua/bán 0,15% mỗi
chiều, thuế bán 0,10%. Validation 15/02/2024–28/06/2024; so sánh lịch sử
04/09/2024–16/10/2026. Mỗi giai đoạn chạy slippage 0,10% và 0,30% mỗi chiều.

Ghi protocol trước khi chạy. Tiêu chí validation ở cả hai mức chi phí: ít
nhất 8 vị thế đóng hết, win rate cao hơn bản gốc và không thấp hơn hold15,
lợi nhuận/drawdown không kém cả hai đối chứng. Nếu nhiều ứng viên đạt, ưu
tiên win rate tệ nhất giữa hai mức chi phí cao nhất, rồi lợi nhuận tệ nhất,
rồi tên. Quyết định chọn được ghi trước khi chạy giai đoạn sau. Không ứng
viên nào đạt nên giữ baseline; không nới tiêu chí sau khi thấy kết quả.

Đây là `EXPLORATORY_REUSED_VALIDATION_AND_TEST`: cả validation và giai đoạn
sau đã được xem nhiều lần. Sau ba vòng đã thử tổng 18 biến thể mới; chưa
có kiểm chứng trên một giai đoạn chưa thấy hoặc forward paper trading.

## Nhận xét chính

Trên 2024–2026 với slippage cơ sở, TP1 có **40/73 lệnh thắng = 54,79%**, nhưng
lợi nhuận chỉ **+2,56%**, thấp hơn bản gốc **+5,83%** và hold15 **+7,64%**.
Khi slippage 0,30%, TP1 còn **35/71 = 49,30%**, lợi nhuận **−1,51%**.
Validation TP1 lỗ ở cả hai mức chi phí dù win rate **52,00% / 54,17%**.

Giải thích từ các lần bán trên giai đoạn cơ sở: TP1 giảm PnL trung bình lần
bán có lãi từ khoảng 420 nghìn VND ở baseline xuống 170 nghìn VND, trong
khi lỗ trung bình vẫn khoảng 181 nghìn VND. Số giao dịch và tổng phí tăng.
Các chỉ số trung bình này tính theo **lần bán**, khác mẫu vị thế đóng hết
dùng cho headline win rate. Không nên tăng win rate bằng cách cắt ngắn
phần lãi trong khi mức lỗ vẫn lớn.

BE riêng đạt **25,00% / +1,32% / drawdown −8,15%** ở giai đoạn sau, chi phí
cơ sở. Có 7 lần bán lỗ dưới 20.000 VND; lỗ nhỏ vẫn được tính đúng là thua.
Khi slippage cao, BE đạt +4,21% nhưng win rate chỉ 27,59%; validation cơ sở
cũng chỉ 21,05%. Cơ chế này chưa giúp mục tiêu tăng win rate.

TP2 + BE + hold15 giữ lợi nhuận giai đoạn sau khá ổn giữa hai mức chi phí
(+3,79% / +3,73%), nhưng validation cơ sở **−1,56%**, win rate **33,33%**,
nên cũng không đủ điều kiện chọn.

TP1 và TP1+BE cho cùng kết quả trên cả hai mức chi phí giai đoạn sau: target
1R thường đã kích hoạt trước khi close +1R có thể kích hoạt BE cho phiên
sau. Hai cấu hình này không phải hai bằng chứng độc lập về hiệu quả.

Slippage cao làm thay đổi khả năng khớp, số cổ phiếu và dòng tiền, nên chạy
lại có thể đổi tập giao dịch. Không xem stress là phép trừ một khoản phí
cố định trên cùng ledger, hoặc suy diễn chi phí cao tạo lợi thế.

## Toàn bộ kết quả

Win rate tính theo vị thế đóng hết; NAV gồm phần còn giữ. Mỗi bảng ghi
slippage mỗi chiều. Kết quả dưới đây được sinh trực tiếp từ summary JSON.

### validation_base

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 6/15 | 40.00% | +3.23% | -4.47% |
| hold15 | 11/24 | 45.83% | +1.27% | -4.35% |
| tp1 | 13/25 | 52.00% | -2.38% | -6.49% |
| tp2 | 7/20 | 35.00% | -2.68% | -6.75% |
| be1 | 4/19 | 21.05% | +2.10% | -4.63% |
| tp1_be1 | 13/26 | 50.00% | -2.43% | -6.54% |
| tp2_be1 | 5/22 | 22.73% | -1.49% | -6.10% |
| tp2_be1_hold15 | 9/27 | 33.33% | -1.56% | -6.05% |

### validation_stress

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 6/15 | 40.00% | +0.74% | -5.19% |
| hold15 | 8/20 | 40.00% | +0.26% | -5.23% |
| tp1 | 13/24 | 54.17% | -1.06% | -5.78% |
| tp2 | 7/19 | 36.84% | -1.73% | -5.78% |
| be1 | 4/16 | 25.00% | +1.53% | -4.80% |
| tp1_be1 | 13/24 | 54.17% | -1.06% | -5.78% |
| tp2_be1 | 5/20 | 25.00% | -0.39% | -4.67% |
| tp2_be1_hold15 | 9/25 | 36.00% | +0.24% | -4.70% |

### comparison_base

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 17/45 | 37.78% | +5.83% | -6.62% |
| hold15 | 29/60 | 48.33% | +7.64% | -5.59% |
| tp1 | 40/73 | 54.79% | +2.56% | -4.44% |
| tp2 | 20/55 | 36.36% | +0.40% | -6.75% |
| be1 | 13/52 | 25.00% | +1.32% | -8.15% |
| tp1_be1 | 40/73 | 54.79% | +2.56% | -4.44% |
| tp2_be1 | 17/61 | 27.87% | -1.62% | -8.12% |
| tp2_be1_hold15 | 33/71 | 46.48% | +3.79% | -6.36% |

### comparison_stress

| Config | Wins/closed | Win rate | Return | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| baseline | 18/47 | 38.30% | +3.59% | -5.26% |
| hold15 | 31/67 | 46.27% | +2.06% | -5.98% |
| tp1 | 35/71 | 49.30% | -1.51% | -6.80% |
| tp2 | 20/53 | 37.74% | +1.18% | -5.40% |
| be1 | 16/58 | 27.59% | +4.21% | -5.66% |
| tp1_be1 | 35/71 | 49.30% | -1.51% | -6.80% |
| tp2_be1 | 16/59 | 27.12% | -2.97% | -8.07% |
| tp2_be1_hold15 | 31/69 | 44.93% | +3.73% | -5.03% |


## Kiểm thử và bằng chứng

36/36 kiểm thử Python đạt trên WSL native PostgreSQL, Ruff/mypy đạt. Kiểm
thử mới bao gồm target sau thanh toán, ưu tiên stop khi cùng bar chạm cả
hai ngưỡng, BE từ close phiên trước thay vì high, gap có thể gây lỗ, và
split giữ đúng giá trị/PnL. Không đổi kết quả baseline/hold15 đã công bố.

32 lượt chạy được lặp lại để đối chiếu hash; cả 8 ledger đối chứng khớp
nghiên cứu trước. Mỗi lượt đối soát NAV và tiền không âm. Giao diện vẫn
DEMO, các tùy chọn này chỉ phục vụ nghiên cứu offline, không bật mặc định.

[JSON tổng hợp](verification/s1-profit.json) lưu cấu hình, chỉ số, hash và
cảnh báo. Raw/ledger ở thư mục local do
`.runtime/vndirect-s1-20261016/latest-s1-profit.txt` trỏ tới, không đưa lên Git.
Các giới hạn dữ liệu public, 24 quan sát mã–phiên thiếu, phân ngành lịch sử,
cổ phiếu thưởng/lô lẻ và thuế vẫn như [báo cáo dữ liệu](REAL_S1_BACKTEST_2026-10-21.md).

```powershell
$env:PYTHONPATH='apps/quant-worker'
& apps/quant-worker/.venv/Scripts/python.exe -m quant.s1_robustness .runtime/vndirect-s1-20261016 --profit
```
