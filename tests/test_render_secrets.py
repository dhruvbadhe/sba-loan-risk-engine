from pathlib import Path


def test_supabase_key_is_supplied_outside_blueprint():
    blueprint = (Path(__file__).resolve().parents[1] / "render.yaml").read_text()
    lines = blueprint.splitlines()
    index = next(i for i, line in enumerate(lines) if line.strip() == "- key: SUPABASE_KEY")
    # Compare a boolean so pytest never displays the previous credential.
    assert bool(lines[index + 1].strip() == "sync: false"), "Key must be supplied in Render"
