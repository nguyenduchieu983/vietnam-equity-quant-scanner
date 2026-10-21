# S1: tăng win rate và kiểm tra độ bền với chi phí

**Chưa tìm được biến thể mới đáp ứng đồng thời yêu cầu trên validation và
slippage cao. Giữ bản gốc làm mặc định.** Đã thử thêm 7 biến thể, đối chiếu
với baseline và hold15 trong 4 kịch bản; tổng cộng 36 lượt, chạy lặp lại đủ
36 lượt để kiểm tra tính tái lập. Không chọn cấu hình chỉ vì có lợi nhuận
đẹp trên giai đoạn so sánh đã xem trước đó.

## Dữ liệu và tiêu chí

Cùng snapshot 100 mã, vốn mỗi lượt 50 triệu VND, stop/risk budget/phí/thuế
như nghiên cứu trước. Validation: 15/02/2024–28/06/2024. Giai đoạn so sánh:
04/09/2024–16/10/2026. Mỗi giai đoạn chạy slippage 0,10% và 0,30% mỗi chiều.

Để tránh lựa chọn tùy ý sau khi xem số liệu, ghi protocol trước khi chạy:
ở **cả hai mức slippage trên validation**, ứng viên phải có ít nhất 8 vị thế
đóng hết, win rate cao hơn bản gốc và không thấp hơn hold15, lợi nhuận và
drawdown không kém **cả hai** đối chứng. Nếu nhiều ứng viên đạt, ưu tiên
win rate thấp nhất giữa hai mức chi phí cao nhất, sau đó lợi nhuận thấp nhất
cao nhất, rồi tên cấu hình. Nếu không đạt, giữ baseline. Giai đoạn sau dùng
cùng tiêu chí, ít nhất 30 vị thế đóng hết ở mỗi mức chi phí để xác nhận.

Đây là tiêu chí sàng lọc nghiêm ngặt của lượt nghiên cứu này, không phải
định nghĩa duy nhất của chiến lược tốt. **Không có ứng viên đạt ngay tại
validation**, kể cả nếu chỉ yêu cầu vượt baseline về ba chỉ số ở cả hai mức
chi phí. Quyết định giữ baseline được lưu trước khi chạy giai đoạn so sánh.

Validation và lịch sử 2024–2026 đều đã được xem trong các lượt trước: phân
loại `EXPLORATORY_REUSED_VALIDATION_AND_TEST`, không gọi là kiểm định ngoài
mẫu chưa thấy. Tổng hai vòng đã thử 12 biến thể mới; không xem kết quả tốt
nhất trong số nhiều lần thử là bằng chứng chắc chắn có lợi thế.

## Bảy biến thể mới

| Tên | Thay đổi so với S1 gốc |
| --- | --- |
| trail3 | Nâng stop theo close phiên trước trừ 3 ATR14; giữ maxHold 30 |
| trail2 | Tương tự, khoảng cách 2 ATR14 |
| trend200 | Chỉ vào nếu close > EMA50 > EMA200 |
| trend200_hold15 | Lọc EMA200 và maxHold 15 |
| volume1 | Khối lượng tín hiệu >= trung bình 20 phiên trước |
| extension2atr | Khoảng cách close−EMA20 không vượt 2 ATR14 |
| trail3_hold15 | Trailing 3 ATR kết hợp maxHold 15 |

Mọi bộ lọc áp dụng sau xếp hạng S1 gốc, không xếp hạng lại. Trailing chỉ nâng
stop bằng dữ liệu phiên trước, không hạ stop khi giá giảm; đổi đơn vị về giá
raw trước khớp. Stop được điều chỉnh tiếp khi có corporate action phiên hiện
tại. Không dùng đỉnh/đáy cuối ngày hiện tại để nâng stop cho chính ngày đó.
Trailing không bảo đảm bán có lãi vì gap, phí, giới hạn giá và thanh toán.

Quy ước maxHold giữ nguyên: bán khi khoảng cách phiên `> maxHold`, nên nhãn
15/30 thường tương ứng khoảng cách 16/31 phiên kể từ phiên mua nếu khớp được.
Lô lẻ/cổ phiếu thưởng bị khóa có thể còn tồn tại lâu hơn. Không đổi quy ước
ngầm giữa đối chứng và ứng viên.

## Đối chiếu bản gốc, hold15 và ứng viên trailing 3 ATR + hold15

Ứng viên dưới đây đáng theo dõi vì cải thiện mức chịu slippage trên giai đoạn
sau, **không phải ứng viên được validation chọn**.

| Giai đoạn / slippage mỗi chiều | Cấu hình | Thắng / đóng hết | Win rate | Lợi nhuận | Drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
| Validation / 0,10% | Gốc | 6/15 | 40,00% | +3,23% | −4,47% |
| Validation / 0,10% | hold15 | 11/24 | 45,83% | +1,27% | −4,35% |
| Validation / 0,10% | trail3_hold15 | 10/24 | 41,67% | +0,45% | −4,84% |
| Validation / 0,30% | Gốc | 6/15 | 40,00% | +0,74% | −5,19% |
| Validation / 0,30% | hold15 | 8/20 | 40,00% | +0,26% | −5,23% |
| Validation / 0,30% | trail3_hold15 | 8/20 | 40,00% | +0,43% | −5,09% |
| 2024–2026 / 0,10% | Gốc | 17/45 | 37,78% | +5,83% | −6,62% |
| 2024–2026 / 0,10% | hold15 | 29/60 | 48,33% | +7,64% | −5,59% |
| 2024–2026 / 0,10% | trail3_hold15 | 27/60 | 45,00% | +5,87% | −5,91% |
| 2024–2026 / 0,30% | Gốc | 18/47 | 38,30% | +3,59% | −5,26% |
| 2024–2026 / 0,30% | hold15 | 31/67 | 46,27% | +2,06% | −5,98% |
| 2024–2026 / 0,30% | trail3_hold15 | 31/66 | 46,97% | +4,44% | −3,91% |

Không nên chỉ nhìn dòng cuối: trên validation chi phí cơ sở, trailing mới
giảm lợi nhuận từ +3,23% xuống +0,45% và drawdown xấu hơn bản gốc. Trên
validation stress, win rate bằng bản gốc và lợi nhuận cũng thấp hơn.

## Kết quả tất cả biến thể trên giai đoạn 2024–2026

Mỗi ô ghi **win rate / lợi nhuận / drawdown**.

| Cấu hình | Slippage 0,10% | Slippage 0,30% |
| --- | --- | --- |
| Gốc | 37,78% / +5,83% / −6,62% | 38,30% / +3,59% / −5,26% |
| hold15 | 48,33% / +7,64% / −5,59% | 46,27% / +2,06% / −5,98% |
| trail3 | 35,29% / +5,54% / −4,77% | 35,85% / +2,40% / −5,44% |
| trail2 | 33,33% / +1,32% / −6,95% | 33,82% / +0,40% / −7,21% |
| trend200 | 33,33% / +6,79% / −8,54% | 36,54% / +9,53% / −5,31% |
| trend200_hold15 | 44,62% / +6,12% / −7,79% | 46,55% / +4,20% / −4,61% |
| volume1 | 33,96% / +0,91% / −7,73% | 39,22% / +4,67% / −8,70% |
| extension2atr | 38,18% / +8,46% / −7,21% | 39,62% / +11,45% / −4,48% |
| trail3_hold15 | 45,00% / +5,87% / −5,91% | 46,97% / +4,44% / −3,91% |

Extension2atr có lợi nhuận cao trên giai đoạn sau, nhưng validation cơ sở
**win rate 22,22%, lợi nhuận −2,72%**, nên không được chọn. Stop 2/3 ATR dùng
riêng cũng không cải thiện win rate. Bộ lọc EMA200 không đổi các giao dịch
validation trong snapshot này, nên không tạo thêm bằng chứng về khả năng cải thiện.

Slippage cao đôi khi cho lợi nhuận cao hơn: mô phỏng chạy lại toàn danh mục,
giá khớp khác làm thay đổi số cổ phiếu, khả năng khớp trong biên OHLC, vốn và
các lệnh tiếp theo. Đây không phải cùng ledger bị trừ thêm chi phí; không
diễn giải rằng tăng chi phí tạo lợi thế. Các biến động này là dấu hiệu nhạy
với mô hình khớp lệnh, cần giữ kết luận thận trọng.

## Bằng chứng và giới hạn

- 33/33 kiểm thử Python đạt, bao gồm native DB; Ruff/mypy đạt.
- Kiểm thử mới xác nhận trailing chỉ dùng phiên trước, không nới stop,
  dữ liệu tương lai không sửa giao dịch cũ và split không làm sai PnL.
- 36/36 hash kết quả khớp giữa hai lượt; sáu ledger đối chứng khớp nguyên vẹn
  nghiên cứu trước (baseline/hold15: validation base, comparison base/stress).
- Mọi lượt đối soát NAV và tiền không âm. Giữ cùng dataset hash; không nạp
  dữ liệu mới để thay mẫu khi thấy kết quả bất lợi.
- Win rate chỉ tính vị thế đóng hết; NAV bao gồm phần còn giữ. Các hạn chế
  về 24 quan sát mã–phiên thiếu, cổ phiếu thưởng, lô lẻ, thuế và dữ liệu lịch
  sử vẫn như [báo cáo dữ liệu thật](REAL_S1_BACKTEST_2026-10-21.md).
- [JSON đầy đủ 36 lượt](verification/s1-robustness.json) ghi các số liệu chưa
  làm tròn, cấu hình, hash, cảnh báo và tiêu chí; raw/ledger giữ local.
- Mặc định S1 và giao diện DEMO không thay đổi; trailing là tùy chọn nghiên cứu.

```powershell
$env:PYTHONPATH='apps/quant-worker'
& apps/quant-worker/.venv/Scripts/python.exe -m quant.s1_robustness .runtime/vndirect-s1-20261016
```

Lượt chạy lưu protocol, quyết định chọn và ledger riêng từng cấu hình trong
thư mục mới. `.runtime/vndirect-s1-20261016/latest-s1-robustness.txt` trỏ tới
lượt gần nhất. Không tự kích hoạt hay nâng một biến thể thành chiến lược live.
