"""Supporting recorded-revenue comparison using the prepared study sample.

Run after run_analysis.py. Reads the unchanged cleaned listing-month CSV and
writes revenue tables, one chart, documentation, and the team-summary addition
inside final_analysis/ only. No inferential regression is performed here.
"""
from pathlib import Path
import json
import os
import numpy as np
import pandas as pd
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / "cleaned_analysis.csv", dtype={"listing_id": "string"}, parse_dates=["month_date"])
ID, DATE = "listing_id", "month_date"
REV = "native_revenue"
df["year"] = df[DATE].dt.year
df["calendar_days"] = df[DATE].dt.days_in_month
df["gross_revenue_per_calendar_night"] = df[REV] / df["calendar_days"]
df["revenue_field_difference"] = df["revenue"] - df[REV]

quality = {
    "study_listing_month_rows": int(len(df)),
    "study_listings": int(df[ID].nunique()),
    "currency_values": df.currency.value_counts(dropna=False).to_dict(),
    "native_revenue_missing_rows": int(df[REV].isna().sum()),
    "revenue_missing_rows": int(df["revenue"].isna().sum()),
    "native_revenue_zero_rows_retained": int(df[REV].eq(0).sum()),
    "native_revenue_negative_rows": int(df[REV].lt(0).sum()),
    "native_revenue_min": float(df[REV].min()),
    "native_revenue_max": float(df[REV].max()),
    "median_revenue_to_native_revenue_ratio": float((df["revenue"] / df[REV].replace(0, np.nan)).median()),
    "native_revenue_gt_zero_and_occupancy_zero": int(((df[REV] > 0) & df.occupancy.eq(0)).sum()),
    "native_revenue_zero_and_occupancy_gt_zero": int((df[REV].eq(0) & df.occupancy.gt(0)).sum()),
}

# Valid revenue observations: no imputation. Zero is a genuine observed value.
revenue_valid = df[REV].notna() & df[REV].ge(0)
full = df.loc[revenue_valid].copy()

# Matched panel: same listing with July and August observed in both years;
# require all four revenue values to be present and valid.
month_counts = full.groupby(ID)[DATE].nunique()
matched_ids = month_counts[month_counts.eq(4)].index
matched_monthly = full[full[ID].isin(matched_ids)].copy()
assert matched_monthly.groupby(ID)[DATE].nunique().eq(4).all()
matched_annual = matched_monthly.groupby([ID, "year"], as_index=False).agg(
    monthly_gross_revenue_eur=(REV, "mean"),
    gross_revenue_per_calendar_night_eur=("gross_revenue_per_calendar_night", "mean"),
    months_observed=(DATE, "nunique"),
)
assert matched_annual.months_observed.eq(2).all()

def summarize(frame, sample, annual=False):
    records = []
    if annual:
        series = {
            "Monthly gross revenue per listing-month (EUR)": "monthly_gross_revenue_eur",
            "Gross revenue per calendar night (EUR/night)": "gross_revenue_per_calendar_night_eur",
        }
        unit = "listing-year; average of July and August within listing-year"
    else:
        series = {
            "Monthly gross revenue per listing-month (EUR)": REV,
            "Gross revenue per calendar night (EUR/night)": "gross_revenue_per_calendar_night",
        }
        unit = "listing-month"
    for metric, col in series.items():
        year_summaries = {}
        for year in (2023, 2024):
            g = frame[frame.year.eq(year)]
            vals = g[col].dropna()
            year_summaries[year] = {
                "n": int(vals.size),
                "listings": int(g.loc[vals.index, ID].nunique()),
                "mean": float(vals.mean()),
                "median": float(vals.median()),
            }
        a, b = year_summaries[2023], year_summaries[2024]
        records.append({
            "comparison": sample, "metric": metric, "unit_of_analysis": unit,
            "n_2023": a["n"], "listings_2023": a["listings"],
            "mean_2023_eur": a["mean"], "median_2023_eur": a["median"],
            "n_2024": b["n"], "listings_2024": b["listings"],
            "mean_2024_eur": b["mean"], "median_2024_eur": b["median"],
            "mean_difference_2024_minus_2023_eur": b["mean"] - a["mean"],
            "mean_change_pct": (b["mean"] / a["mean"] - 1) * 100 if a["mean"] else np.nan,
            "median_difference_2024_minus_2023_eur": b["median"] - a["median"],
            "median_change_pct": (b["median"] / a["median"] - 1) * 100 if a["median"] else np.nan,
        })
    return records

results = pd.DataFrame(
    summarize(full, "Full study sample")
    + summarize(matched_annual, "Matched listings: all four months", annual=True)
)
results.to_csv(HERE / "revenue_comparison.csv", index=False, float_format="%.6f")
quality.update({
    "valid_revenue_listing_months": int(len(full)),
    "valid_revenue_listings": int(full[ID].nunique()),
    "matched_all_four_month_listings": int(len(matched_ids)),
    "matched_listing_years": int(len(matched_annual)),
    "revenue_missing_sample_rows_excluded": int(len(df) - len(full)),
    "available_days_not_used_as_denominator": True,
})
(HERE / "revenue_data_quality.json").write_text(json.dumps(quality, indent=2, default=str))

# One figure, with explicitly labeled samples, measures, units, and Ns.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
colors = {2023: "#4C78A8", 2024: "#E15759"}
fig, axes = plt.subplots(2, 2, figsize=(11, 8))
panels = [
    (axes[0, 0], "Full study sample", "Monthly gross revenue per listing-month (EUR)", "mean_2023_eur", "mean_2024_eur", "listing-months"),
    (axes[0, 1], "Full study sample", "Gross revenue per calendar night (EUR/night)", "mean_2023_eur", "mean_2024_eur", "listing-months"),
    (axes[1, 0], "Matched listings: all four months", "Monthly gross revenue per listing-year average (EUR)", "mean_2023_eur", "mean_2024_eur", "listing-years"),
    (axes[1, 1], "Matched listings: all four months", "Gross revenue per calendar night (EUR/night)", "mean_2023_eur", "mean_2024_eur", "listing-years"),
]
for ax, sample, title, col23, col24, nlabel in panels:
    metric = "Monthly gross revenue per listing-month (EUR)" if "Monthly" in title else "Gross revenue per calendar night (EUR/night)"
    r = results[(results.comparison == sample) & (results.metric == metric)].iloc[0]
    vals = [r[col23], r[col24]]
    bars = ax.bar(["2023", "2024"], vals, color=[colors[2023], colors[2024]], width=.62)
    sample_title = "Full study sample" if sample == "Full study sample" else "Matched panel; listings observed in all four months"
    ax.set_title(f"{title}\n{sample_title}", fontsize=10)
    ax.set_xticks([0, 1], [f"2023\nN={int(r.n_2023):,} {nlabel}", f"2024\nN={int(r.n_2024):,} {nlabel}"])
    ax.set_ylabel("EUR per month" if "Monthly" in title else "EUR per calendar night")
    ax.set_ylim(0, max(vals) * 1.24 if max(vals) else 1)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*.025,
                f"€{val:,.0f}", ha="center", va="bottom", fontsize=10)
fig.suptitle("Recorded gross revenue: July–August 2023 vs 2024", fontsize=16, y=.99)
fig.text(.5, .01, "Means shown. Full sample uses listing-months; matched sample averages July and August within each listing-year. Zero-revenue observations retained.", ha="center", fontsize=9, color="#555")
fig.tight_layout(rect=(0, .045, 1, .96))
fig.savefig(HERE / "revenue_comparison.png", dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)

def fmtmoney(x): return f"€{x:,.2f}"
def fmtdelta(x): return f"-€{abs(x):,.2f}" if x < 0 else f"+€{x:,.2f}"
def fmtpct(x): return f"{x:+.1f}%"
presentation = []
for sample in ("Full study sample", "Matched listings: all four months"):
    monthly = results[(results.comparison == sample) & results.metric.str.startswith("Monthly")].iloc[0]
    daily = results[(results.comparison == sample) & results.metric.str.startswith("Gross revenue per calendar night")].iloc[0]
    if sample == "Full study sample":
        label = "Across the full study sample"
        ntext = f"({int(monthly.n_2023):,} listing-months in 2023; {int(monthly.n_2024):,} in 2024)"
    else:
        label = f"Among {int(monthly.listings_2023):,} listings observed in all four months"
        ntext = "after averaging July and August within each listing-year"
    presentation.append(
        f"{label}, mean recorded gross revenue per listing-month was {fmtmoney(monthly.mean_2023_eur)} in 2023 and {fmtmoney(monthly.mean_2024_eur)} in 2024, a change of {fmtdelta(monthly.mean_difference_2024_minus_2023_eur)} ({fmtpct(monthly.mean_change_pct)}); mean gross revenue per calendar night was {fmtmoney(daily.mean_2023_eur)} versus {fmtmoney(daily.mean_2024_eur)} {ntext}. These are observational comparisons of recorded gross revenue, not profit or evidence that price changes caused revenue to change. For LA 2028 hosts, the comparison highlights that higher nightly prices alone do not guarantee higher gross receipts; costs, availability, booking timing, and local demand matter, and Paris does not identify an optimal LA price."
    )
paragraph = "\n\n".join(presentation)
(HERE / "revenue_presentation_paragraph.md").write_text(paragraph + "\n")

def money_pair(r, prefix):
    return (f"2023 mean {fmtmoney(r['mean_2023_eur'])}, median {fmtmoney(r['median_2023_eur'])}; "
            f"2024 mean {fmtmoney(r['mean_2024_eur'])}, median {fmtmoney(r['median_2024_eur'])}. "
            f"Mean change {fmtdelta(r['mean_difference_2024_minus_2023_eur'])} ({r['mean_change_pct']:+.1f}%); "
            f"median change {fmtdelta(r['median_difference_2024_minus_2023_eur'])} ({r['median_change_pct']:+.1f}%).")
full_m = results[(results.comparison == "Full study sample") & results.metric.str.startswith("Monthly")].iloc[0]
full_d = results[(results.comparison == "Full study sample") & results.metric.str.startswith("Gross revenue per calendar night")].iloc[0]
match_m = results[(results.comparison == "Matched listings: all four months") & results.metric.str.startswith("Monthly")].iloc[0]
match_d = results[(results.comparison == "Matched listings: all four months") & results.metric.str.startswith("Gross revenue per calendar night")].iloc[0]
revenue_section = f'''<!-- REVENUE ANALYSIS START -->
## Supporting revenue comparison

The supporting question is whether average recorded gross revenue per listing increased or decreased in July–August 2024 versus July–August 2023. It does not replace the original occupancy question or the three required regressions.

`native_revenue` is the selected financial field, treated as EUR using the same explicit native-currency assumption as `native_avg_daily_rate`: every study row's currency field is EUR, and both native fields differ from the non-native fields. An analogous published schema describes revenue as total generated and native revenue as generated in native currency; the exact Kaggle file's field documentation is incomplete, so this remains an assumption. `revenue` and `native_revenue` have a median ratio of {quality['median_revenue_to_native_revenue_ratio']:.3f}. There are {quality['native_revenue_missing_rows']} missing native-revenue values and {quality['native_revenue_zero_rows_retained']:,} genuine zero-revenue rows. No missing revenue is imputed; any missing value is excluded only from the relevant revenue comparison. There are no negative revenue values. `available_days` is not used as a denominator: revenue per calendar night is native revenue divided by the number of days in that month.

The full-sample unit is a listing-month. The matched comparison requires the same listing to be present with valid revenue in July and August of both years ({int(len(matched_ids)):,} listings); it averages July and August within each listing-year before comparing years. It therefore reports one average per listing-year, not market totals. Listings in the two year samples differ in the full comparison.

| Comparison | Measure | 2023 | 2024 | 2024 minus 2023 |
|---|---|---:|---:|---:|
| Full sample (listing-months) | Monthly gross revenue — mean / median | {fmtmoney(full_m.mean_2023_eur)} / {fmtmoney(full_m.median_2023_eur)} | {fmtmoney(full_m.mean_2024_eur)} / {fmtmoney(full_m.median_2024_eur)} | mean {fmtdelta(full_m.mean_difference_2024_minus_2023_eur)} ({full_m.mean_change_pct:+.1f}%); median {fmtdelta(full_m.median_difference_2024_minus_2023_eur)} ({full_m.median_change_pct:+.1f}%) |
| Full sample (listing-months) | Gross revenue per calendar night — mean / median | {fmtmoney(full_d.mean_2023_eur)} / {fmtmoney(full_d.median_2023_eur)} | {fmtmoney(full_d.mean_2024_eur)} / {fmtmoney(full_d.median_2024_eur)} | mean {fmtdelta(full_d.mean_difference_2024_minus_2023_eur)} ({full_d.mean_change_pct:+.1f}%); median {fmtdelta(full_d.median_difference_2024_minus_2023_eur)} ({full_d.median_change_pct:+.1f}%) |
| Matched sample ({int(len(matched_ids)):,} listings; average listing-year) | Monthly gross revenue — mean / median | {fmtmoney(match_m.mean_2023_eur)} / {fmtmoney(match_m.median_2023_eur)} | {fmtmoney(match_m.mean_2024_eur)} / {fmtmoney(match_m.median_2024_eur)} | mean {fmtdelta(match_m.mean_difference_2024_minus_2023_eur)} ({match_m.mean_change_pct:+.1f}%); median {fmtdelta(match_m.median_difference_2024_minus_2023_eur)} ({match_m.median_change_pct:+.1f}%) |
| Matched sample ({int(len(matched_ids)):,} listings; average listing-year) | Gross revenue per calendar night — mean / median | {fmtmoney(match_d.mean_2023_eur)} / {fmtmoney(match_d.median_2023_eur)} | {fmtmoney(match_d.mean_2024_eur)} / {fmtmoney(match_d.median_2024_eur)} | mean {fmtdelta(match_d.mean_difference_2024_minus_2023_eur)} ({match_d.mean_change_pct:+.1f}%); median {fmtdelta(match_d.median_difference_2024_minus_2023_eur)} ({match_d.median_change_pct:+.1f}%) |

These are observational comparisons of recorded gross revenue, not profit. The higher 2024 mean nightly price coexisted with lower recorded gross revenue per listing-month on average in both samples. For LA 2028 hosts, this is a reminder that a higher asking price does not guarantee higher gross receipts; costs, availability, booking timing, and demand matter. Paris does not identify an optimal LA price, and this comparison cannot attribute revenue changes to prices.

Presentation-ready wording is also saved in `revenue_presentation_paragraph.md`; the chart is `revenue_comparison.png`. Full results are in `revenue_comparison.csv`.
<!-- REVENUE ANALYSIS END -->'''

summary_path = HERE / "team_summary.md"
base = summary_path.read_text()
start, end = "<!-- REVENUE ANALYSIS START -->", "<!-- REVENUE ANALYSIS END -->"
if start in base and end in base:
    before = base[:base.index(start)].rstrip()
    after = base[base.index(end) + len(end):].lstrip()
    base = before + ("\n\n" + after if after else "")
summary_path.write_text(base.rstrip() + "\n\n" + revenue_section + "\n")

notes = f'''# Revenue field and analysis notes

The source contains `revenue` and `native_revenue`. In the study sample, all {len(df):,} rows have `currency=EUR`; the revenue fields are not equal and the median `revenue / native_revenue` ratio is {quality['median_revenue_to_native_revenue_ratio']:.3f}. The analysis therefore uses `native_revenue` as the euro-denominated field, consistently with the price analysis. This is an explicit assumption because the exact Kaggle file does not provide readable field-level definitions. An analogous published AirROI past-calendar schema defines revenue as total generated and native revenue as generated in native currency. Source: https://www.airroi.com/data-portal/markets/paris-france (past calendar rates schema).

`available_days` was not used in the denominator. Here `available_days` and `unavailable_days` sum to calendar days and occupancy is mechanically aligned with unavailable days; they should not be mistaken for booked nights. The per-calendar-night measure is `native_revenue / days_in_month`.

Missing `native_revenue` is not imputed. A missing value is excluded from the revenue-only comparison; zeros are retained. Main-sample monthly averages weight each available listing-month equally. The matched sample includes only listings with all four July/August 2023/2024 rows and nonmissing valid revenue; July and August are averaged within listing-year, then the same 2,407 listing IDs are compared across years. These summaries compare per-listing amounts rather than market totals and are observational, with no causal inference or price optimization claim.
'''
(HERE / "revenue_method_notes.md").write_text(notes)
print(f"Wrote revenue comparison for {len(full):,} listing-months; matched {len(matched_ids):,} listings; missing revenue={quality['native_revenue_missing_rows']:,}; zeros retained={quality['native_revenue_zero_rows_retained']:,}")
print(results.to_string(index=False))
