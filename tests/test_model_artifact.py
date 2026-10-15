from pathlib import Path


def test_legacy_notebook_path_resolves_to_single_serving_model():
    root = Path(__file__).resolve().parents[1]
    serving_model = root / "app/models/best_hgb_pipeline.pkl"
    notebook_model = root / "models/best_hgb_pipeline.pkl"
    assert serving_model.is_file()
    assert (root / "models").is_symlink()
    assert notebook_model.samefile(serving_model)
