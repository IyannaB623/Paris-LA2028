# Team summary: Paris Airbnb price and occupancy

## Findings

The analysis uses 21,172 valid listing-months from 8,179 listings: 8,552 observations in July–August 2023 and 12,620 in July–August 2024. Model 1 estimates -0.080 occupancy percentage points per €100 (p=0.613; 95% CI -0.389 to +0.230). Model 2 estimates -0.113 points (p=0.475; 95% CI -0.423 to +0.197); the slope moved slightly more negative as expected, but neither baseline slope is distinguishable from zero at 5%.

In Model 3, the estimated price slope is +0.547 occupancy percentage points per €100 in 2023 (95% CI -0.120 to +1.213; p=0.108) and +0.311 points in 2024 (95% CI -0.025 to +0.646; p=0.0694). The 2024-minus-2023 slope difference is -0.236 points (95% CI -0.939 to +0.467; p=0.51); equal slopes cannot be rejected. Slopes are small and statistically uncertain. These are associations, not causal effects.

## Data and correction to preliminary slides

The raw source has 268,814 monthly rows and 9,114 distinct listing IDs. The July–August 2023/2024 sample has 21,172 rows and 8,179 listings, not 9,114 listings; 9,114 is the full-source distinct-listing count. The period split is 8,552 in 2023 and 12,620 in 2024. Rows are listing-months, not independent listings.

The preliminary analysis called `avg_daily_rate` EUR. All selected rows say currency EUR, and the source also supplies `native_avg_daily_rate`; these fields differ (median all-field/native ratio 1.080). The source documentation available here does not define the conversion basis of `avg_daily_rate`. We therefore use `native_avg_daily_rate` as EUR/night based on its native-currency name plus the EUR currency field, explicitly as an assumption; the analogous published schema describes the native rate as the average daily rate in native currency, but does not document the exact Kaggle file's conversion. Both fields remain in the cleaned data for comparison. Replacing the preliminary rate field revises mean rates from €203.86 to €185.99 (2023) and €277.12 to €257.51 (2024), and medians from €141.70 to €129 and €203.85 to €189. Occupancy figures are unchanged. Recompute/replace earlier price descriptives before presenting them.

## Data handling

No selected rows were excluded for zero occupancy or `active=False`: occupancy is a supplied monthly 0–1 measure, but its denominator and active flag timing are undocumented; inactive rows sometimes have positive occupancy and active rows sometimes have zero occupancy. We retain both, avoiding selection based on an ambiguous status. No selected rows have missing outcome, price, or room type; occupancy is bounded, prices are positive, and selected listing-month keys are unique. High-price observations remain in the main sample. Bedrooms are not included: 2,814 (13.3%) are missing and values reach 50, weakening comparability. Entire-home status is the common control because whole homes can command higher rates and meet different group/travel needs affecting demand; it is fully observed and defined consistently. Keep the same sample across all three models.

## Interpretation and limitations

Theory gives competing predictions. A ticket-driven demand shock and fewer substitutes could flatten price sensitivity in 2024; a surge in supply or overpricing could make the negative association stronger. Neither was preregistered. For hosts, the slope gives a descriptive average association per €100, not an exact optimal LA price.

Unobserved location, quality, amenities, booking timing, minimum-stay rules, and availability may affect both prices and occupancy. For example, desirable/high-quality homes can set higher prices and attract more bookings, biasing the price slope upward (less negative or more positive) relative to a causal price effect. Conversely, hosts may raise prices in response to expected demand, also pushing the association upward. Monthly aggregation covers dates outside the Games, and the panel is unbalanced; listing composition changes between years. Clustered standard errors account for repeated observations of the same listing but do not remove confounding.

The top-1% price sensitivity changes the inference: after dropping 212 observations above €1,090.58, the slopes are +1.753 points for 2023 and +0.828 for 2024, with a slope difference of -0.925 points (p=0.0387). The top-price sensitivity therefore produces a statistically detectable negative difference that is absent in the main sample, while both estimated group slopes remain positive. In the balanced four-month panel (9,628 rows, 2,407 listings), the slope difference is +0.151 (p=0.709), consistent with the main result. A balanced panel is selected toward listings continuously represented in the source and is not automatically more representative.

## Theory-based expectations for slides

Model 1 tests a zero price slope. Model 2 uses entire-home as a confounder proxy; controlling for property type could make the price slope more negative if whole homes are simultaneously costlier and more occupied. Model 3 tests equal slopes; demand-shock theory predicts a weaker negative association in 2024, while overpricing/supply-saturation predicts a stronger negative association. State these as theoretical expectations, not preregistered hypotheses.

<!-- REVENUE ANALYSIS START -->
## Supporting revenue comparison

The supporting question is whether average recorded gross revenue per listing increased or decreased in July–August 2024 versus July–August 2023. It does not replace the original occupancy question or the three required regressions.

`native_revenue` is the selected financial field, treated as EUR using the same explicit native-currency assumption as `native_avg_daily_rate`: every study row's currency field is EUR, and both native fields differ from the non-native fields. An analogous published schema describes revenue as total generated and native revenue as generated in native currency; the exact Kaggle file's field documentation is incomplete, so this remains an assumption. `revenue` and `native_revenue` have a median ratio of 1.079. There are 0 missing native-revenue values and 8,801 genuine zero-revenue rows. No missing revenue is imputed; any missing value is excluded only from the relevant revenue comparison. There are no negative revenue values. `available_days` is not used as a denominator: revenue per calendar night is native revenue divided by the number of days in that month.

The full-sample unit is a listing-month. The matched comparison requires the same listing to be present with valid revenue in July and August of both years (2,407 listings); it averages July and August within each listing-year before comparing years. It therefore reports one average per listing-year, not market totals. Listings in the two year samples differ in the full comparison.

| Comparison | Measure | 2023 | 2024 | 2024 minus 2023 |
|---|---|---:|---:|---:|
| Full sample (listing-months) | Monthly gross revenue — mean / median | €2,630.81 / €1,055.00 | €2,328.13 / €866.50 | mean -€302.68 (-11.5%); median -€188.50 (-17.9%) |
| Full sample (listing-months) | Gross revenue per calendar night — mean / median | €84.86 / €34.03 | €75.10 / €27.95 | mean -€9.76 (-11.5%); median -€6.08 (-17.9%) |
| Matched sample (2,407 listings; average listing-year) | Monthly gross revenue — mean / median | €3,509.28 / €2,473.50 | €2,888.75 / €1,378.00 | mean -€620.53 (-17.7%); median -€1,095.50 (-44.3%) |
| Matched sample (2,407 listings; average listing-year) | Gross revenue per calendar night — mean / median | €113.20 / €79.79 | €93.19 / €44.45 | mean -€20.02 (-17.7%); median -€35.34 (-44.3%) |

These are observational comparisons of recorded gross revenue, not profit. The higher 2024 mean nightly price coexisted with lower recorded gross revenue per listing-month on average in both samples. For LA 2028 hosts, this is a reminder that a higher asking price does not guarantee higher gross receipts; costs, availability, booking timing, and demand matter. Paris does not identify an optimal LA price, and this comparison cannot attribute revenue changes to prices.

Presentation-ready wording is also saved in `revenue_presentation_paragraph.md`; the chart is `revenue_comparison.png`. Full results are in `revenue_comparison.csv`.
<!-- REVENUE ANALYSIS END -->
