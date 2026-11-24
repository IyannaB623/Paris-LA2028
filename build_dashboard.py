"""Build dashboard.html from the saved final-analysis tables and charts."""
from pathlib import Path
import base64, html, json
import pandas as pd

ROOT = Path(__file__).resolve().parent
A = ROOT / "final_analysis"
OUT = ROOT / "analysis_output" / "dashboard.html"
stats = pd.read_csv(A / "descriptive_statistics.csv")
counts = pd.read_csv(A / "period_counts.csv")
regs = pd.read_csv(A / "regression_coefficients.csv")
slopes = pd.read_csv(A / "model3_slopes.csv")
sens = pd.read_csv(A / "sensitivity_results.csv")
revenue = pd.read_csv(A / "revenue_comparison.csv")
revenue_full = pd.read_csv(A / "revenue_supplementary_full_sample.csv")
q = json.loads((A / "data_quality.json").read_text())
rq = json.loads((A / "revenue_data_quality.json").read_text())
rev_text = (A / "revenue_presentation_paragraph.md").read_text().strip()
PRIMARY = "Primary (pooled top 1% price excluded)"
FULL = "Full valid sample (sensitivity)"

def get(frame, **filters):
    x = frame
    for k, v in filters.items(): x = x[x[k].eq(v)]
    return x.iloc[0]
def euro(x): return f"€{x:,.2f}"
def delta(x): return ("−" if x < 0 else "+") + f"€{abs(x):,.2f}"
def pval(x): return "<0.001" if x < .001 else f"{x:.3f}"
def pct(x): return f"{x:.1%}"
def pp(x): return f"{x:+.3f} pp"
def esc(x): return html.escape(str(x))
def img(name): return "data:image/png;base64," + base64.b64encode((A/name).read_bytes()).decode()

pr = get(stats, sample=PRIMARY, variable="price_eur")
oc = get(stats, sample=PRIMARY, variable="occupancy")
home = get(stats, sample=PRIMARY, variable="entire_home")
N, listings = int(pr.n), int(q["analysis_sample_distinct_listings"])
period_names = ["July–August 2023", "July–August 2024"]
period_labels = [x + " — primary trimmed" for x in period_names]

desc = []
for sample, label in [(PRIMARY,"Primary overall"),(period_labels[0],"2023 primary"),(period_labels[1],"2024 primary")]:
    for var, labelvar in [("price_eur","Nightly price (EUR)"),("occupancy","Monthly occupancy"),("entire_home","Entire-home control")]:
        r=get(stats,sample=sample,variable=var)
        conv = euro if var == "price_eur" else pct
        desc.append(f"<tr><td>{esc(label)}</td><td>{labelvar}</td><td>{int(r.n):,}</td><td>{conv(r['mean'])}</td><td>{conv(r['median'])}</td><td>{conv(r['sample_sd'])}</td></tr>")

terms={"const":"Intercept","price_per_100_eur":"Price (per €100)","entire_home":"Entire-home control","period_2024":"2024 indicator","price_x_2024":"Price × 2024"}
def regression_rows(sample):
    out=[]
    for _,r in regs[regs.analysis_sample.eq(sample)].iterrows():
        out.append(f"<tr><td>{r.model}</td><td>{terms.get(r.term,r.term)}</td><td>{r.coefficient:+.3f}</td><td>{pval(r.p_value)}</td><td>[{r.ci95_low:+.3f}, {r.ci95_high:+.3f}]</td><td>{int(r.n):,}</td><td>{r.r_squared:.4f}</td></tr>")
    return "".join(out)
primary_reg=regression_rows(PRIMARY)
full_reg=regression_rows(FULL)
slopedata=slopes[slopes.analysis_sample.eq(PRIMARY)]
slope_rows="".join(f"<tr><td>{esc(r.contrast)}</td><td>{pp(r.estimate)}</td><td>{pval(r.p_value)}</td><td>[{r.ci95_low:+.3f}, {r.ci95_high:+.3f}]</td></tr>" for _,r in slopedata.iterrows())
full_diff=get(slopes,analysis_sample=FULL,contrast="2024 minus 2023 slope")
prim_diff=get(slopes,analysis_sample=PRIMARY,contrast="2024 minus 2023 slope")
prim_23=get(slopes,analysis_sample=PRIMARY,contrast="2023 price slope")
prim_24=get(slopes,analysis_sample=PRIMARY,contrast="2024 price slope")
balanced=get(sens,model="Trimmed primary: listings observed in all four months",term="price_x_2024")

def revenue_rows(frame, supplementary=False):
    rows=[]
    for _,r in frame.iterrows():
        matched="matched" in r.comparison.lower() or "all four months" in r.comparison.lower()
        label=("Full-sample matched (supplementary)" if matched else "Full sample (supplementary)") if supplementary else ("Primary matched listings (all four months)" if matched else "Primary trimmed sample")
        obs=(f"{int(r.listings_2023):,} / {int(r.listings_2024):,} listings" if not matched else f"{int(r.listings_2023):,} matched listings/year")
        rows.append(f"<tr><td>{label}</td><td>{esc(r.metric)}</td><td>{obs}</td><td>{euro(r.mean_2023_eur)} / {euro(r.median_2023_eur)}</td><td>{euro(r.mean_2024_eur)} / {euro(r.median_2024_eur)}</td><td>{delta(r.mean_difference_2024_minus_2023_eur)} ({r.mean_change_pct:+.1f}%)</td><td>{delta(r.median_difference_2024_minus_2023_eur)} ({r.median_change_pct:+.1f}%)</td></tr>")
    return "".join(rows)

period_cards=[]
for name, label in zip(period_names,period_labels):
    c=get(counts,period=name); p=get(stats,sample=label,variable="price_eur"); o=get(stats,sample=label,variable="occupancy")
    period_cards.append(f"<article class='card'><h3>{name}</h3><p>{int(c.observations):,} listing-months · {int(c.distinct_listings):,} distinct listings</p><p>Price mean/median: {euro(p['mean'])} / {euro(p['median'])}</p><p>Occupancy mean/median: {pct(o['mean'])} / {pct(o['median'])}</p></article>")

chart_specs=[("price_histogram_pooled_q99.png","Full valid sample: native nightly price; dashed marker is pooled q99"),("scatter_occupancy_price.png","Primary sample: actual occupancy against nightly price, split by period"),("period_split_distributions.png","Primary sample: price and occupancy distributions by period"),("period_mean_occupancy.png","Primary sample: mean occupancy by period"),("revenue_comparison.png","Primary sample: recorded revenue comparisons")]
hist_chart=f"<article class='card chart'><h3>{chart_specs[0][1]}</h3><img src='{img(chart_specs[0][0])}' alt='{esc(chart_specs[0][1])}'></article>"
charts="".join(f"<article class='card chart'><h3>{title}</h3><img src='{img(file)}' alt='{esc(title)}'></article>" for file,title in chart_specs[1:])

doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Paris Airbnb | DSO 510 Final Analysis</title>
<style>
:root{{--ink:#18212f;--muted:#657184;--paper:#f3f5f8;--line:#e4e8ef;--blue:#315a83}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1440px;margin:auto;padding:34px}}header{{background:#17283d;color:white;border-radius:20px;padding:34px 40px}}h1{{font-size:40px;margin:8px 0}}header p{{color:#d4deea;max-width:950px}}h2{{font-size:22px;margin-bottom:4px}}h3{{margin:0 0 8px}}.section{{margin-top:28px}}.sub,.muted{{color:var(--muted);font-size:13px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.kpis{{grid-template-columns:repeat(4,minmax(0,1fr))}}.card{{background:white;border:1px solid var(--line);border-radius:15px;padding:20px;box-shadow:0 5px 18px #18212f08}}.kpi strong{{font-size:29px;display:block}}.kpi span{{font-size:12px;color:var(--muted);text-transform:uppercase;font-weight:700}}.chart img{{width:100%;height:auto;display:block}}.tablewrap{{overflow:auto;padding:0}}table{{width:100%;border-collapse:collapse;min-width:790px;font-size:13px}}th,td{{text-align:right;padding:9px;border-bottom:1px solid var(--line);white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{background:#f6f8fb;text-transform:uppercase;font-size:11px;color:#526074}}.table-note{{padding:12px;color:var(--muted);font-size:12px}}.callout{{padding:20px}}footer{{padding:20px;color:var(--muted);font-size:12px}}@media(max-width:850px){{main{{padding:15px}}.grid,.kpis{{grid-template-columns:1fr}}header{{padding:25px}}}}
</style></head><body><main><header><small>DSO 510 · Final analysis · Paris Airbnb</small><h1>Pricing the Games</h1><p>Are higher nightly prices associated with lower occupancy, and did that relationship differ between July–August 2023 and July–August 2024? These observational estimates do not establish causation or identify an optimal price for Los Angeles.</p></header>
<section class="section"><h2>Primary analysis at a glance</h2><p class="sub">The pooled 99th-percentile price-trimmed sample is primary. All three models use the same listing-month sample.</p><div class="grid kpis"><article class="card kpi"><span>Listing-months</span><strong>{N:,}</strong></article><article class="card kpi"><span>Distinct listings</span><strong>{listings:,}</strong><small>9,114 is the full source count</small></article><article class="card kpi"><span>Mean nightly price</span><strong>{euro(pr['mean'])}</strong><small>median {euro(pr['median'])} · assumed EUR</small></article><article class="card kpi"><span>Mean occupancy</span><strong>{pct(oc['mean'])}</strong><small>median {pct(oc['median'])} · genuine zeros retained</small></article></div></section>
<section class="section"><h2>Pooled price cutoff</h2><p class="sub">Cutoff calculated once across the full valid July–August 2023/2024 sample, then applied unchanged to both periods.</p><div class="grid">{hist_chart}</div><div class="card callout"><b>99th-percentile cutoff: {euro(q['pooled_price_q99_eur'])} per night.</b> This removes {q['pooled_price_q99_rows_removed']:,} of {q['full_valid_sample_rows']:,} valid rows ({q['pooled_price_q99_pct_removed']:.2f}% — just over 1% because of quantile ties), leaving {N:,} rows and {listings:,} listings for primary analysis.</div></section>
<section class="section"><h2>Period counts and descriptive statistics</h2><div class="grid">{''.join(period_cards)}</div><p class="sub">Sample SD; occupancy and entire-home are percentages. Entire-home indicator is 1 for entire_home listings.</p><div class="card tablewrap"><table><thead><tr><th>Sample</th><th>Variable</th><th>N</th><th>Mean</th><th>Median</th><th>Sample SD</th></tr></thead><tbody>{''.join(desc)}</tbody></table><div class="table-note">Price is native nightly rate assumed EUR; occupancy is a monthly proportion; control is a 0/1 variable.</div></div></section>
<section class="section"><h2>Primary analysis charts</h2><div class="grid">{charts}</div></section>
<section class="section"><h2>Three required listing-clustered OLS regressions</h2><p class="sub">Price effects are occupancy percentage points per €100 higher nightly price. Standard errors cluster by listing ID to account for repeated listing-month records.</p><div class="card tablewrap"><table><thead><tr><th>Model</th><th>Term</th><th>Coefficient</th><th>p-value</th><th>95% CI</th><th>N</th><th>R²</th></tr></thead><tbody>{primary_reg}</tbody></table><div class="table-note">Models: (1) price; (2) price + entire-home; (3) price + 2024 period + price × 2024 + entire-home. Entire-home effects are in occupancy percentage points.</div></div></section>
<section class="section"><h2>Model 3 price slopes</h2><div class="card tablewrap"><table><thead><tr><th>Estimate</th><th>Effect per €100</th><th>p-value</th><th>95% CI</th></tr></thead><tbody>{slope_rows}</tbody></table><div class="table-note">The primary estimates are 2023 {pp(prim_23.estimate)} (p={pval(prim_23.p_value)}; CI {prim_23.ci95_low:+.3f} to {prim_23.ci95_high:+.3f}), 2024 {pp(prim_24.estimate)} (p={pval(prim_24.p_value)}; CI {prim_24.ci95_low:+.3f} to {prim_24.ci95_high:+.3f}). Difference {pp(prim_diff.estimate)} (p={pval(prim_diff.p_value)}; CI {prim_diff.ci95_low:+.3f} to {prim_diff.ci95_high:+.3f}); these are linear combinations using the model covariance matrix.</div></div></section>
<section class="section"><h2>Full-sample regression sensitivity</h2><p class="sub">Estimates before excluding prices above q99; retain as a clearly labeled sensitivity comparison.</p><div class="card tablewrap"><table><thead><tr><th>Model</th><th>Term</th><th>Coefficient</th><th>p-value</th><th>95% CI</th><th>N</th><th>R²</th></tr></thead><tbody>{full_reg}</tbody></table><div class="table-note">Full-sample Model 3 interaction: {pp(full_diff.estimate)}, p={pval(full_diff.p_value)}, 95% CI [{full_diff.ci95_low:+.3f}, {full_diff.ci95_high:+.3f}], versus primary {pp(prim_diff.estimate)}, p={pval(prim_diff.p_value)}, 95% CI [{prim_diff.ci95_low:+.3f}, {prim_diff.ci95_high:+.3f}]. The sign and inference change; conclusions are sensitive to high-price observations.</div></div></section>
<section class="section"><h2>Supporting question: recorded gross revenue</h2><p class="sub">Per-listing averages rather than market totals. Gross revenue is not profit; comparisons are observational.</p><div class="card tablewrap"><table><thead><tr><th>Sample</th><th>Measure</th><th>Listings (2023 / 2024)</th><th>2023 mean / median</th><th>2024 mean / median</th><th>Mean change</th><th>Median change</th></tr></thead><tbody>{revenue_rows(revenue)}</tbody></table><div class="table-note">Matched comparison averages July and August within each listing-year. Primary matched panel has {int(balanced.distinct_listings):,} listings and {int(balanced.n):,} listing-months; each listing has all four months after trimming. Calendar-night revenue divides monthly native_revenue by calendar days, never available_days. {rq['primary_native_revenue_zero_rows_retained']:,} zero-revenue observations retained; {rq['primary_native_revenue_missing_rows']} missing values are not imputed.</div></div><div class="card tablewrap" style="margin-top:14px"><h3>Full-sample comparisons (supplementary)</h3><table><thead><tr><th>Sample</th><th>Measure</th><th>Listings (2023 / 2024)</th><th>2023 mean / median</th><th>2024 mean / median</th><th>Mean change</th><th>Median change</th></tr></thead><tbody>{revenue_rows(revenue_full,True)}</tbody></table></div><div class="card callout" style="margin-top:14px"><b>Presentation wording</b><p>{esc(rev_text)}</p><p>For LA 2028 hosts, this adds a gross-revenue comparison alongside occupancy, but it cannot show that price changes caused the revenue pattern. Paris does not identify an optimal LA price.</p></div></section>
<section class="section"><h2>Interpretation, hypotheses, and limitations</h2><div class="grid"><article class="card"><h3>Observed findings</h3><p>Models 1 and 2 show small, statistically uncertain price slopes. In Model 3, the trimmed-sample price slopes are positive in both periods: +1.753 pp per €100 in 2023 and +0.828 in 2024. The 2024-minus-2023 difference is −0.925 pp (p=.039; CI −1.802 to −0.048). That is opposite a simple negative price–occupancy hypothesis, but it is not causal evidence. The matched four-month primary interaction is {pp(balanced.coefficient)} (p={pval(balanced.p_value)}; CI {balanced.ci95_low:+.3f} to {balanced.ci95_high:+.3f}), not statistically clear.</p></article><article class="card"><h3>Theory-based expectations</h3><p>Event demand and fewer substitutes might weaken price sensitivity, while added supply or overpricing could strengthen a negative association. These competing expectations were theory-based, not preregistered; the full-sample comparison also demonstrates sensitivity to extreme prices.</p></article><article class="card"><h3>Currency and control assumptions</h3><p>Selected records state EUR. We use native_avg_daily_rate as euros/night, retaining avg_daily_rate for comparison because fields differ and file-specific documentation is incomplete. Entire-home is the control because property type can relate to both price and demand. Bedrooms has about 13% missing and extreme values, so it is not used.</p></article><article class="card"><h3>Limitations</h3><p>Monthly records do not isolate event dates. Year samples differ in composition. Location and property quality may raise both prices and bookings, biasing the observed price association upward (less negative). Availability, timing, amenities, and host strategy are unobserved; listing-clustered errors do not remove confounding. These results do not estimate a causal effect or an optimal LA price.</p></article></div></section>
<footer>DSO 510 · Source: past_rates.csv · Generated from saved final_analysis tables and charts</footer></main></body></html>'''
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(doc,encoding="utf-8")
print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
print(f"Primary N={N:,}; listings={listings:,}; q99={euro(q['pooled_price_q99_eur'])}; chart images=5")
