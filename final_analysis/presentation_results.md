# Slide-ready results: Paris Airbnb price and occupancy

## Primary sample and correction

Use native_avg_daily_rate as the nightly price, treated as euros because the selected data rows report EUR; the source file does not fully document why this differs from avg_daily_rate. Calculate q99 once in the pooled valid July–August 2023/2024 sample: €1,090.58/night. Apply the same cutoff to both years. The cutoff removes 212 of 21,172 listing-months (1.001%, due to ties), leaving 20,960 listing-months from 8,127 listings. Earlier counts of 9,114 refer to the full source, not this selected sample. The primary sample excludes prices above q99; all-full-sample results are sensitivity results.

## Occupancy regressions

All three OLS models use the same primary sample and standard errors clustered by listing ID. Effects are occupancy percentage points per €100 higher nightly price.

- Model 1, price only: +0.190 pp (p=.382; 95% CI −0.237 to +0.617).
- Model 2, adding entire-home: +0.142 pp (p=.515; 95% CI −0.286 to +0.571); entire-home coefficient +1.888 pp (p=.117; CI −0.474 to +4.249).
- Model 3, allowing year-specific slopes: 2023 slope +1.753 pp (p<.001; CI +0.907 to +2.600); 2024 slope +0.828 pp (p<.001; CI +0.395 to +1.261). Difference, 2024 minus 2023: −0.925 pp (p=.039; CI −1.802 to −0.048).

The positive period-specific slopes do not support a simple negative price–occupancy association in the trimmed sample. Their difference suggests a lower price slope in 2024, but the matched four-month sample of 2,352 listings has an uncertain interaction (+0.460 pp, p=.441; CI −0.711 to +1.631). The full-sample interaction is also uncertain (−0.236 pp, p=.510; CI −0.939 to +0.467). Magnitude and inference are sensitive to the high-price tail and listing composition.

## Revenue support

In the trimmed listing-month sample, mean monthly recorded gross revenue per listing fell from €2,482.08 in 2023 to €2,216.50 in 2024 (−€265.58; −10.7%); mean recorded revenue per calendar night fell from €80.07 to €71.50 (−€8.57; −10.7%). Among 2,352 listings verified to have all four months after trimming, mean monthly revenue averaged within listing-year fell from €3,189.12 to €2,654.48 (−€534.64; −16.8%). Full-sample comparisons remain supplementary. Gross revenue is not profit, and these are observational comparisons.

## Hypotheses, implications, limitations

The theory-based competing expectations remain: event demand and fewer substitutes might weaken price sensitivity; increased supply or overpricing might strengthen a negative association. These were not preregistered. The positive primary slopes are opposite a simple negative association hypothesis, while the lower 2024 slope is directionally consistent with relatively stronger sensitivity in that year. Neither pattern is causal. For LA 2028 hosts, the Paris evidence is descriptive context, not an exact LA pricing target. Location/property quality may increase both price and occupancy, biasing the association upward (less negative); monthly data cannot isolate event dates, year composition changes, and clustering does not eliminate confounding.
