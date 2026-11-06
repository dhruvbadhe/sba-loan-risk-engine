import base64
from io import BytesIO

from matplotlib.figure import Figure
from PIL import Image

from app.chart_rendering import figure_image_html


def test_chart_contains_its_own_image_without_a_media_request():
    figure = Figure(figsize=(4, 2))
    figure.subplots().plot([50, 90], [38000, 7600])
    html = figure_image_html(figure, 'Expected loss "chart"')
    encoded = html.split("base64,", 1)[1].split('"', 1)[0]
    with Image.open(BytesIO(base64.b64decode(encoded))) as image:
        assert image.format == "PNG"
        assert image.width > image.height > 0
        image.verify()
    assert 'alt="Expected loss &quot;chart&quot;"' in html
    assert "/media/" not in html


def test_prediction_embeds_both_charts(monkeypatch):
    from pathlib import Path
    from unittest.mock import Mock

    from streamlit.testing.v1 import AppTest

    result = {
        "probability_of_default": 0.3,
        "loss_given_default": 0.25,
        "exposure_at_default": 250000,
        "expected_loss": 18750,
        "risk_tier": "Tier 3",
        "underwriting_action": "Senior Review",
        "shap_base_value": 0.1,
        "shap_values": {"num__grossapproval": 0.2},
        "processed_features": {"num__grossapproval": 250000},
    }
    monkeypatch.setattr(
        "requests.post", Mock(return_value=Mock(status_code=200, json=lambda: result))
    )
    script = Path(__file__).resolve().parents[1] / "app/streamlit_app.py"
    dashboard = AppTest.from_file(str(script))
    dashboard.session_state["access_token"] = "test-only-token"
    dashboard.run(timeout=15)
    next(button for button in dashboard.button if button.label == "ASSESS RISK").click()
    dashboard.run(timeout=15)
    assert not dashboard.exception
    assert not dashboard.error
    charts = [
        item.value
        for item in dashboard.markdown
        if "data:image/png;base64," in item.value
    ]
    assert len(charts) == 2
    assert any("Expected loss versus" in chart for chart in charts)
    assert any("SHAP feature" in chart for chart in charts)
