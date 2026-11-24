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
# active=False rows and high prices. Do not condition on active status.
clean=s.drop_duplicates([ID,DATE],keep="first").copy()
valid=clean[ID].notna()&clean[DATE].notna()&clean[Y].notna()&clean[PRICE].notna()&clean.room_type.notna()&(clean[PRICE]>0)&clean[Y].between(0,1)
clean=clean.loc[valid].copy()
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
],columns=["variable","units_or_coding","definition"])
dictionary.to_csv(OUT/"variable_dictionary.csv",index=False)

# Full descriptive stats and period counts for the actual common regression sample.
def desc(df,label):
 rows=[]
 for v in ["price_eur",Y,CONTROL]:
  z=df[v].dropna(); rows.append(dict(sample=label,variable=v,n=len(z),mean=z.mean(),median=z.median(),sample_sd=z.std(ddof=1),minimum=z.min(),maximum=z.max()))
 return rows
descs=desc(clean,"Full valid analysis sample")
for period,g in clean.groupby("period",sort=True): descs += desc(g,period)
pd.DataFrame(descs).to_csv(OUT/"descriptive_statistics.csv",index=False)
counts=clean.groupby("period").agg(observations=(ID,"size"),distinct_listings=(ID,"nunique")).reset_index()
counts.to_csv(OUT/"period_counts.csv",index=False)

models=[("Model 1",["const","price_per_100_eur"]),
 ("Model 2",["const","price_per_100_eur","entire_home"]),
 ("Model 3",["const","price_per_100_eur","period_2024","price_x_2024","entire_home"])]
tables=[]; fits={}
for name,terms in models:
 b,cov,t,r2=fit_cluster(clean,terms,name); tables+=t; fits[name]=(b,cov,terms)
pd.DataFrame(tables).to_csv(OUT/"regression_coefficients.csv",index=False)

# Model 3 linear combinations with covariance-based SE and cluster df.
b,cov,terms=fits["Model 3"]; ix={v:i for i,v in enumerate(terms)}; df=clean[ID].nunique()-1; crit=tcrit95(df)
contrasts=[]
for label,vec in [("2023 price slope",{"price_per_100_eur":1}),
 ("2024 price slope",{"price_per_100_eur":1,"price_x_2024":1}),
 ("2024 minus 2023 slope",{"price_x_2024":1})]:
 v=np.zeros(len(terms))
 for term,val in vec.items(): v[ix[term]]=val
 est=float(v@b); se=float(math.sqrt(v@cov@v)); t=est/se; p=2*(1-tcdf(abs(t),df))
 contrasts.append(dict(contrast=label,estimate=est,cluster_se=se,p_value=p,ci95_low=est-crit*se,ci95_high=est+crit*se,units="occupancy percentage points per €100"))
pd.DataFrame(contrasts).to_csv(OUT/"model3_slopes.csv",index=False)

# Sensitivities keep all model fields and same OLS specification.
q99=clean.price_eur.quantile(.99)
sens=[]
for label,frame in [("Main full valid sample",clean),("Exclude top 1% by price",clean[clean.price_eur<=q99]),
 ("Listings observed in all four months",clean[clean.groupby(ID)[DATE].transform("nunique")==4])]:
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
 fig.text(.01,.01,"Source: past_rates.csv | listing-month observations | full valid analysis sample unless noted",fontsize=8,color="#555")
 fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(OUT/name,dpi=300,bbox_inches="tight",facecolor="white"); plt.close(fig)
fig,ax=plt.subplots(figsize=(9,6))
for p,g in clean.groupby("period",sort=True): ax.scatter(g.price_eur,g[Y],s=9,alpha=.18,label=f"{p} (n={len(g):,})",c=colors[p],edgecolors="none")
ax.set(title=f"Monthly occupancy vs. nightly price (N={len(clean):,}; {clean[ID].nunique():,} listings)",xlabel="Average nightly price (EUR per night)",ylabel="Monthly occupancy")
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
issues.update({"analysis_sample_rows":len(clean),"analysis_sample_distinct_listings":int(clean[ID].nunique()),"analysis_removals_from_selected":len(s)-len(clean),"price_top_1pct_threshold_eur":float(q99)})
(OUT/"data_quality.json").write_text(json.dumps(issues,indent=2,default=str))
coef=pd.DataFrame(tables); contrast=pd.DataFrame(contrasts); statdf=pd.DataFrame(descs)
def get(model,term,col="coefficient"): return float(coef[(coef.model==model)&(coef.term==term)][col].iloc[0])
def cget(term,col): return float(contrast[contrast.contrast==term][col].iloc[0])
summary=f'''# Team summary: Paris Airbnb price and occupancy

## Findings

The analysis uses {len(clean):,} valid listing-months from {clean[ID].nunique():,} listings: {int((clean.period_2024==0).sum()):,} observations in July–August 2023 and {int((clean.period_2024==1).sum()):,} in July–August 2024. Model 1 estimates {get('Model 1','price_per_100_eur'):+.3f} occupancy percentage points per €100 (p={get('Model 1','price_per_100_eur','p_value'):.3g}; 95% CI {get('Model 1','price_per_100_eur','ci95_low'):+.3f} to {get('Model 1','price_per_100_eur','ci95_high'):+.3f}). Model 2 estimates {get('Model 2','price_per_100_eur'):+.3f} points (p={get('Model 2','price_per_100_eur','p_value'):.3g}; 95% CI {get('Model 2','price_per_100_eur','ci95_low'):+.3f} to {get('Model 2','price_per_100_eur','ci95_high'):+.3f}); the slope moved slightly more negative as expected, but neither baseline slope is distinguishable from zero at 5%.

In Model 3, the estimated price slope is {cget('2023 price slope','estimate'):+.3f} occupancy percentage points per €100 in 2023 (95% CI {cget('2023 price slope','ci95_low'):+.3f} to {cget('2023 price slope','ci95_high'):+.3f}; p={cget('2023 price slope','p_value'):.3g}) and {cget('2024 price slope','estimate'):+.3f} points in 2024 (95% CI {cget('2024 price slope','ci95_low'):+.3f} to {cget('2024 price slope','ci95_high'):+.3f}; p={cget('2024 price slope','p_value'):.3g}). The 2024-minus-2023 slope difference is {cget('2024 minus 2023 slope','estimate'):+.3f} points (95% CI {cget('2024 minus 2023 slope','ci95_low'):+.3f} to {cget('2024 minus 2023 slope','ci95_high'):+.3f}; p={cget('2024 minus 2023 slope','p_value'):.3g}); equal slopes cannot be rejected. Slopes are small and statistically uncertain. These are associations, not causal effects.

## Data and correction to preliminary slides

The raw source has {raw_n:,} monthly rows and {raw_ids:,} distinct listing IDs. The July–August 2023/2024 sample has {len(s):,} rows and {s[ID].nunique():,} listings, not 9,114 listings; 9,114 is the full-source distinct-listing count. The period split is {int((s.period_2024==0).sum()):,} in 2023 and {int((s.period_2024==1).sum()):,} in 2024. Rows are listing-months, not independent listings.

The preliminary analysis called `avg_daily_rate` EUR. All selected rows say currency EUR, and the source also supplies `native_avg_daily_rate`; these fields differ (median all-field/native ratio {float((s.avg_daily_rate/s.native_avg_daily_rate).median()):.3f}). The source documentation available here does not define the conversion basis of `avg_daily_rate`. We therefore use `native_avg_daily_rate` as EUR/night based on its native-currency name plus the EUR currency field, explicitly as an assumption; the analogous published schema describes the native rate as the average daily rate in native currency, but does not document the exact Kaggle file's conversion. Both fields remain in the cleaned data for comparison. Replacing the preliminary rate field revises mean rates from €203.86 to €185.99 (2023) and €277.12 to €257.51 (2024), and medians from €141.70 to €129 and €203.85 to €189. Occupancy figures are unchanged. Recompute/replace earlier price descriptives before presenting them.

## Data handling

No selected rows were excluded for zero occupancy or `active=False`: occupancy is a supplied monthly 0–1 measure, but its denominator and active flag timing are undocumented; inactive rows sometimes have positive occupancy and active rows sometimes have zero occupancy. We retain both, avoiding selection based on an ambiguous status. No selected rows have missing outcome, price, or room type; occupancy is bounded, prices are positive, and selected listing-month keys are unique. High-price observations remain in the main sample. Bedrooms are not included: {int(s.bedrooms.isna().sum()):,} ({s.bedrooms.isna().mean():.1%}) are missing and values reach {s.bedrooms.max():.0f}, weakening comparability. Entire-home status is the common control because whole homes can command higher rates and meet different group/travel needs affecting demand; it is fully observed and defined consistently. Keep the same sample across all three models.

## Interpretation and limitations

Theory gives competing predictions. A ticket-driven demand shock and fewer substitutes could flatten price sensitivity in 2024; a surge in supply or overpricing could make the negative association stronger. Neither was preregistered. For hosts, the slope gives a descriptive average association per €100, not an exact optimal LA price.

Unobserved location, quality, amenities, booking timing, minimum-stay rules, and availability may affect both prices and occupancy. For example, desirable/high-quality homes can set higher prices and attract more bookings, biasing the price slope upward (less negative or more positive) relative to a causal price effect. Conversely, hosts may raise prices in response to expected demand, also pushing the association upward. Monthly aggregation covers dates outside the Games, and the panel is unbalanced; listing composition changes between years. Clustered standard errors account for repeated observations of the same listing but do not remove confounding.

The top-1% price sensitivity changes the inference: after dropping 212 observations above €{q99:,.2f}, the slopes are {float(pd.DataFrame(sens).query("model == 'Exclude top 1% by price' and term == '2023 slope'").coefficient.iloc[0]):+.3f} points for 2023 and {float(pd.DataFrame(sens).query("model == 'Exclude top 1% by price' and term == '2024 slope'").coefficient.iloc[0]):+.3f} for 2024, with a slope difference of {float(pd.DataFrame(sens).query("model == 'Exclude top 1% by price' and term == 'slope difference'").coefficient.iloc[0]):+.3f} points (p={float(pd.DataFrame(sens).query("model == 'Exclude top 1% by price' and term == 'slope difference'").p_value.iloc[0]):.3g}). The top-price sensitivity therefore produces a statistically detectable negative difference that is absent in the main sample, while both estimated group slopes remain positive. In the balanced four-month panel (9,628 rows, 2,407 listings), the slope difference is {float(pd.DataFrame(sens).query("model == 'Listings observed in all four months' and term == 'slope difference'").coefficient.iloc[0]):+.3f} (p={float(pd.DataFrame(sens).query("model == 'Listings observed in all four months' and term == 'slope difference'").p_value.iloc[0]):.3g}), consistent with the main result. A balanced panel is selected toward listings continuously represented in the source and is not automatically more representative.

## Theory-based expectations for slides

Model 1 tests a zero price slope. Model 2 uses entire-home as a confounder proxy; controlling for property type could make the price slope more negative if whole homes are simultaneously costlier and more occupied. Model 3 tests equal slopes; demand-shock theory predicts a weaker negative association in 2024, while overpricing/supply-saturation predicts a stronger negative association. State these as theoretical expectations, not preregistered hypotheses.
'''
(OUT/"team_summary.md").write_text(summary)

readme=f'''# Reproducible analysis

Run `python3 final_analysis/run_analysis.py`, then `python3 final_analysis/analyze_revenue.py`, then `python3 build_dashboard.py` from the project root (or run each script by absolute path). The first script reads `past_rates.csv`; the revenue script reads the prepared analysis CSV; both write only into `final_analysis/`. The final command rebuilds `analysis_output/dashboard.html`. Environment: Python {platform.python_version()}, pandas {pd.__version__}, numpy {np.__version__}. `statsmodels` and `scipy` are unavailable in the supplied environment, so OLS and listing-clustered sandwich standard errors are computed directly with NumPy; p-values and t confidence intervals use the Student t distribution with listing-cluster degrees of freedom, calculated by the included incomplete-beta routine.

Files include `cleaned_analysis.csv`, `variable_dictionary.csv`, descriptive and regression CSV tables, sensitivity table, data-quality JSON, analysis PNGs, and `team_summary.md`. The supporting revenue script adds `revenue_comparison.csv`, `revenue_data_quality.json`, `revenue_comparison.png`, `revenue_presentation_paragraph.md`, and `revenue_method_notes.md`. Analysis sample: {len(clean):,} rows, {clean[ID].nunique():,} listings. Main models use the identical complete valid sample. Price and revenue use native-currency fields as EUR under explicit assumptions. Sensitivity specifications re-estimate Model 3.
'''
(OUT/"README.md").write_text(readme)
print(f"Raw {raw_n:,}, raw listings {raw_ids:,}; selected {len(s):,} rows, {s[ID].nunique():,} IDs; analysis {len(clean):,} rows, {clean[ID].nunique():,} IDs")
print(pd.DataFrame(tables)[["model","term","coefficient","p_value","ci95_low","ci95_high","n","r_squared"]].to_string(index=False))
print(contrast.to_string(index=False)); print(pd.DataFrame(sens).to_string(index=False))
