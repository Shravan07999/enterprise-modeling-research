import re
import uuid
from xml.sax.saxutils import escape as _xml_escape


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"\s+", "_", name.strip())
    cleaned = re.sub(r"[^\w\-.]", "", cleaned)
    return cleaned or "model"


def xml_escape(text: str) -> str:
    return _xml_escape(str(text), entities={'"': "&quot;", "'": "&apos;"})


def adl_escape(text: str) -> str:
    return str(text).replace('"', '\\"')


def generate_uuid() -> str:
    return f"id-{uuid.uuid4()}"


def grid_position(index: int, cols: int = 3,
                  col_w: float = 7.0, row_h: float = 2.5,
                  margin_x: float = 1.0, margin_y: float = 1.0) -> tuple[float, float]:
    col = index % cols
    row = index // cols
    x = margin_x + col * col_w
    y = margin_y + row * row_h
    return (x, y)
