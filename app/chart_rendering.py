"""Embed charts in the page so they do not depend on instance-local media files."""

import base64
from html import escape
from io import BytesIO


def figure_image_html(figure, description: str) -> str:
    image = BytesIO()
    figure.savefig(image, format="png", dpi=150, bbox_inches="tight")
    encoded = base64.b64encode(image.getvalue()).decode("ascii")
    return (
        f'<img src="data:image/png;base64,{encoded}" '
        f'alt="{escape(description, quote=True)}" '
        'style="width:100%;height:auto;display:block;" />'
    )
