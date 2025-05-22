import utils


def test_lambert93_to_wsg84():
    lon, lat = 102980, 6847973
    res = utils.lambert93_to_wsg84(lon, lat)

    assert isinstance(res, tuple)
    assert res == (-5.0888561153013425, 48.456574558829914)  # Known conversion


def test_load_operator_coverage_cache(monkeypatch, tmp_path):
    # Patch paths and pandas.read_csv to avoid file IO
    import pandas as pd

    dummy_row: dict[str, str] = {
        "Operateur": "20801",
        "x": "102980",
        "y": "6847973",
        "2G": "1",
        "3G": "1",
        "4G": "0",
    }

    monkeypatch.setattr(utils, "CSV_PATH", "dummy.csv")
    monkeypatch.setattr(utils, "CACHE_FILE_PATH", str(tmp_path / "cache.json"))
    monkeypatch.setattr(pd, "read_csv", lambda fp, **kw: pd.DataFrame([dummy_row]))

    network_coverage_by_operator = utils.load_operator_to_network_coverage_cache()
    assert "20801" in network_coverage_by_operator
    assert isinstance(network_coverage_by_operator["20801"], list)
    assert len(network_coverage_by_operator["20801"]) == 1

    first_entry = network_coverage_by_operator["20801"][0]

    network_coverage = first_entry["coverage"]
    assert network_coverage["2G"] is True
    assert network_coverage["3G"] is True
    assert network_coverage["4G"] is False

    lambert93_coords = first_entry["csv_coords_lambert93"]
    assert lambert93_coords["lon"] == 102980
    assert lambert93_coords["lat"] == 6847973
