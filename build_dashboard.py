"""Build the Paris Airbnb final-analysis dashboard from final_analysis outputs."""
from pathlib import Path
import base64
import html
import pandas as pd

ROOT = Path(__file__).resolve().parent
ANALYSIS = ROOT / "final_analysis"
OUT = ROOT / "analysis_output" / "dashboard.html"
stats = pd.read_csv(ANALYSIS / "descriptive_statistics.csv")
counts = pd.read_csv(ANALYSIS / "period_counts.csv")
reg = pd.read_csv(ANALYSIS / "regression_coefficients.csv")
slopes = pd.read_csv(ANALYSIS / "model3_slopes.csv")
sens = pd.read_csv(ANALYSIS / "sensitivity_results.csv")
revenue = pd.read_csv(ANALYSIS / "revenue_comparison.csv")
revenue_text = (ANALYSIS / "revenue_presentation_paragraph.md").read_text().strip()
quality = __import__("json").loads((ANALYSIS / "data_quality.json").read_text())
revenue_quality = __import__("json").loads((ANALYSIS / "revenue_data_quality.json").read_text())

FULL = "Full valid analysis sample"
P23, P24 = "July–August 2023", "July–August 2024"
VAR_LABELS = {"price_eur": "Nightly price (EUR)", "occupancy": "Monthly occupancy", "entire_home": "Entire-home indicator"}
MODEL_LABELS = {"Model 1": "Occupancy ~ price", "Model 2": "Occupancy ~ price + entire-home", "Model 3": "Occupancy ~ price + 2024 + price × 2024 + entire-home"}
TERM_LABELS = {"const": "Intercept", "price_per_100_eur": "Price (per €100)", "entire_home": "Entire-home control", "period_2024": "2024 period indicator", "price_x_2024": "Price × 2024 interaction"}

def row(frame, **conds):
    mask = pd.Series(True, index=frame.index)
    for col, val in conds.items(): mask &= frame[col].eq(val)
    return frame.loc[mask].iloc[0]

def fmt_eur(x): return f"€{x:,.2f}"
def fmt_delta_eur(x): return f"-€{abs(x):,.2f}" if x < 0 else f"+€{x:,.2f}"
def fmt_pct(x): return f"{x:.1%}"
def fmt_p(x): return "<0.001" if x < .001 else f"{x:.3f}"
def fmt_pp(x): return f"{x:+.3f} pp"
def esc(x): return html.escape(str(x))

def image_data(filename):
    payload = base64.b64encode((ANALYSIS / filename).read_bytes()).decode("ascii")
    return "data:image/png;base64," + payload

full_price = row(stats, sample=FULL, variable="price_eur")
full_occ = row(stats, sample=FULL, variable="occupancy")
full_home = row(stats, sample=FULL, variable="entire_home")
count_by_period = {r.period: r for r in counts.itertuples(index=False)}
N = int(full_price.n)
unique_n = int(quality["analysis_sample_distinct_listings"])

desc_rows = []
for sample in [FULL, P23, P24]:
    subset = stats[stats["sample"].eq(sample)]
    label = {FULL: "Full analysis sample", P23: "July–August 2023", P24: "July–August 2024"}[sample]
    for variable in ["price_eur", "occupancy", "entire_home"]:
        r = subset[subset.variable.eq(variable)].iloc[0]
        if variable == "price_eur": values = [fmt_eur(r["mean"]), fmt_eur(r["median"]), fmt_eur(r["sample_sd"])]
        elif variable == "occupancy": values = [fmt_pct(r["mean"]), fmt_pct(r["median"]), fmt_pct(r["sample_sd"])]
        else: values = [fmt_pct(r["mean"]), fmt_pct(r["median"]), fmt_pct(r["sample_sd"])]
        desc_rows.append(f"<tr><td>{esc(label)}</td><td>{esc(VAR_LABELS[variable])}</td><td>{int(r['n']):,}</td><td>{values[0]}</td><td>{values[1]}</td><td>{values[2]}</td></tr>")

reg_rows = []
for model in ["Model 1", "Model 2", "Model 3"]:
    for _, r in reg[reg.model.eq(model)].iterrows():
        reg_rows.append(
            f"<tr><td>{esc(model)}</td><td>{esc(TERM_LABELS.get(r.term, r.term))}</td>"
            f"<td>{r.coefficient:+.3f}</td><td>{fmt_p(r.p_value)}</td>"
            f"<td>[{r.ci95_low:+.3f}, {r.ci95_high:+.3f}]</td>"
            f"<td>{int(r.n):,}</td><td>{r.r_squared:.4f}</td></tr>"
        )

slope_rows = []
for _, r in slopes.iterrows():
    slope_rows.append(f"<tr><td>{esc(r.contrast)}</td><td>{fmt_pp(r.estimate)}</td><td>{fmt_p(r.p_value)}</td><td>[{r.ci95_low:+.3f}, {r.ci95_high:+.3f}]</td></tr>")

sens_label = "Exclude top 1% by price"
sens_slope23 = row(sens, model=sens_label, term="2023 slope")
sens_slope24 = row(sens, model=sens_label, term="2024 slope")
sens_diff = row(sens, model=sens_label, term="slope difference")
bal_diff = row(sens, model="Listings observed in all four months", term="slope difference")
top_n = N - int(row(sens, model=sens_label, term="const").n)

revenue_rows = []
for _, r in revenue.iterrows():
    if r.comparison == "Full study sample":
        sample_label = "Full study sample"
        units = f"{int(r.n_2023):,} / {int(r.n_2024):,} listing-months; {int(r.listings_2023):,} / {int(r.listings_2024):,} listings"
    else:
        sample_label = "Matched listings (four months)"
        units = f"{int(r.n_2023):,} / {int(r.n_2024):,} listing-years; {int(r.listings_2023):,} matched listings each year"
    revenue_rows.append(
        f"<tr><td>{esc(sample_label)}</td><td>{esc(r.metric)}</td><td>{units}</td>"
        f"<td>{fmt_eur(r.mean_2023_eur)}<br><small>median {fmt_eur(r.median_2023_eur)}</small></td>"
        f"<td>{fmt_eur(r.mean_2024_eur)}<br><small>median {fmt_eur(r.median_2024_eur)}</small></td>"
        f"<td>{fmt_delta_eur(r.mean_difference_2024_minus_2023_eur)} ({r.mean_change_pct:+.1f}%)</td>"
        f"<td>{fmt_delta_eur(r.median_difference_2024_minus_2023_eur)} ({r.median_change_pct:+.1f}%)</td></tr>"
    )

period_table = []
for p, year in [(P23, "2023"), (P24, "2024")]:
    c = count_by_period[p]
    pr = row(stats, sample=p, variable="price_eur")
    oc = row(stats, sample=p, variable="occupancy")
    period_table.append(f'''<div class="card period"><h3><span class="dot {'blue' if year == '2023' else 'red'}">●</span> July–August {year}</h3>
      <div class="metricrow"><span>Listing-month observations</span><b>{int(c.observations):,}</b></div>
      <div class="metricrow"><span>Distinct listings</span><b>{int(c.distinct_listings):,}</b></div>
      <div class="metricrow"><span>Mean nightly price</span><b>{fmt_eur(pr['mean'])}</b></div>
      <div class="metricrow"><span>Median nightly price</span><b>{fmt_eur(pr['median'])}</b></div>
      <div class="metricrow"><span>Mean occupancy</span><b>{fmt_pct(oc['mean'])}</b></div>
      <div class="metricrow"><span>Median occupancy</span><b>{fmt_pct(oc['median'])}</b></div></div>''')

imgs = {
    "scatter": image_data("scatter_occupancy_price.png"),
    "split": image_data("period_split_distributions.png"),
    "occupancy": image_data("period_mean_occupancy.png"),
    "revenue": image_data("revenue_comparison.png"),
}

doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pricing the Games | Paris Airbnb final analysis</title>
<style>
:root{{--ink:#18212f;--muted:#657184;--paper:#f3f5f8;--card:#fff;--line:#e4e8ef;--blue:#315a83;--red:#d95b5b;--green:#4d8d60}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1440px;margin:auto;padding:36px 38px 54px}}header{{background:#17283d;color:white;border-radius:20px;padding:36px 42px;position:relative;overflow:hidden}}header:after{{content:"";position:absolute;width:420px;height:420px;border-radius:50%;right:-100px;top:-240px;background:#315a83;opacity:.55}}.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:#b5c9dd;font-weight:700}}h1{{font-size:clamp(28px,4vw,44px);line-height:1.1;margin:12px 0 10px;max-width:860px}}header p{{color:#d4deea;margin:0;max-width:900px}}.headerrow{{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;position:relative;z-index:1}}.actions{{display:flex;gap:10px;flex-wrap:wrap}}button{{border:1px solid #ffffff55;border-radius:9px;background:#ffffff12;color:white;padding:10px 14px;font-weight:650;cursor:pointer}}
.section{{margin-top:28px}}.sectionhead{{display:flex;justify-content:space-between;gap:20px;align-items:end;margin:0 2px 13px}}h2{{margin:0;font-size:21px}}.sub{{color:var(--muted);font-size:13px;margin:4px 0 0}}.grid{{display:grid;gap:16px}}.kpis{{grid-template-columns:repeat(4,minmax(0,1fr))}}.card{{background:var(--card);border:1px solid var(--line);border-radius:15px;box-shadow:0 5px 18px #18212f08}}.kpi{{padding:19px 21px}}.label{{font-size:12px;font-weight:700;letter-spacing:.045em;color:var(--muted);text-transform:uppercase}}.kpi strong{{display:block;font-size:30px;letter-spacing:-.03em;margin-top:4px}}.kpi small{{color:var(--muted)}}.periodcards,.chartgrid,.split{{grid-template-columns:1fr 1fr}}.period{{padding:21px 23px}}.period h3{{margin:0 0 14px}}.metricrow{{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding:9px 0;gap:18px}}.metricrow span{{color:var(--muted)}}.metricrow b{{text-align:right}}.dot.blue{{color:var(--blue)}}.dot.red{{color:var(--red)}}.chart{{padding:14px 16px 12px}}.chart img{{display:block;width:100%;height:auto}}.chart h3{{margin:0 0 5px;font-size:16px}}.tablewrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:760px;font-size:13px}}th,td{{padding:10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}}thead th{{position:sticky;top:0;background:#f6f8fb;color:#526074;font-size:11px;text-transform:uppercase;letter-spacing:.03em}}th:first-child,td:first-child{{text-align:left}}.table-note{{padding:12px 16px;color:var(--muted);font-size:12px}}.findings{{padding:23px 26px}}.findings ul{{margin:10px 0 0;padding-left:20px}}.findings li{{margin:8px 0}}.notes{{grid-template-columns:repeat(3,1fr)}}.note{{padding:20px 22px}}.note h3{{margin:0 0 8px;font-size:15px}}.note p{{font-size:13px;color:var(--muted);margin:0}}.callout{{padding:20px 22px}}.callout p{{margin:5px 0;color:var(--muted)}}.tag{{display:inline-block;font-size:11px;padding:4px 8px;border-radius:20px;background:#f0f3f7;color:#526074;margin-left:6px}}footer{{color:var(--muted);font-size:12px;margin:23px 2px 0;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}}
@media(max-width:900px){{main{{padding:18px}}.kpis{{grid-template-columns:repeat(2,1fr)}}.chartgrid,.split,.notes{{grid-template-columns:1fr}}header{{padding:27px}}.headerrow{{display:block}}.actions{{margin-top:18px}}}}@media(max-width:520px){{.kpis,.periodcards{{grid-template-columns:1fr}}.kpi strong{{font-size:26px}}}}
@media print{{body{{background:white}}main{{max-width:none;padding:0}}header{{border-radius:0;print-color-adjust:exact;-webkit-print-color-adjust:exact}}.actions{{display:none}}.card{{break-inside:avoid;box-shadow:none}}.section{{break-inside:avoid-page}}.tablewrap{{overflow:visible}}table{{min-width:0;font-size:8px}}th,td{{padding:5px 3px}}thead th{{position:static}}}}
</style></head><body><main>
<header><div class="headerrow"><div><div class="eyebrow">Final analysis · Paris Airbnb · July–August comparison</div><h1>Pricing the Games</h1><p>Are higher nightly prices associated with lower occupancy, and did the price–occupancy relationship differ in July–August 2024 from the same months in 2023?<br>For hosts considering major-event pricing; these results describe associations and do not identify an optimal price.</p></div><div class="actions"><button onclick="window.print()">Print / Save as PDF</button></div></div></header>
<section class="section"><div class="sectionhead"><div><h2>At a glance</h2><p class="sub">Same valid sample used in all three regressions · listing-month unit</p></div></div><div class="grid kpis">
<div class="card kpi"><div class="label">Analysis observations</div><strong>{N:,}</strong><small>listing-months across four study months</small></div>
<div class="card kpi"><div class="label">Distinct selected listings</div><strong>{unique_n:,}</strong><small>9,114 is the full source count</small></div>
<div class="card kpi"><div class="label">Mean nightly price</div><strong>{fmt_eur(full_price['mean'])}</strong><small>median {fmt_eur(full_price['median'])} · native EUR rate</small></div>
<div class="card kpi"><div class="label">Mean occupancy</div><strong>{fmt_pct(full_occ['mean'])}</strong><small>median {fmt_pct(full_occ['median'])} · zeros retained</small></div>
</div></section>
<section class="section"><div class="sectionhead"><div><h2>Period comparison</h2><p class="sub">Period listing counts are distinct within each year; a listing may appear in both years.</p></div></div><div class="grid periodcards">{''.join(period_table)}</div></section>
<section class="section"><div class="sectionhead"><div><h2>Updated charts</h2><p class="sub">Full valid analysis sample; scatterplot points are actual listing-month observations.</p></div></div><div class="grid chartgrid">
<div class="card chart"><h3>Occupancy against nightly price, split by period</h3><img src="{imgs['scatter']}" alt="Scatterplot of actual occupancy observations against price by period"></div>
<div class="card chart"><h3>Price and occupancy distributions by period</h3><img src="{imgs['split']}" alt="Price and occupancy distribution comparison by study period"></div>
<div class="card chart"><h3>Mean occupancy by period</h3><img src="{imgs['occupancy']}" alt="Mean occupancy for 2023 and 2024"></div>
</div></section>
<section class="section"><div class="sectionhead"><div><h2>Descriptive statistics</h2><p class="sub">Sample standard deviation. Occupancy and entire-home are proportions shown as percentages; entire-home is 1 for entire_home listings.</p></div></div><div class="card tablewrap"><table><thead><tr><th>Sample</th><th>Variable</th><th>N</th><th>Mean</th><th>Median</th><th>Sample SD</th></tr></thead><tbody>{''.join(desc_rows)}</tbody></table><div class="table-note">Price is EUR/night. Occupancy is stored from 0 to 1. Entire-home is a 0/1 control.</div></div></section>
<section class="section"><div class="sectionhead"><div><h2>Three clustered OLS regressions</h2><p class="sub">Coefficients for price are occupancy percentage points per €100 higher nightly price. 95% confidence intervals and p-values use standard errors clustered by listing ID.</p></div></div><div class="card tablewrap"><table><thead><tr><th>Model</th><th>Term</th><th>Coefficient</th><th>p-value</th><th>95% CI</th><th>N</th><th>R²</th></tr></thead><tbody>{''.join(reg_rows)}</tbody></table><div class="table-note">All models use N={N:,} observations ({unique_n:,} listing clusters). Clustering accounts for repeated months from the same listing. Model 1: price only. Model 2: adds entire-home. Model 3: adds 2024 and price × 2024.</div></div></section>
<section class="section"><div class="sectionhead"><div><h2>Model 3: price slopes by period</h2><p class="sub">Linear combinations and their uncertainty use the Model 3 covariance matrix.</p></div></div><div class="card tablewrap"><table><thead><tr><th>Estimate</th><th>Slope / difference</th><th>p-value</th><th>95% CI</th></tr></thead><tbody>{''.join(slope_rows)}</tbody></table><div class="table-note">Slopes are occupancy percentage points per €100 higher price. The “2024 minus 2023” row tests whether the slopes differ.</div></div></section>
<section class="section"><div class="sectionhead"><div><h2>Supporting question: recorded gross revenue</h2><p class="sub">Per-listing comparisons, not market totals. The original occupancy research question and three regressions remain the primary analysis.</p></div></div>
<div class="card chart"><h3>Mean recorded gross revenue in July–August</h3><img src="{imgs['revenue']}" alt="Mean monthly gross revenue per listing and gross revenue per calendar night for full and matched samples in 2023 and 2024"></div>
<div class="card tablewrap" style="margin-top:16px"><table><thead><tr><th>Sample</th><th>Measure</th><th>Observations and listings (2023 / 2024)</th><th>2023 mean / median</th><th>2024 mean / median</th><th>Mean change</th><th>Median change</th></tr></thead><tbody>{''.join(revenue_rows)}</tbody></table>
<div class="table-note">Matched sample requires the same listing observed in July and August of both years. July and August are averaged within each listing-year. Calendar-night revenue divides native monthly revenue by the month's calendar days, never by available_days. {revenue_quality['native_revenue_zero_rows_retained']:,} zero-revenue rows are retained; missing revenue is not imputed ({revenue_quality['native_revenue_missing_rows']} missing in this sample).</div></div>
<div class="card findings" style="margin-top:16px"><h3>Presentation-ready wording</h3><p>{esc(revenue_text)}</p><p>Recorded gross revenue is not profit. These are observational comparisons: they do not show that price changes caused revenue changes and do not identify an optimal LA price.</p></div>
<div class="card callout" style="margin-top:16px"><h3>Revenue field assumption</h3><p>All study rows report EUR, but `revenue` and `native_revenue` differ (median ratio {revenue_quality['median_revenue_to_native_revenue_ratio']:.3f}). The analysis uses `native_revenue` as EUR, consistently with the `native_avg_daily_rate` assumption. The exact dataset's field-level documentation is incomplete, so this is an explicit assumption; see `final_analysis/revenue_method_notes.md`.</p></div></section>
<section class="section"><div class="sectionhead"><div><h2>What the results mean</h2><p class="sub">Observed estimates, separated from theory-based expectations.</p></div></div><div class="grid split">
<div class="card findings"><h3>Observed findings</h3><ul>
<li>The unadjusted and entire-home-adjusted price slopes are small and statistically uncertain. Their confidence intervals include zero.</li>
<li>In Model 3, neither year’s price slope nor the difference between them is statistically clear at the 5% level. The data do not show a reliable change in the price relationship between these periods.</li>
<li>Mean occupancy is lower and mean price is higher in the 2024 sample, but that period contrast alone does not establish that price changes caused occupancy to change.</li>
<li>For hosts, these estimates do not give an exact best price for Paris or LA. Listing quality, location, timing, availability, and demand could also shape the observed association.</li></ul></div>
<div class="card findings"><h3>Competing expectations</h3><ul>
<li>A ticket-driven demand surge and fewer substitutes could make guests less price-sensitive in 2024, weakening a negative price slope.</li>
<li>A surge in supply or overpricing against expected demand could strengthen a negative price slope as some listings remain unbooked.</li>
<li>These are theory-based competing predictions, not preregistered expectations. The main interaction estimate does not clearly distinguish them.</li></ul></div>
</div></section>
<section class="section"><div class="sectionhead"><div><h2>Sensitivity and measurement notes</h2><p class="sub">The full valid sample remains the primary analysis.</p></div></div><div class="grid notes">
<div class="card note"><h3>Price field and currency assumption</h3><p>Every selected row reports currency EUR, but avg_daily_rate and native_avg_daily_rate differ. The analysis uses native_avg_daily_rate as EUR/night, based on its native-currency name and the EUR field. The exact Kaggle file does not document why the fields differ, so this is an explicit assumption. Both values are preserved in the cleaned CSV. The corrected period mean prices are {fmt_eur(row(stats,sample=P23,variable='price_eur')['mean'])} (2023) and {fmt_eur(row(stats,sample=P24,variable='price_eur')['mean'])} (2024); earlier slides used the other field.</p></div>
<div class="card note"><h3>Highest-price sensitivity</h3><p>Dropping the top 1% ({top_n:,} observations; prices above about {fmt_eur(quality['price_top_1pct_threshold_eur'])}) changes the estimated slope difference to {fmt_pp(sens_diff.coefficient)} (p={fmt_p(sens_diff.p_value)}; 95% CI [{sens_diff.ci95_low:+.3f}, {sens_diff.ci95_high:+.3f}]). This negative difference is statistically detectable in that sensitivity but not the full sample; the inference is sensitive to the highest prices.</p><p>Top-1% slopes: 2023 {fmt_pp(sens_slope23.coefficient)}; 2024 {fmt_pp(sens_slope24.coefficient)}.</p></div>
<div class="card note"><h3>Other data choices</h3><p>The selected sample has {int(quality['selected_zero_occupancy']):,} zero-occupancy rows, retained. `active` was not used to exclude rows because some inactive records have positive occupancy and some active records have zero occupancy. Bedrooms was omitted: {int(quality['bedrooms_missing']):,} values are missing and some are unusually large. Entire-home is the common control, plausibly related to both price and demand.</p><p>For listings present in all four months, the slope difference is {fmt_pp(bal_diff.coefficient)} (p={fmt_p(bal_diff.p_value)}), consistent with the full-sample inference.</p></div>
</div></section>
<section class="section"><div class="card callout"><h3>Important limitations</h3><p>Monthly records combine dates outside the Olympic Games and cannot isolate event days. The year samples differ in size and listing composition. Location, property quality, amenities, timing, minimum stays, and availability may influence both price and occupancy. For example, better locations or higher-quality homes may charge more and attract more bookings, pushing the estimated price association upward (less negative) relative to a causal effect. Listing-clustered errors account for repeated observations, not confounding.</p><p>The downloaded Kaggle dataset page provides no readable field-level documentation in this review. An analogous past-calendar schema defines a native rate as an average daily rate in native currency; the applied EUR interpretation is therefore an assumption based on that convention and the sample currency column.</p></div></section>
<footer><span>DSO 510 · Paris Airbnb final analysis · Source: past_rates.csv</span><span>Built from saved files in final_analysis/</span></footer>
</main></body></html>'''

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(doc, encoding="utf-8")
print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
print(f"Loaded: N={N:,}, listings={unique_n:,}; model rows={len(reg):,}; chart files=4")
