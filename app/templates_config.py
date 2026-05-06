from fastapi.templating import Jinja2Templates
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def _get_logo_url() -> str | None:
    for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
        if os.path.exists(os.path.join("uploads", f"logo_custom{ext}")):
            return f"/uploads/logo_custom{ext}"
    return None


templates.env.globals["get_logo_url"] = _get_logo_url
