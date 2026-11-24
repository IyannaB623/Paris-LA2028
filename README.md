# Paris Airbnb pricing and occupancy project

This repository contains the DSO 510 Paris Airbnb analysis comparing July–August 2023 with July–August 2024. The dashboard and final analysis outputs are committed; raw datasets are not.

## Research questions

**Primary question:** Are higher average nightly prices associated with lower monthly occupancy, and did that relationship differ between July–August 2023 and July–August 2024?

The primary analysis uses three OLS models on the same listing-month sample: occupancy on price; occupancy on price and an entire-home control; and occupancy on price, the 2024 indicator, their interaction, and the control. Standard errors are clustered by listing ID.

Following the professor's guidance, the primary sample excludes listing-month prices above the pooled 99th percentile (€1,090.58/night), calculated once across both study years and applied identically to each. This removes 212 of 21,172 valid observations, leaving 20,960 listing-months from 8,127 listings. Full valid-sample results are retained as sensitivity comparisons. `final_analysis/presentation_results.md` provides slide-ready findings and interpretation.

**Supporting question:** Did average recorded gross revenue per listing increase or decrease in July–August 2024 compared with July–August 2023? The revenue analysis compares listing-month means and medians, revenue per calendar night, and the same listings observed in all four study months. These are observational comparisons of recorded gross revenue, not profit or causal effects.

## Dataset source and obtaining the raw data

The source is the [Airbnb Paris Kaggle dataset](https://www.kaggle.com/datasets/abaghyangor/airbnb-paris). Raw source data is excluded from this repository because of size and provenance; each teammate must obtain the dataset directly from Kaggle. Sign in to Kaggle if required, open the dataset page, download its files, and place `past_rates.csv` in this repository's top-level folder. The scripts expect that exact filename. Do not commit downloaded source data. `past_rates.parquet`, `listings.parquet`, and `listings_monthly.csv` are also ignored.

The analysis preserves listing IDs as strings. It uses `native_avg_daily_rate` and `native_revenue` as EUR because the selected records report `currency=EUR`; the exact Kaggle file does not provide readable field-level currency documentation, so this is an explicit assumption. Both alternate financial fields remain in the prepared CSV for comparison. See `final_analysis/revenue_method_notes.md` for revenue definitions, missing-value handling, zero retention, and the calendar-night denominator.

## Repository contents

- `final_analysis/run_analysis.py` — prepares the common sample, descriptive statistics, clustered regressions, sensitivity analyses, and primary charts.
- `final_analysis/analyze_revenue.py` — calculates the supporting full-sample and matched-listing revenue comparisons and produces the revenue chart/table.
- `final_analysis/reproduce_analysis.ipynb` — notebook entry point that runs the two analysis scripts.
- `final_analysis/` — prepared analysis CSV, variable dictionary, descriptive and regression tables, sensitivity results, chart PNGs, revenue outputs, method notes, and team summary.
- `build_dashboard.py` — rebuilds the standalone dashboard from saved final-analysis outputs.
- `analysis_output/dashboard.html` — final dashboard. The charts are embedded in the HTML, so teammates can view this file without the raw dataset or adjacent image files.
- `requirements.txt` — Python packages used by the scripts.

The older `analyze_descriptives.py` and preliminary files under `analysis_output/` are not part of the final workflow. They predate the currency review and should not be used to regenerate final results.

## Reproduce the analysis

Use Python 3.10 or later. From the repository root, after obtaining `past_rates.csv` as described above:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 final_analysis/run_analysis.py
python3 final_analysis/analyze_revenue.py
python3 build_dashboard.py
```

The scripts write analysis artifacts under `final_analysis/` and rebuild `analysis_output/dashboard.html`. They do not modify the downloaded raw CSV. The notebook may be opened in Jupyter; its code cell runs the same scripts. Notebook users need Jupyter installed separately if it is not already available.

The cleaned CSV is a derived analysis file and is included for review. The raw inputs are needed to rerun the complete pipeline. The main analysis retains valid zero-occupancy observations and the revenue analysis retains zero-revenue observations; no missing revenue is imputed. The revenue/calendar-night measure divides monthly `native_revenue` by calendar days, not `available_days`.

## View the dashboard

Open `analysis_output/dashboard.html` in a browser (double-click it or use the browser's **Open File** command). It is self-contained: all charts are embedded, and it does not rely on local image paths or a web server. From GitHub, teammates should download the HTML file and then open that downloaded file in a browser; GitHub's code view does not render it as the dashboard. To rebuild it after analysis outputs change, run `python3 build_dashboard.py` from the project root.

## Collaboration

Create a branch for each change, keep raw data and credentials out of commits, and open a pull request for review. The repository intentionally contains the cleaned analysis and results but not source datasets or local environments.
