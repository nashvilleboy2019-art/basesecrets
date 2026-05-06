from fastapi.templating import Jinja2Templates
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def _get_logo_url() -> str | None:
    for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
        if os.path.exists(os.path.join("uploads", f"logo_custom{ext}")):
            return f"/uploads/logo_custom{ext}"
    return None


def _get_theme_style() -> str:
    from app import settings_manager
    cfg = settings_manager.load()
    primary = cfg.get("primary_color", "#0f172a")
    secondary = cfg.get("secondary_color", "#4f46e5")
    return (
        "<style>"
        f":root{{--color-sidebar:{primary};--color-accent:{secondary};}}"
        ".nav-item-active{color:#fff!important;border-bottom:3px solid var(--color-accent)!important;}"
        ".btn-accent{background-color:var(--color-accent)!important;color:#fff!important;transition:filter .15s;}"
        ".btn-accent:hover{filter:brightness(0.85);}"
        "</style>"
    )


templates.env.globals["get_logo_url"] = _get_logo_url
templates.env.globals["get_theme_style"] = _get_theme_style
