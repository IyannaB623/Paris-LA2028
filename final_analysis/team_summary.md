# Team summary: Paris Airbnb pricing, occupancy, and revenue

## Primary analysis: pooled top-1% price excluded

The pooled 99th-percentile cutoff is **€1,090.58 per night**, calculated once from all 21,172 valid July–August 2023/2024 listing-months using `native_avg_daily_rate`. We apply this same cutoff to both years and exclude 212 rows (1.00%), leaving **20,960 listing-months from 8,127 listings**: 8,489 in 2023 and 12,471 in 2024. The histogram `price_histogram_pooled_q99.png` shows the full native-price distribution and cutoff. The trimmed sample is now primary; the full valid sample remains a sensitivity comparison.

Model 1 price estimate: +0.190 pp/€100 (p=0.382; 95% CI -0.237 to +0.617). Model 2, adding the entire-home control: +0.142 pp/€100 (p=0.515; 95% CI -0.286 to +0.571). Model 3 interaction coefficient: -0.925 pp/€100 (p=0.0387; 95% CI -1.802 to -0.048).

In Model 3, the 2023 price slope is +1.753 occupancy percentage points per €100 (p=4.96e-05; 95% CI +0.907 to +2.600); the 2024 slope is +0.828 (p=0.000179; 95% CI +0.395 to +1.261). The difference (2024 minus 2023) is -0.925 (p=0.0387; 95% CI -1.802 to -0.048). All three required regressions use this same trimmed sample and listing-clustered standard errors.

## How the findings compare with the original hypotheses

The preliminary claim asked whether higher nightly prices reduce bookings more during the 2024 Olympic period than in the ordinary-summer baseline. Theory offered two competing expectations: event demand and fewer substitutes could weaken price sensitivity, while an influx of supply or overpricing could strengthen a negative price–occupancy relationship. In the trimmed sample both estimated period-specific slopes are positive; higher listed prices are associated with higher occupancy in each period, not lower occupancy. The 2024 slope is significantly lower than the 2023 slope, so the equal-slope null is rejected at 5%. That downward shift is directionally consistent with stronger relative price sensitivity in 2024, but the positive slopes do not show that higher prices reduced occupancy in either year. These are observational associations, not causal effects or preregistered expectations.

## Full-sample sensitivity

The full valid sample uses all 21,172 rows and 8,179 listings. Model 1 price estimate: -0.080 pp/€100 (p=0.613; 95% CI -0.389 to +0.230); Model 2: -0.113 pp/€100 (p=0.475; 95% CI -0.423 to +0.197); Model 3 interaction: -0.236 pp/€100 (p=0.51; 95% CI -0.939 to +0.467). Full-sample Model 3 slopes are +0.547 pp/€100 in 2023 (p=0.108; 95% CI -0.120 to +1.213) and +0.311 in 2024 (p=0.0694; 95% CI -0.025 to +0.646); difference -0.236 (p=0.51; 95% CI -0.939 to +0.467). Comparing these estimates shows whether trimming changes magnitudes, intervals, and inference. Balanced four-month results are in `sensitivity_results.csv` as supplementary analyses.

## Supporting revenue comparison

See the updated revenue section and table in the dashboard, plus `revenue_comparison.csv` for the trimmed primary analysis and `revenue_supplementary_full_sample.csv` for the prior full-sample comparisons. The matched primary count requires all four study months to remain after trimming. The earlier untrimmed revenue comparison is retained as a clearly labeled supplementary result. Revenue is recorded gross revenue, not profit; it is not evidence that price caused revenue changes and does not identify an optimal LA price.

## Data decisions and limitations

The price field is `native_avg_daily_rate`, treated as EUR because every selected source row reports EUR. The exact Kaggle field-level currency definition is incomplete; this assumption is preserved. Price cutoff is on that same native-currency field. We retain genuine zero occupancy and do not filter on the ambiguous active flag. Bedrooms remains excluded because 13.3% are missing and some values are implausibly high; entire-home is the common control. Location, quality, amenities, timing, availability, and listing composition can affect both price and occupancy; monthly data cannot isolate Olympic dates. Better located or higher-quality listings may have both higher prices and higher occupancy, biasing price associations upward. Clustered errors address repeated listing observations but do not remove confounding.

<!-- REVENUE ANALYSIS START -->
## Supporting revenue comparison

The supporting question is whether average recorded gross revenue per listing increased or decreased in July–August 2024 versus July–August 2023. It does not replace the original occupancy question or the three required regressions.

`native_revenue` is treated as EUR using the same native-currency assumption as `native_avg_daily_rate`: all study rows report EUR, but the two revenue fields differ (median `revenue / native_revenue`=1.079) and the exact Kaggle field definitions are incomplete. There are 0 missing native-revenue values in the trimmed sample and 8,699 genuine zeros; none are imputed or dropped for being zero. `available_days` is not the denominator: calendar-night revenue is native revenue divided by calendar days.

The primary matched comparison has **2,352 listings**, each verified to retain all four study months after price trimming (9,408 listing-month rows; two months in each summer). July and August are averaged within each listing-year before the year comparison. This strict balanced definition makes the period comparison use the same listings and same months. Results compare per-listing amounts, not market totals.

| Primary comparison | Measure | 2023 mean / median | 2024 mean / median | Mean change | Median change |
|---|---|---:|---:|---:|---:|
| Trimmed full sample (listing-months) | Monthly gross revenue | €2,482.08 / €1,052.00 | €2,216.50 / €866.00 | -€265.58 (-10.7%) | -€186.00 (-17.7%) |
| Trimmed full sample (listing-months) | Gross revenue per calendar night | €80.07 / €33.94 | €71.50 / €27.94 | -€8.57 (-10.7%) | -€6.00 (-17.7%) |
| Matched trimmed listings (listing-year averages) | Monthly gross revenue | €3,189.12 / €2,429.50 | €2,654.48 / €1,341.75 | -€534.64 (-16.8%) | -€1,087.75 (-44.8%) |
| Matched trimmed listings (listing-year averages) | Gross revenue per calendar night | €102.87 / €78.37 | €85.63 / €43.28 | -€17.25 (-16.8%) | -€35.09 (-44.8%) |

**Supplementary untrimmed comparison:** `revenue_supplementary_full_sample.csv` preserves both the prior full-sample listing-month analysis and its all-four-month matched comparison (2,407 listings), clearly separate from the trimmed primary results. Its full-sample means are €2,630.81 (2023) and €2,328.13 (2024); the supplementary matched means are €3,509.28 and €2,888.75.

These are observational comparisons of recorded gross revenue, not profit. They do not show that prices caused revenue to change and do not identify an optimal LA price. For LA hosts, higher nightly rates alone do not guarantee higher gross receipts; costs, availability, booking timing, and demand also matter.

Presentation-ready wording is in `revenue_presentation_paragraph.md`; the chart is `revenue_comparison.png`. Trimmed primary results are in `revenue_comparison.csv`; earlier full-sample comparisons are in `revenue_supplementary_full_sample.csv`.
<!-- REVENUE ANALYSIS END -->
