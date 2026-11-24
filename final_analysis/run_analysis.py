"""Reproducible Paris Airbnb analysis. Run from any directory with Python 3,
pandas, numpy, and matplotlib installed. Original project files are read only.
OLS is fit with numpy; listing-clustered sandwich inference is computed directly
because statsmodels/scipy are not installed in the supplied environment.
"""
from pathlib import Path
import json, math, platform, os
import numpy as np
import pandas as pd
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
SOURCE = ROOT / "past_rates.csv"
ID, DATE = "listing_id", "month_date"
PRICE = "native_avg_daily_rate"
Y = "occupancy"
CONTROL = "entire_home"

def betacf(a, b, x):
    qab=a+b; qap=a+1; qam=a-1; c=1.; d=1-qab*x/qap
    if abs(d)<1e-300: d=1e-300
    d=1/d; h=d
    for m in range(1,301):
        m2=2*m; aa=m*(b-m)*x/((qam+m2)*(a+m2)); d=1+aa*d
        if abs(d)<1e-300: d=1e-300
        c=1+aa/c
        if abs(c)<1e-300: c=1e-300
        d=1/d; h*=d*c; aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2)); d=1+aa*d
        if abs(d)<1e-300: d=1e-300
        c=1+aa/c
        if abs(c)<1e-300: c=1e-300
        d=1/d; delta=d*c; h*=delta
        if abs(delta-1)<3e-14: break
    return h

def ibeta(a,b,x):
    if x<=0: return 0.
    if x>=1: return 1.
    bt=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log1p(-x))
    if x<(a+1)/(a+b+2): return bt*betacf(a,b,x)/a
    return 1-bt*betacf(b,a,1-x)/b

def tcdf(t, df):
    x=df/(df+t*t); v=ibeta(df/2, .5, x)/2
    return 1-v if t>=0 else v

def tcrit95(df):
    lo,hi=0.,20.
    for _ in range(80):
        mid=(lo+hi)/2
        if tcdf(mid,df)<.975: lo=mid
        else: hi=mid
    return (lo+hi)/2

def fit_cluster(frame, terms, model):
    cols=[]
    for term in terms:
        if term=="const": cols.append(np.ones(len(frame)))
        else: cols.append(frame[term].to_numpy(float))
    X=np.column_stack(cols); y=100*frame[Y].to_numpy(float)  # model coefficients in occupancy percentage points
    inv=np.linalg.inv(X.T@X); b=inv@(X.T@y); resid=y-X@b
    groups=frame[ID].to_numpy(); unique=np.unique(groups); meat=np.zeros((X.shape[1],X.shape[1]))
    for g in unique:
        m=groups==g; score=X[m].T@resid[m]; meat+=np.outer(score,score)
    n,k=X.shape; G=len(unique)
    cov=inv@meat@inv * (G/(G-1))*((n-1)/(n-k))
    se=np.sqrt(np.diag(cov)); df=G-1; crit=tcrit95(df)
    t=b/se; p=np.array([2*(1-tcdf(abs(float(v)),df)) for v in t])
    r2=1-float(resid@resid)/float(((y-y.mean())**2).sum())
    table=[]
    for i,name in enumerate(terms):
        table.append(dict(model=model,term=name,coefficient=b[i],cluster_se=se[i],p_value=p[i],ci95_low=b[i]-crit*se[i],ci95_high=b[i]+crit*se[i],n=n,distinct_listings=G,r_squared=r2))
    return b,cov,table,r2

raw=pd.read_csv(SOURCE,dtype={ID:"string"},parse_dates=[DATE])
raw_n=len(raw); raw_ids=raw[ID].nunique(); raw_dups=int(raw.duplicated([ID,DATE]).sum())
s=raw[raw[DATE].dt.year.isin([2023,2024]) & raw[DATE].dt.month.isin([7,8])].copy()
s["period_2024"]=(s[DATE].dt.year==2024).astype(int)
s["period"] = np.where(s.period_2024.eq(1),"July–August 2024","July–August 2023")
s["entire_home"]=(s.room_type=="entire_home").astype(int)
s["price_eur"]=s[PRICE]
s["price_all_currency_field"]=s["avg_daily_rate"]
s["price_difference_all_minus_native"]=s["avg_daily_rate"]-s[PRICE]
s["price_per_100_eur"]=s.price_eur/100
s["price_x_2024"]=s.price_per_100_eur*s.period_2024

# Record quality checks before the sole analysis-sample restriction.
issues={
 "selected_rows":len(s),"selected_distinct_listings":int(s[ID].nunique()),
 "selected_duplicate_keys":int(s.duplicated([ID,DATE]).sum()),
 "selected_missing_any_model_fields":int(s[[ID,DATE,Y,PRICE,"room_type"]].isna().any(axis=1).sum()),
 "selected_nonpositive_native_prices":int((s[PRICE]<=0).sum()),
 "selected_occupancy_outside_0_1":int((~s[Y].between(0,1)).sum()),
 "selected_zero_occupancy":int((s[Y]==0).sum()),
 "selected_active_false":int((~s.active).sum()),
 "active_false_with_positive_occupancy":int(((~s.active)&(s[Y]>0)).sum()),
 "active_true_with_zero_occupancy":int((s.active&(s[Y]==0)).sum()),
 "selected_currency_values":s.currency.value_counts(dropna=False).to_dict(),
 "bedrooms_missing":int(s.bedrooms.isna().sum()),"bedrooms_missing_pct":float(s.bedrooms.isna().mean()),
 "bedrooms_over_10":int((s.bedrooms>10).sum()),"bedrooms_max":float(s.bedrooms.max()),
 "selected_duplicate_key_rows":int(s.duplicated([ID,DATE]).sum()),
 "native_to_avg_daily_rate_ratio_median":float((s["avg_daily_rate"]/s[PRICE]).median()),
 "avg_daily_rate_mean":float(s.avg_daily_rate.mean()),"native_rate_mean":float(s[PRICE].mean()),
 "raw_duplicate_keys":raw_dups,"raw_month_rows":raw_n,"raw_distinct_listings":int(raw_ids)
}
issues["valid_sample_rows"] = len(s)
issues["valid_sample_distinct_listings"] = int(s[ID].nunique())
issues["bedroom_analysis_sample_rows_if_complete"] = int(s["bedrooms"].notna().sum())
issues["all_four_month_listings"] = int((s.groupby(ID)[DATE].nunique()==4).sum())
issues["all_four_month_rows"] = int((s.groupby(ID)[DATE].nunique()==4).sum()*4)

# Key uniqueness and required outcome/price/type valid; preserve valid zero occupancy,
# active=False rows and all prices in the reference sample. Do not condition on active status.
full_clean=s.drop_duplicates([ID,DATE],keep="first").copy()
valid=full_clean[ID].notna()&full_clean[DATE].notna()&full_clean[Y].notna()&full_clean[PRICE].notna()&full_clean.room_type.notna()&(full_clean[PRICE]>0)&full_clean[Y].between(0,1)
full_clean=full_clean.loc[valid].copy()
# Calculate the pooled threshold once, then apply the identical price cutoff in each year.
q99=float(full_clean["price_eur"].quantile(.99))
full_clean["price_above_pooled_q99"] = full_clean["price_eur"].gt(q99)
full_clean["in_primary_trimmed_sample"] = ~full_clean["price_above_pooled_q99"]
clean=full_clean.loc[full_clean["price_eur"].le(q99)].copy()
full_clean.to_csv(OUT/"full_valid_analysis.csv",index=False,date_format="%Y-%m-%d")
clean.to_csv(OUT/"cleaned_analysis.csv",index=False,date_format="%Y-%m-%d")

dictionary=pd.DataFrame([
 [ID,"string","Source listing ID preserved verbatim; clustering unit."],
 [DATE,"YYYY-MM-DD","First day of the source month."],
 ["period","category","July–August 2023 or July–August 2024."],
 ["period_2024","0/1","1 for July–August 2024; 0 for July–August 2023."],
 [Y,"fraction, 0–1","Monthly occupancy supplied by source; genuine zeros retained."],
 ["price_eur","EUR/night","native_avg_daily_rate; native currency is EUR for every selected row."],
 ["price_all_currency_field","Source currency units/night","avg_daily_rate retained for comparison; currency semantics undocumented."],
 ["price_difference_all_minus_native","Source units minus EUR","avg_daily_rate minus native_avg_daily_rate."],
 ["price_per_100_eur","EUR/100","price_eur divided by 100, so price slope is pp occupancy per €100."],
 ["room_type","category","Source room_type."],
 [CONTROL,"0/1","1 when room_type=entire_home; 0 otherwise."],
 ["bedrooms","bedrooms","Candidate excluded from primary models due to missingness and implausible values."],
 ["active","boolean","Source monthly active flag; retained as a descriptive quality field, not exclusion rule."],
 ["currency","ISO code","Source field, EUR in all selected rows."],
 ["avg_daily_rate","undocumented units/night","Second source price field; preserved, not selected as EUR main predictor."],
 ["native_avg_daily_rate","native currency/night","Selected EUR rate, assuming native currency follows currency field; documentation incomplete."],
 ["revenue","source currency","Source gross-revenue measure; currency/conversion semantics are not documented for this exact file; preserved for comparison."],
 ["native_revenue","native currency","Source native gross-revenue measure; used as EUR because selected rows report currency=EUR, under an explicit assumption."],
 ["price_above_pooled_q99","0/1","True when native price exceeds the pooled full-study-sample 99th percentile; cutoff is applied identically to both years."],
 ["in_primary_trimmed_sample","0/1","True when native price is at or below the pooled q99 cutoff; rows above are excluded from primary regressions."],
],columns=["variable","units_or_coding","definition"])
dictionary.to_csv(OUT/"variable_dictionary.csv",index=False)

# Descriptives identify the trimmed primary sample and preserve full-sample rows
# as a clearly labeled sensitivity comparison.
def desc(df,label):
 rows=[]
 for v in ["price_eur",Y,CONTROL]:
  z=df[v].dropna(); rows.append(dict(sample=label,variable=v,n=len(z),mean=z.mean(),median=z.median(),sample_sd=z.std(ddof=1),minimum=z.min(),maximum=z.max()))
 return rows
PRIMARY_LABEL="Primary (pooled top 1% price excluded)"
FULL_LABEL="Full valid sample (sensitivity)"
descs=desc(clean,PRIMARY_LABEL)
for period,g in clean.groupby("period",sort=True): descs += desc(g,f"{period} — primary trimmed")
descs += desc(full_clean,FULL_LABEL)
for period,g in full_clean.groupby("period",sort=True): descs += desc(g,f"{period} — full sample sensitivity")
pd.DataFrame(descs).to_csv(OUT/"descriptive_statistics.csv",index=False)
counts=clean.groupby("period").agg(observations=(ID,"size"),distinct_listings=(ID,"nunique")).reset_index()
counts.to_csv(OUT/"period_counts.csv",index=False)
full_counts=full_clean.groupby("period").agg(observations=(ID,"size"),distinct_listings=(ID,"nunique")).reset_index()
full_counts.to_csv(OUT/"period_counts_full_sensitivity.csv",index=False)

models=[("Model 1",["const","price_per_100_eur"]),
 ("Model 2",["const","price_per_100_eur","entire_home"]),
 ("Model 3",["const","price_per_100_eur","period_2024","price_x_2024","entire_home"])]
tables=[]; fits={}
for sample_label,frame in [(PRIMARY_LABEL,clean),(FULL_LABEL,full_clean)]:
 for name,terms in models:
  b,cov,t,r2=fit_cluster(frame,terms,name)
  for item in t: item["analysis_sample"]=sample_label
  tables+=t; fits[(sample_label,name)]=(b,cov,terms)
pd.DataFrame(tables).to_csv(OUT/"regression_coefficients.csv",index=False)

# Model 3 linear combinations with covariance-based SE and cluster df.
contrasts=[]
for sample_label,frame in [(PRIMARY_LABEL,clean),(FULL_LABEL,full_clean)]:
 b,cov,terms=fits[(sample_label,"Model 3")]; ix={v:i for i,v in enumerate(terms)}; df=frame[ID].nunique()-1; crit=tcrit95(df)
 for label,vec in [("2023 price slope",{"price_per_100_eur":1}),
  ("2024 price slope",{"price_per_100_eur":1,"price_x_2024":1}),
  ("2024 minus 2023 slope",{"price_x_2024":1})]:
  v=np.zeros(len(terms))
  for term,val in vec.items(): v[ix[term]]=val
  est=float(v@b); se=float(math.sqrt(v@cov@v)); t=est/se; p=2*(1-tcdf(abs(t),df))
  contrasts.append(dict(analysis_sample=sample_label,contrast=label,estimate=est,cluster_se=se,p_value=p,ci95_low=est-crit*se,ci95_high=est+crit*se,units="occupancy percentage points per €100"))
pd.DataFrame(contrasts).to_csv(OUT/"model3_slopes.csv",index=False)

# Supplementary balanced-panel sensitivity: a listing must retain all four rows
# after the pooled price trim. Full-sample balanced panel retained for comparison.
sens=[]
for label,frame in [("Trimmed primary: listings observed in all four months",clean[clean.groupby(ID)[DATE].transform("nunique")==4]),
 ("Full sample sensitivity: listings observed in all four months",full_clean[full_clean.groupby(ID)[DATE].transform("nunique")==4])]:
 b2,c2,t2,r2=fit_cluster(frame,models[2][1],label)
 sens += t2
 # Add the 2023 and 2024 simple slopes plus difference from covariance.
 j={v:i for i,v in enumerate(models[2][1])}; dd=frame[ID].nunique()-1; cc=tcrit95(dd)
 for nm,coef in [("2023 slope",np.array([0,1,0,0,0.])),("2024 slope",np.array([0,1,0,1,0.])),("slope difference",np.array([0,0,0,1,0.]))]:
  est=float(coef@b2); se=float(math.sqrt(coef@c2@coef)); pv=2*(1-tcdf(abs(est/se),dd))
  sens.append(dict(model=label,term=nm,coefficient=est,cluster_se=se,p_value=pv,ci95_low=est-cc*se,ci95_high=est+cc*se,n=len(frame),distinct_listings=frame[ID].nunique(),r_squared=r2))
pd.DataFrame(sens).to_csv(OUT/"sensitivity_results.csv",index=False)

# Actual-observation charts. Density is shown with alpha; no bins or sample trimming.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, FuncFormatter
colors={"July–August 2023":"#4C78A8","July–August 2024":"#E15759"}
plt.rcParams.update({"font.size":11,"axes.titlesize":15,"figure.dpi":140})
def save(fig,name):
 fig.text(.01,.01,"Source: past_rates.csv | listing-month observations | primary sample excludes prices above pooled q99 unless noted",fontsize=8,color="#555")
 fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(OUT/name,dpi=300,bbox_inches="tight",facecolor="white"); plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5.5))
ax.hist(full_clean.price_eur,bins=70,color="#4C78A8",edgecolor="white",linewidth=.3)
ax.axvline(q99,color="#D95B5B",linewidth=2.2,linestyle="--",label=f"Pooled 99th percentile = €{q99:,.2f}")
ax.set(title=f"Full study sample native-currency nightly prices (N={len(full_clean):,})",
       xlabel="native_avg_daily_rate (EUR assumed; per night)",ylabel="Listing-month observations")
ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:f"€{x:,.0f}")); ax.legend(frameon=False,loc="upper right")
ax.text(.99,.82,f"Cutoff computed once from pooled 2023–2024 sample.\nExclude {len(full_clean)-len(clean):,} observations above cutoff in both periods.",
        transform=ax.transAxes,ha="right",va="top",fontsize=9,color="#555")
save(fig,"price_histogram_pooled_q99.png")
fig,ax=plt.subplots(figsize=(9,6))
for p,g in clean.groupby("period",sort=True): ax.scatter(g.price_eur,g[Y],s=9,alpha=.18,label=f"{p} (n={len(g):,})",c=colors[p],edgecolors="none")
ax.set(title=f"Monthly occupancy vs. price: primary trimmed sample (N={len(clean):,}; {clean[ID].nunique():,} listings)",xlabel="Native average nightly price (EUR assumed per night)",ylabel="Monthly occupancy")
ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:f"€{x:,.0f}")); ax.legend(frameon=False); save(fig,"scatter_occupancy_price.png")
fig,axes=plt.subplots(1,2,figsize=(10,5))
for ax,(v,title) in zip(axes,[("price_eur","Nightly price"),(Y,"Occupancy")]):
 vals=[clean.loc[clean.period==p,v].to_numpy() for p in ["July–August 2023","July–August 2024"]]
 ax.boxplot(vals,tick_labels=["2023","2024"],showfliers=False,whis=(5,95)); ax.set_title(title+" by period (5th–95th percentile whiskers)")
 if v=="price_eur": ax.set_ylabel("EUR per night"); ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f"€{x:,.0f}"))
 else: ax.set_ylabel("Monthly occupancy"); ax.yaxis.set_major_formatter(PercentFormatter(1))
 ax.set_xlabel("July–August period");
fig.suptitle(f"Actual listing-month observations; boxes show median and IQR (N={len(clean):,})"); save(fig,"period_split_distributions.png")
fig,ax=plt.subplots(figsize=(8,5))
means=clean.groupby("period")[Y].mean().reindex(["July–August 2023","July–August 2024"])
ax.bar(["2023","2024"],means,color=[colors["July–August 2023"],colors["July–August 2024"]]); ax.set(title="Mean occupancy by period",xlabel="July–August period",ylabel="Mean monthly occupancy",ylim=(0,1)); ax.yaxis.set_major_formatter(PercentFormatter(1));
for i,(p,val) in enumerate(means.items()): ax.text(i,val+.015,f"{val:.1%}\nn={int((clean.period==p).sum()):,}",ha="center")
save(fig,"period_mean_occupancy.png")

# Human-readable accounting and concise summary generated from saved results.
period_counts_primary=clean.groupby("period").agg(observations=(ID,"size"),distinct_listings=(ID,"nunique"))
trimmed_rows=int(len(full_clean)-len(clean))
issues.update({"full_valid_sample_rows":len(full_clean),"full_valid_sample_distinct_listings":int(full_clean[ID].nunique()),
 "analysis_sample_rows":len(clean),"analysis_sample_distinct_listings":int(clean[ID].nunique()),
 "analysis_removals_from_selected":trimmed_rows,"pooled_price_q99_eur":q99,
 "pooled_price_q99_quantile":0.99,"pooled_price_q99_rows_removed":trimmed_rows,
 "pooled_price_q99_pct_removed":100*trimmed_rows/len(full_clean),
 "primary_rows_2023":int((clean.period_2024==0).sum()),"primary_rows_2024":int((clean.period_2024==1).sum()),
 "primary_zero_occupancy":int(clean[Y].eq(0).sum()),
 "primary_listings_all_four_months":int((clean.groupby(ID)[DATE].nunique()==4).sum())})
(OUT/"data_quality.json").write_text(json.dumps(issues,indent=2,default=str))
coef=pd.DataFrame(tables); contrast=pd.DataFrame(contrasts); statdf=pd.DataFrame(descs)
def get(sample,model,term,col="coefficient"):
 return float(coef[(coef.analysis_sample==sample)&(coef.model==model)&(coef.term==term)][col].iloc[0])
def cget(sample,term,col):
 return float(contrast[(contrast.analysis_sample==sample)&(contrast.contrast==term)][col].iloc[0])
def citable(sample,model,term):
 return f"{get(sample,model,term):+.3f} pp/€100 (p={get(sample,model,term,'p_value'):.3g}; 95% CI {get(sample,model,term,'ci95_low'):+.3f} to {get(sample,model,term,'ci95_high'):+.3f})"
p23=int(period_counts_primary.loc["July–August 2023","observations"]); p24=int(period_counts_primary.loc["July–August 2024","observations"])
trim_slope_diff=cget(PRIMARY_LABEL,"2024 minus 2023 slope","estimate")
full_slope_diff=cget(FULL_LABEL,"2024 minus 2023 slope","estimate")
summary=f'''# Team summary: Paris Airbnb pricing, occupancy, and revenue

## Primary analysis: pooled top-1% price excluded

The pooled 99th-percentile cutoff is **€{q99:,.2f} per night**, calculated once from all {len(full_clean):,} valid July–August 2023/2024 listing-months using `native_avg_daily_rate`. We apply this same cutoff to both years and exclude {trimmed_rows:,} rows ({trimmed_rows/len(full_clean):.2%}), leaving **{len(clean):,} listing-months from {clean[ID].nunique():,} listings**: {p23:,} in 2023 and {p24:,} in 2024. The histogram `price_histogram_pooled_q99.png` shows the full native-price distribution and cutoff. The trimmed sample is now primary; the full valid sample remains a sensitivity comparison.

Model 1 price estimate: {citable(PRIMARY_LABEL,'Model 1','price_per_100_eur')}. Model 2, adding the entire-home control: {citable(PRIMARY_LABEL,'Model 2','price_per_100_eur')}. Model 3 interaction coefficient: {citable(PRIMARY_LABEL,'Model 3','price_x_2024')}.

In Model 3, the 2023 price slope is {cget(PRIMARY_LABEL,'2023 price slope','estimate'):+.3f} occupancy percentage points per €100 (p={cget(PRIMARY_LABEL,'2023 price slope','p_value'):.3g}; 95% CI {cget(PRIMARY_LABEL,'2023 price slope','ci95_low'):+.3f} to {cget(PRIMARY_LABEL,'2023 price slope','ci95_high'):+.3f}); the 2024 slope is {cget(PRIMARY_LABEL,'2024 price slope','estimate'):+.3f} (p={cget(PRIMARY_LABEL,'2024 price slope','p_value'):.3g}; 95% CI {cget(PRIMARY_LABEL,'2024 price slope','ci95_low'):+.3f} to {cget(PRIMARY_LABEL,'2024 price slope','ci95_high'):+.3f}). The difference (2024 minus 2023) is {trim_slope_diff:+.3f} (p={cget(PRIMARY_LABEL,'2024 minus 2023 slope','p_value'):.3g}; 95% CI {cget(PRIMARY_LABEL,'2024 minus 2023 slope','ci95_low'):+.3f} to {cget(PRIMARY_LABEL,'2024 minus 2023 slope','ci95_high'):+.3f}). All three required regressions use this same trimmed sample and listing-clustered standard errors.

## How the findings compare with the original hypotheses

The preliminary claim asked whether higher nightly prices reduce bookings more during the 2024 Olympic period than in the ordinary-summer baseline. Theory offered two competing expectations: event demand and fewer substitutes could weaken price sensitivity, while an influx of supply or overpricing could strengthen a negative price–occupancy relationship. In the trimmed sample both estimated period-specific slopes are positive; higher listed prices are associated with higher occupancy in each period, not lower occupancy. The 2024 slope is significantly lower than the 2023 slope, so the equal-slope null is rejected at 5%. That downward shift is directionally consistent with stronger relative price sensitivity in 2024, but the positive slopes do not show that higher prices reduced occupancy in either year. These are observational associations, not causal effects or preregistered expectations.

## Full-sample sensitivity

The full valid sample uses all {len(full_clean):,} rows and {full_clean[ID].nunique():,} listings. Model 1 price estimate: {citable(FULL_LABEL,'Model 1','price_per_100_eur')}; Model 2: {citable(FULL_LABEL,'Model 2','price_per_100_eur')}; Model 3 interaction: {citable(FULL_LABEL,'Model 3','price_x_2024')}. Full-sample Model 3 slopes are {cget(FULL_LABEL,'2023 price slope','estimate'):+.3f} pp/€100 in 2023 (p={cget(FULL_LABEL,'2023 price slope','p_value'):.3g}; 95% CI {cget(FULL_LABEL,'2023 price slope','ci95_low'):+.3f} to {cget(FULL_LABEL,'2023 price slope','ci95_high'):+.3f}) and {cget(FULL_LABEL,'2024 price slope','estimate'):+.3f} in 2024 (p={cget(FULL_LABEL,'2024 price slope','p_value'):.3g}; 95% CI {cget(FULL_LABEL,'2024 price slope','ci95_low'):+.3f} to {cget(FULL_LABEL,'2024 price slope','ci95_high'):+.3f}); difference {full_slope_diff:+.3f} (p={cget(FULL_LABEL,'2024 minus 2023 slope','p_value'):.3g}; 95% CI {cget(FULL_LABEL,'2024 minus 2023 slope','ci95_low'):+.3f} to {cget(FULL_LABEL,'2024 minus 2023 slope','ci95_high'):+.3f}). Comparing these estimates shows whether trimming changes magnitudes, intervals, and inference. Balanced four-month results are in `sensitivity_results.csv` as supplementary analyses.

## Data decisions and limitations

The price field is `native_avg_daily_rate`, treated as EUR because every selected source row reports EUR. The exact Kaggle field-level currency definition is incomplete; this assumption is preserved. Price cutoff is on that same native-currency field. We retain genuine zero occupancy and do not filter on the ambiguous active flag. Bedrooms remains excluded because 13.3% are missing and some values are implausibly high; entire-home is the common control. Location, quality, amenities, timing, availability, and listing composition can affect both price and occupancy; monthly data cannot isolate Olympic dates. Better located or higher-quality listings may have both higher prices and higher occupancy, biasing price associations upward. Clustered errors address repeated listing observations but do not remove confounding.
'''
(OUT/"team_summary.md").write_text(summary)

readme=f'''# Reproducible analysis

Run `python3 final_analysis/run_analysis.py`, then `python3 final_analysis/analyze_revenue.py`, then `python3 build_dashboard.py` from the project root (or run each script by absolute path). The analysis script reads `past_rates.csv` and writes into `final_analysis/`. It calculates the native-price 99th percentile once across the pooled valid four-month sample ({len(full_clean):,} rows), then applies the same €{q99:,.2f} cutoff in 2023 and 2024. The primary cleaned CSV has {len(clean):,} rows and {clean[ID].nunique():,} listings; `full_valid_analysis.csv` retains the full sample for sensitivity comparisons. Environment: Python {platform.python_version()}, pandas {pd.__version__}, numpy {np.__version__}. `statsmodels` and `scipy` are unavailable in the supplied environment, so OLS and listing-clustered sandwich standard errors are computed directly with NumPy; inference uses Student t with listing-cluster degrees of freedom.

Outputs include primary and full-sample descriptive/regression tables, period counts, slope contrasts, balanced-panel sensitivity results, data-quality JSON, the full-price histogram with cutoff, trimmed-sample charts, notebook, and team summary. The revenue script saves trimmed primary comparisons and clearly labeled supplementary full-sample comparisons. Price and revenue use native-currency fields as EUR under explicit assumptions. Dashboard charts are embedded in `analysis_output/dashboard.html`.
'''
(OUT/"README.md").write_text(readme)
print(f"Raw {raw_n:,}, raw listings {raw_ids:,}; selected {len(s):,} rows, {s[ID].nunique():,} IDs; analysis {len(clean):,} rows, {clean[ID].nunique():,} IDs")
print(pd.DataFrame(tables)[["model","term","coefficient","p_value","ci95_low","ci95_high","n","r_squared"]].to_string(index=False))
print(contrast.to_string(index=False)); print(pd.DataFrame(sens).to_string(index=False))
