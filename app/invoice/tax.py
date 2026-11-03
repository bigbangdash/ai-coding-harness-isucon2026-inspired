"""請求書の消費税計算（specs/invoice-tax/requirements.md）。

適格請求書のルールに従い、税率ごとに税抜金額を合計してから 1 回だけ端数処理する（REQ-2）。
金額はすべて整数（円）で扱う。
"""
from __future__ import annotations

from dataclasses import dataclass, field

SUPPORTED_RATES = (10, 8)  # REQ-1: 標準 10%、軽減 8%


class InvoiceTaxError(ValueError):
    """不正な明細（REQ-5）。"""


@dataclass(frozen=True)
class Line:
    unit_price: int  # 税抜単価（円）
    quantity: int
    rate: int        # 税率（%）


@dataclass(frozen=True)
class RateTotal:
    subtotal: int
    tax: int


@dataclass(frozen=True)
class InvoiceTax:
    by_rate: dict[int, RateTotal] = field(default_factory=dict)

    @property
    def subtotal(self) -> int:
        return sum(t.subtotal for t in self.by_rate.values())

    @property
    def tax(self) -> int:
        return sum(t.tax for t in self.by_rate.values())

    @property
    def total(self) -> int:
        return self.subtotal + self.tax


def _validate(line: Line) -> None:
    if line.rate not in SUPPORTED_RATES:
        raise InvoiceTaxError(f"未対応の税率: {line.rate}%")
    if line.quantity < 0 or line.unit_price < 0:
        raise InvoiceTaxError(f"数量・単価は 0 以上: {line}")


def calculate(lines: list[Line]) -> InvoiceTax:
    subtotals: dict[int, int] = {}
    for line in lines:
        _validate(line)
        subtotals[line.rate] = subtotals.get(line.rate, 0) + line.unit_price * line.quantity
    # REQ-2, REQ-3: 税率ごとに 1 回、切り捨て（金額は 0 以上なので整数除算 = 切り捨て）
    return InvoiceTax({rate: RateTotal(s, s * rate // 100) for rate, s in subtotals.items()})
