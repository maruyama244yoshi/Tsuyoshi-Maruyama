"""元利均等返済の単純試算（動画内の数値はすべてこのロジックで算出する）。

計算方法（固定）:
  月利 r = 年利 / 12、返済回数 n = 年数 * 12
  毎月返済額 = P * r / (1 - (1 + r) ** -n)   … 円未満四捨五入
  年間返済額 = 毎月返済額 * 12
表示は「万円」単位で四捨五入（例: 4,435,440円 → 約444万円）。
※元利均等返済の単純試算。実際の融資条件（手数料・端数処理・返済日等）とは異なる。
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
import argparse
import json

getcontext().prec = 40
NOTE = "※元利均等返済の単純試算。実際の融資条件とは異なります。"


def monthly_payment(principal: int, annual_rate_pct: float, years: int) -> int:
    p = Decimal(principal)
    r = Decimal(str(annual_rate_pct)) / Decimal(100) / Decimal(12)
    n = years * 12
    if r == 0:
        m = p / n
    else:
        m = p * r / (1 - (1 + r) ** (-n))
    return int(m.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def annual_payment(principal: int, annual_rate_pct: float, years: int) -> int:
    return monthly_payment(principal, annual_rate_pct, years) * 12


def man(yen: int) -> int:
    """円 → 万円（四捨五入）。"""
    return int((Decimal(yen) / Decimal(10000)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def table(principal: int, years: int, rates):
    rows = []
    for rate in rates:
        m = monthly_payment(principal, rate, years)
        rows.append({"rate_pct": rate, "monthly_yen": m, "annual_yen": m * 12, "annual_man": man(m * 12)})
    base = rows[0]["annual_yen"]
    for r in rows:
        r["diff_vs_first_yen"] = r["annual_yen"] - base
        r["diff_vs_first_man"] = man(r["annual_yen"] - base)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--principal", type=int, default=100_000_000)
    ap.add_argument("--years", type=int, default=30)
    ap.add_argument("--rates", type=float, nargs="+", default=[2.00, 2.25, 2.50, 3.00])
    a = ap.parse_args()
    print(json.dumps({"principal": a.principal, "years": a.years, "note": NOTE,
                      "rows": table(a.principal, a.years, a.rates)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
