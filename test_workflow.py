import pandas as pd
import actuarial_logic
import chainladder as chain_cl
import numpy as np

def test_full_workflow():
    # 1. Mock Triangle
    df = pd.DataFrame({
        'AY': ['2017-01-01', '2017-01-01', '2017-01-01', '2018-01-01', '2018-01-01', '2019-01-01'],
        'dev': [12, 24, 36, 12, 24, 12],
        'loss': [100, 150, 180, 120, 170, 130]
    })
    tri = actuarial_logic.create_cl_triangle(df, 'AY', 'dev', 'loss', True)

    # 2. IBNR
    ibnr_res = actuarial_logic.run_ibnr(tri, ["cl", "mack"])
    assert "cl" in ibnr_res

    # 3. Uncertainty
    unc_res = actuarial_logic.quantify_uncertainty(tri, [0.75, 0.95])
    assert "std_err" in unc_res

    print("Full actuarial workflow test passed.")

if __name__ == "__main__":
    test_full_workflow()
