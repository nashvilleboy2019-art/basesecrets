import json, os

_PATH = os.path.join("data", "settings.json")

_DEFAULTS = {
    "company_name": "",
    "logo_ext": "",
    "primary_color": "#0f172a",
    "secondary_color": "#4f46e5",
    "ldap_enabled": False,
    "ldap_server": "",
    "ldap_port": 389,
    "ldap_user_template": "{username}@domain.local",
    "ldap_default_role": "auditeur",
    "ldap_bind_dn": "",
    "ldap_bind_password": "",
    "ldap_allowed_ou": "",
    "ldap_required_group": "",
}


def load() -> dict:
    if not os.path.exists(_PATH):
        return dict(_DEFAULTS)
    try:
        with open(_PATH, encoding="utf-8") as f:
            return {**_DEFAULTS, **json.load(f)}
    except Exception:
        return dict(_DEFAULTS)


def save(updates: dict):
    os.makedirs("data", exist_ok=True)
    data = load()
    data.update(updates)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
