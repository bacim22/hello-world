import pandas as pd
import actuarial_logic
import chainladder as chain_cl
import numpy as np

def test_data_quality():
    df = pd.DataFrame({"losses": [100, 100, 100, 100, 100, 100, 100, 100, 100, -50, 1000000]})
    results = actuarial_logic.assess_quality(df)
    assert results["score"] < 100
    assert any("negative" in issue for issue in results["issues"])
    assert any("outliers" in issue for issue in results["issues"])
    print("Data quality assessment test passed.")

def test_triangle_construction():
    df = pd.DataFrame({
        'AY': ['2017-01-01', '2017-01-01', '2018-01-01', '2018-01-01'],
        'dev': [12, 24, 12, 24],
        'loss': [100, 150, 120, 170]
    })
    tri = actuarial_logic.create_cl_triangle(df, 'AY', 'dev', 'loss', True, dev_unit='month')
    assert isinstance(tri, chain_cl.Triangle)
    assert np.nanmax(tri.values) == 170
    print("Triangle construction test passed.")
    return tri

def test_diagnostics_and_ldf(tri):
    diag = actuarial_logic.run_diagnostics(tri)
    assert "recommendation" in diag
    print("Diagnostics test passed.")
    ldf = actuarial_logic.select_loss_development_factors(tri, "volume")
    assert isinstance(ldf, chain_cl.Development)
    print("LDF selection test passed.")

def test_tail_and_ibnr(tri):
    tail = actuarial_logic.fit_tail(tri, "inverse_power")
    assert isinstance(tail, chain_cl.TailCurve)
    print("Tail fitting test passed.")
    ibnr_results = actuarial_logic.run_ibnr(tri, ["cl", "mack"])
    assert "cl" in ibnr_results
    assert "mack" in ibnr_results
    print("IBNR modeling test passed.")

def test_uncertainty(tri):
    unc = actuarial_logic.quantify_uncertainty(tri, [0.75, 0.95])
    assert "cv" in unc
    assert "95%" in unc["confidence_intervals"]
    print("Uncertainty quantification test passed.")

if __name__ == "__main__":
    test_data_quality()
    tri = test_triangle_construction()
    test_diagnostics_and_ldf(tri)
    test_tail_and_ibnr(tri)
    test_uncertainty(tri)
