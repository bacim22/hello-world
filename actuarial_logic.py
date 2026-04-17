import pandas as pd
import numpy as np
import chainladder as chain_cl
from typing import Dict, Any, Tuple, List

def assess_quality(df: pd.DataFrame) -> Dict[str, Any]:
    issues = []
    numeric_df = df.select_dtypes(include=[np.number])
    negatives = (numeric_df < 0).sum().sum()
    if negatives > 0:
        issues.append(f"Found {negatives} negative values.")
    for col in numeric_df.columns:
        mean = numeric_df[col].mean()
        std = numeric_df[col].std()
        if std > 0:
            outliers = ((numeric_df[col] - mean).abs() > 3 * std).sum()
            if outliers > 0:
                issues.append(f"Column '{col}' has {outliers} outliers (>3σ).")
    missing_pct = df.isnull().mean().mean() * 100
    if missing_pct > 5:
        issues.append(f"Missing data is {missing_pct:.2f}%, which exceeds 5%.")
    base_score = 100 - (len(issues) * 10)
    if missing_pct > 5: base_score -= 20
    score = max(0, min(100, base_score))
    return {"score": score, "issues": issues, "status": "PASS" if score >= 60 else "FAIL"}

def create_cl_triangle(df: pd.DataFrame, origin: str, dev: str, value: str, cumulative: bool, origin_type: str = 'AY', dev_unit: str = 'month') -> chain_cl.Triangle:
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[origin]):
        df[origin] = pd.to_datetime(df[origin])
    if pd.api.types.is_numeric_dtype(df[dev]):
        if dev_unit == 'year':
            df[dev] = df.apply(lambda row: row[origin] + pd.DateOffset(months=int(row[dev])*12), axis=1)
        elif dev_unit == 'quarter':
            df[dev] = df.apply(lambda row: row[origin] + pd.DateOffset(months=int(row[dev])*3), axis=1)
        else: # month
            df[dev] = df.apply(lambda row: row[origin] + pd.DateOffset(months=int(row[dev])), axis=1)
    return chain_cl.Triangle(df, origin=origin, development=dev, columns=[value], cumulative=cumulative)

def run_diagnostics(triangle: chain_cl.Triangle) -> Dict[str, Any]:
    # 1. Calendar Year Effects: threshold > 20% deviation in recent vs older diagonals
    # We can calculate the link ratio mean of the latest diagonal vs the rest
    lrs = triangle.link_ratio
    latest_diag = np.nanmean(np.diagonal(lrs.values[0,0,::-1,:], offset=-1)) # Simplified diagonal extraction
    # Actually, let's just use chainladder's latest_diagonal on link_ratio
    latest_lrs = lrs.latest_diagonal.values
    older_lrs_mean = np.nanmean(lrs.values)
    latest_lrs_mean = np.nanmean(latest_lrs)

    cal_effect_detected = False
    if older_lrs_mean != 0:
        deviation = abs(latest_lrs_mean - older_lrs_mean) / older_lrs_mean
        if deviation > 0.20:
            cal_effect_detected = True

    # 2. Development Pattern Stability: CV > 30% per period
    cvs = lrs.std() / lrs.mean()
    unstable_periods = np.nansum(cvs.values > 0.30)

    is_unstable = unstable_periods > 0 or cal_effect_detected

    return {
        "calendar_year_effect": "Detected (>20% deviation)" if cal_effect_detected else "Low",
        "stability_cv": cvs.to_frame().to_dict() if hasattr(cvs, 'to_frame') else str(cvs),
        "recommendation": "Chain-Ladder" if not is_unstable else "Bornhuetter-Ferguson / Cape Cod",
        "status": "Pass" if not is_unstable else "Fail"
    }

def select_loss_development_factors(triangle: chain_cl.Triangle, method: str) -> chain_cl.Development:
    avg = method if method in ['volume', 'simple'] else 'volume'
    return chain_cl.Development(average=avg).fit(triangle)

def fit_tail(triangle: chain_cl.Triangle, method: str) -> chain_cl.TailCurve:
    curve = method if method in ["inverse_power", "weibull", "exponential"] else "inverse_power"
    return chain_cl.TailCurve(curve=curve).fit(triangle)

def run_ibnr(triangle: chain_cl.Triangle, methods: List[str], apriori: float = None, premium: pd.Series = None) -> Dict[str, Any]:
    results = {}
    if "cl" in methods:
        cl_model = chain_cl.Chainladder().fit(triangle)
        results["cl"] = {"ibnr": cl_model.ibnr_.sum().sum(), "ultimate": cl_model.ultimate_.sum().sum()}
    if "bf" in methods:
        if apriori is None: raise ValueError("A priori loss ratio required for BF.")
        bf_model = chain_cl.BornhuetterFerguson(apriori=apriori).fit(triangle, sample_weight=premium)
        results["bf"] = {"ibnr": bf_model.ibnr_.sum().sum(), "ultimate": bf_model.ultimate_.sum().sum()}
    if "mack" in methods:
        mack_model = chain_cl.MackChainladder().fit(triangle)
        results["mack"] = {
            "ibnr": mack_model.ibnr_.sum().sum(),
            "ultimate": mack_model.ultimate_.sum().sum(),
            "std_error": mack_model.total_mack_std_err_.sum().sum()
        }
    ibnrs = [v["ibnr"] for v in results.values() if "ibnr" in v]
    if ibnrs:
        results["central_estimate"] = sum(ibnrs) / len(ibnrs)
        results["range"] = [min(ibnrs), max(ibnrs)]
    return results

def quantify_uncertainty(triangle: chain_cl.Triangle, confidence_intervals: List[float]) -> Dict[str, Any]:
    from scipy.stats import norm
    mack = chain_cl.MackChainladder().fit(triangle)
    ibnr = mack.ibnr_.sum().sum()
    std_err = mack.total_mack_std_err_.sum().sum()
    cv = std_err / ibnr if ibnr != 0 else 0

    ci_results = {}
    for ci in confidence_intervals:
        z = norm.ppf(ci)
        ci_results[f"{ci*100:.0f}%"] = ibnr + z * std_err

    return {
        "ibnr": ibnr,
        "std_err": std_err,
        "cv": cv,
        "cv_classification": "Low" if cv < 0.1 else "Moderate" if cv < 0.25 else "High",
        "confidence_intervals": ci_results
    }
