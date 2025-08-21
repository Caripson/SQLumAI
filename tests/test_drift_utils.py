from scripts.drift_utils import compute_null_drift


def test_compute_null_drift_thresholding():
    prev = {"dbo.T.Email": {"count": 100, "nulls": 5}}
    curr = {"dbo.T.Email": {"count": 100, "nulls": 25}}
    drifts = compute_null_drift(prev, curr, threshold=0.1)
    assert drifts and drifts[0][0] == "dbo.T.Email" and 0.19 < drifts[0][1] < 0.21

