"""Supporting recorded-revenue comparison using the prepared study sample.

Run after run_analysis.py. Reads the trimmed primary and untrimmed sensitivity
CSVs and writes revenue tables, chart, documentation, and the team-summary
addition inside final_analysis/ only. No inferential regression is performed.
"""
from pathlib import Path
import json
import os
import numpy as np
import pandas as pd
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / "cleaned_analysis.csv", dtype={"listing_id": "string"}, parse_dates=["month_date"])
full_df = pd.read_csv(HERE / "full_valid_analysis.csv", dtype={"listing_id": "string"}, parse_dates=["month_date"])
ID, DATE = "listing_id", "month_date"
REV = "native_revenue"
quality = json.loads((HERE / "data_quality.json").read_text())
cutoff = float(quality["pooled_price_q99_eur"])
for frame in (df, full_df):
    frame["year"] = frame[DATE].dt.year
    frame["calendar_days"] = frame[DATE].dt.days_in_month
    frame["gross_revenue_per_calendar_night"] = frame[REV] / frame["calendar_days"]
    frame["revenue_field_difference"] = frame["revenue"] - frame[REV]

# Missing values are not imputed; zero is a real recorded outcome. Full sample
# is retained in a separate table as supplementary comparison.
primary = df.loc[df[REV].notna() & df[REV].ge(0)].copy()
full = full_df.loc[full_df[REV].notna() & full_df[REV].ge(0)].copy()

def matched_panel(frame):
    nmonths = frame.groupby(ID)[DATE].nunique()
    ids = nmonths[nmonths.eq(4)].index
    monthly = frame[frame[ID].isin(ids)].copy()
    # Every selected listing must remain observed in all four months and valid.
    assert len(monthly) == 4 * len(ids)
    assert monthly.groupby(ID)[DATE].nunique().eq(4).all()
    annual = monthly.groupby([ID, "year"], as_index=False).agg(
        monthly_gross_revenue_eur=(REV, "mean"),
        gross_revenue_per_calendar_night_eur=("gross_revenue_per_calendar_night", "mean"),
        months_observed=(DATE, "nunique"),
    )
    assert annual.months_observed.eq(2).all()
    return ids, monthly, annual

matched_ids, matched_monthly, matched_annual = matched_panel(primary)
full_matched_ids, full_matched_monthly, full_matched_annual = matched_panel(full)
quality.update({
    "primary_revenue_rows": int(len(primary)),
    "primary_revenue_listings": int(primary[ID].nunique()),
    "primary_native_revenue_missing_rows": int(df[REV].isna().sum()),
    "primary_native_revenue_zero_rows_retained": int(df[REV].eq(0).sum()),
    "primary_matched_listings_all_four_months": int(len(matched_ids)),
    "primary_matched_rows_all_four_months": int(len(matched_monthly)),
    "primary_matched_listing_years": int(len(matched_annual)),
    "primary_matched_all_four_months_verified": bool(matched_monthly.groupby(ID)[DATE].nunique().eq(4).all()),
    "full_sample_supplementary_matched_listings": int(len(full_matched_ids)),
    "full_sample_supplementary_matched_listing_years": int(len(full_matched_annual)),
    "full_valid_revenue_rows": int(len(full)),
    "full_native_revenue_missing_rows": int(full_df[REV].isna().sum()),
    "full_native_revenue_zero_rows_retained": int(full_df[REV].eq(0).sum()),
    "native_revenue_negative_rows": int(full_df[REV].lt(0).sum()),
    "revenue_missing_rows_excluded_full": int(full_df[REV].isna().sum()),
    "median_revenue_to_native_revenue_ratio": float((full_df["revenue"] / full_df[REV].replace(0, np.nan)).median()),
    "native_revenue_gt_zero_and_occupancy_zero": int(((full_df[REV] > 0) & full_df.occupancy.eq(0)).sum()),
    "native_revenue_zero_and_occupancy_gt_zero": int((full_df[REV].eq(0) & full_df.occupancy.gt(0)).sum()),
    "pooled_native_price_q99_eur": cutoff,
    "available_days_not_used_as_denominator": True,
})

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
    summarize(primary, "Primary trimmed sample")
    + summarize(matched_annual, "Primary matched listings: all four months", annual=True)
)
supplementary = pd.DataFrame(
    summarize(full, "Full valid sample (supplementary)")
    + summarize(full_matched_annual, "Full matched listings: all four months (supplementary)", annual=True)
)
results.to_csv(HERE / "revenue_comparison.csv", index=False, float_format="%.6f")
supplementary.to_csv(HERE / "revenue_supplementary_full_sample.csv", index=False, float_format="%.6f")
(HERE / "revenue_data_quality.json").write_text(json.dumps(quality, indent=2, default=str))

# One figure, with explicitly labeled samples, measures, units, and Ns.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
colors = {2023: "#4C78A8", 2024: "#E15759"}
fig, axes = plt.subplots(2, 2, figsize=(11, 8))
panels = [
    (axes[0, 0], "Primary trimmed sample", "Monthly gross revenue per listing-month (EUR)", "mean_2023_eur", "mean_2024_eur", "listing-months"),
    (axes[0, 1], "Primary trimmed sample", "Gross revenue per calendar night (EUR/night)", "mean_2023_eur", "mean_2024_eur", "listing-months"),
    (axes[1, 0], "Primary matched listings: all four months", "Monthly gross revenue per listing-year average (EUR)", "mean_2023_eur", "mean_2024_eur", "listing-years"),
    (axes[1, 1], "Primary matched listings: all four months", "Gross revenue per calendar night (EUR/night)", "mean_2023_eur", "mean_2024_eur", "listing-years"),
]
for ax, sample, title, col23, col24, nlabel in panels:
    metric = "Monthly gross revenue per listing-month (EUR)" if "Monthly" in title else "Gross revenue per calendar night (EUR/night)"
    r = results[(results.comparison == sample) & (results.metric == metric)].iloc[0]
    vals = [r[col23], r[col24]]
    bars = ax.bar(["2023", "2024"], vals, color=[colors[2023], colors[2024]], width=.62)
    sample_title = "Primary sample; pooled top 1% of native prices excluded" if sample == "Primary trimmed sample" else "Matched trimmed panel; listings observed in all four months"
    ax.set_title(f"{title}\n{sample_title}", fontsize=10)
    ax.set_xticks([0, 1], [f"2023\nN={int(r.n_2023):,} {nlabel}", f"2024\nN={int(r.n_2024):,} {nlabel}"])
    ax.set_ylabel("EUR per month" if "Monthly" in title else "EUR per calendar night")
    ax.set_ylim(0, max(vals) * 1.24 if max(vals) else 1)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*.025,
                f"€{val:,.0f}", ha="center", va="bottom", fontsize=10)
fig.suptitle("Recorded gross revenue: July–August 2023 vs 2024", fontsize=16, y=.99)
fig.text(.5, .01, f"Means shown. Shared price cutoff: €{cutoff:,.2f}; matched sample averages July and August within listing-year. Zero-revenue observations retained.", ha="center", fontsize=9, color="#555")
fig.tight_layout(rect=(0, .045, 1, .96))
fig.savefig(HERE / "revenue_comparison.png", dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)

def fmtmoney(x): return f"€{x:,.2f}"
def fmtdelta(x): return f"-€{abs(x):,.2f}" if x < 0 else f"+€{x:,.2f}"
def fmtpct(x): return f"{x:+.1f}%"
presentation = []
for sample in ("Primary trimmed sample", "Primary matched listings: all four months"):
    monthly = results[(results.comparison == sample) & results.metric.str.startswith("Monthly")].iloc[0]
    daily = results[(results.comparison == sample) & results.metric.str.startswith("Gross revenue per calendar night")].iloc[0]
    if sample == "Primary trimmed sample":
        label = "In the primary sample, excluding listing-month prices above the pooled q99 cutoff"
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
primary_m = results[(results.comparison == "Primary trimmed sample") & results.metric.str.startswith("Monthly")].iloc[0]
primary_d = results[(results.comparison == "Primary trimmed sample") & results.metric.str.startswith("Gross revenue per calendar night")].iloc[0]
match_m = results[(results.comparison == "Primary matched listings: all four months") & results.metric.str.startswith("Monthly")].iloc[0]
match_d = results[(results.comparison == "Primary matched listings: all four months") & results.metric.str.startswith("Gross revenue per calendar night")].iloc[0]
supp_full_m = supplementary[(supplementary.comparison == "Full valid sample (supplementary)") & supplementary.metric.str.startswith("Monthly")].iloc[0]
supp_full_d = supplementary[(supplementary.comparison == "Full valid sample (supplementary)") & supplementary.metric.str.startswith("Gross revenue per calendar night")].iloc[0]
supp_match_m = supplementary[supplementary.metric.str.startswith("Monthly") & supplementary.comparison.str.startswith("Full matched")].iloc[0]
supp_match_d = supplementary[supplementary.metric.str.startswith("Gross revenue per calendar night") & supplementary.comparison.str.startswith("Full matched")].iloc[0]
revenue_section = f'''<!-- REVENUE ANALYSIS START -->
## Supporting revenue comparison

The supporting question is whether average recorded gross revenue per listing increased or decreased in July–August 2024 versus July–August 2023. It does not replace the original occupancy question or the three required regressions.

`native_revenue` is treated as EUR using the same native-currency assumption as `native_avg_daily_rate`: all study rows report EUR, but the two revenue fields differ (median `revenue / native_revenue`={quality['median_revenue_to_native_revenue_ratio']:.3f}) and the exact Kaggle field definitions are incomplete. There are {int(df[REV].isna().sum())} missing native-revenue values in the trimmed sample and {int(df[REV].eq(0).sum()):,} genuine zeros; none are imputed or dropped for being zero. `available_days` is not the denominator: calendar-night revenue is native revenue divided by calendar days.

The primary matched comparison has **{len(matched_ids):,} listings**, each verified to retain all four study months after price trimming ({len(matched_monthly):,} listing-month rows; two months in each summer). July and August are averaged within each listing-year before the year comparison. This strict balanced definition makes the period comparison use the same listings and same months. Results compare per-listing amounts, not market totals.

| Primary comparison | Measure | 2023 mean / median | 2024 mean / median | Mean change | Median change |
|---|---|---:|---:|---:|---:|
| Trimmed full sample (listing-months) | Monthly gross revenue | {fmtmoney(primary_m.mean_2023_eur)} / {fmtmoney(primary_m.median_2023_eur)} | {fmtmoney(primary_m.mean_2024_eur)} / {fmtmoney(primary_m.median_2024_eur)} | {fmtdelta(primary_m.mean_difference_2024_minus_2023_eur)} ({primary_m.mean_change_pct:+.1f}%) | {fmtdelta(primary_m.median_difference_2024_minus_2023_eur)} ({primary_m.median_change_pct:+.1f}%) |
| Trimmed full sample (listing-months) | Gross revenue per calendar night | {fmtmoney(primary_d.mean_2023_eur)} / {fmtmoney(primary_d.median_2023_eur)} | {fmtmoney(primary_d.mean_2024_eur)} / {fmtmoney(primary_d.median_2024_eur)} | {fmtdelta(primary_d.mean_difference_2024_minus_2023_eur)} ({primary_d.mean_change_pct:+.1f}%) | {fmtdelta(primary_d.median_difference_2024_minus_2023_eur)} ({primary_d.median_change_pct:+.1f}%) |
| Matched trimmed listings (listing-year averages) | Monthly gross revenue | {fmtmoney(match_m.mean_2023_eur)} / {fmtmoney(match_m.median_2023_eur)} | {fmtmoney(match_m.mean_2024_eur)} / {fmtmoney(match_m.median_2024_eur)} | {fmtdelta(match_m.mean_difference_2024_minus_2023_eur)} ({match_m.mean_change_pct:+.1f}%) | {fmtdelta(match_m.median_difference_2024_minus_2023_eur)} ({match_m.median_change_pct:+.1f}%) |
| Matched trimmed listings (listing-year averages) | Gross revenue per calendar night | {fmtmoney(match_d.mean_2023_eur)} / {fmtmoney(match_d.median_2023_eur)} | {fmtmoney(match_d.mean_2024_eur)} / {fmtmoney(match_d.median_2024_eur)} | {fmtdelta(match_d.mean_difference_2024_minus_2023_eur)} ({match_d.mean_change_pct:+.1f}%) | {fmtdelta(match_d.median_difference_2024_minus_2023_eur)} ({match_d.median_change_pct:+.1f}%) |

**Supplementary untrimmed comparison:** `revenue_supplementary_full_sample.csv` preserves both the prior full-sample listing-month analysis and its all-four-month matched comparison ({len(full_matched_ids):,} listings), clearly separate from the trimmed primary results. Its full-sample means are {fmtmoney(supp_full_m.mean_2023_eur)} (2023) and {fmtmoney(supp_full_m.mean_2024_eur)} (2024); the supplementary matched means are {fmtmoney(supp_match_m.mean_2023_eur)} and {fmtmoney(supp_match_m.mean_2024_eur)}.

These are observational comparisons of recorded gross revenue, not profit. They do not show that prices caused revenue to change and do not identify an optimal LA price. For LA hosts, higher nightly rates alone do not guarantee higher gross receipts; costs, availability, booking timing, and demand also matter.

Presentation-ready wording is in `revenue_presentation_paragraph.md`; the chart is `revenue_comparison.png`. Trimmed primary results are in `revenue_comparison.csv`; earlier full-sample comparisons are in `revenue_supplementary_full_sample.csv`.
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

The source contains `revenue` and `native_revenue`. All rows report `currency=EUR`; the revenue fields differ, with a median `revenue / native_revenue` ratio of {quality['median_revenue_to_native_revenue_ratio']:.3f}. We use `native_revenue` as EUR consistently with the price-field assumption. This is an explicit assumption because the exact Kaggle file does not expose readable field-level definitions. An analogous published AirROI past-calendar schema describes revenue as total generated and native revenue as the amount in native currency. Source: https://www.airroi.com/data-portal/markets/paris-france (past calendar rates schema).

`available_days` was not used in the denominator. Here `available_days` and `unavailable_days` sum to calendar days and occupancy is mechanically aligned with unavailable days; they should not be mistaken for booked nights. The per-calendar-night measure is `native_revenue / days_in_month`.

Missing `native_revenue` is not imputed; a missing value is excluded from the corresponding revenue comparison, and zero values are retained. Revenue per calendar night is `native_revenue / days_in_month`, never divided by `available_days`. The primary matched comparison has {len(matched_ids):,} listings with all four months still present after applying the pooled price cutoff, and averages July and August within listing-year. The earlier untrimmed full-sample and matched results are retained in `revenue_supplementary_full_sample.csv`. Comparisons are per listing, not market totals, and are observational.
'''
(HERE / "revenue_method_notes.md").write_text(notes)
print(f"Wrote trimmed revenue comparison for {len(primary):,} listing-months; matched {len(matched_ids):,} listings with all four months; missing revenue={quality['primary_native_revenue_missing_rows']:,}; zeros retained={quality['primary_native_revenue_zero_rows_retained']:,}")
print(results.to_string(index=False))
