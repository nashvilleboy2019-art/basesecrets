"""
Prend les screenshots de toutes les pages cles pour la documentation.
Prerequis : python demo_populate.py doit avoir ete lance avant.
Usage     : python demo_screenshots.py
Sortie    : dossier screenshots/
"""
import os, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT  = "screenshots"
os.makedirs(OUT, exist_ok=True)


def find_secret_id(page, id_secret):
    """Trouve l'ID BD d'un secret par son id_secret via la recherche."""
    page.goto(f"{BASE}/secrets?q={id_secret}", wait_until="networkidle")
    link = page.query_selector("table tbody tr:first-child td:first-child a")
    if link:
        href = link.get_attribute("href")
        return href.split("/")[-1]
    return None


def find_audit_id(page, name_fragment):
    """Trouve l'ID BD d'une session d'audit."""
    page.goto(f"{BASE}/audit", wait_until="networkidle")
    rows = page.query_selector_all("table tbody tr")
    for row in rows:
        text = row.inner_text()
        if name_fragment in text:
            link = row.query_selector("a")
            if link:
                href = link.get_attribute("href")
                return href.split("/")[2]  # /audit/{id}  ou /audit/{id}/report
    return None


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Screenshot login sans session ---
        ctx_anon = browser.new_context(viewport={"width": 1440, "height": 900})
        page_anon = ctx_anon.new_page()
        page_anon.goto(f"{BASE}/login", wait_until="networkidle")
        time.sleep(0.4)
        page_anon.screenshot(path=os.path.join(OUT, "01_login.png"))
        print("  OK  01_login.png  —  Page de connexion")
        ctx_anon.close()

        # --- Session authentifiee ---
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        page.goto(f"{BASE}/login")
        page.fill("input[name=username]", "admin")
        page.fill("input[name=password]", "noukie2017")
        page.click("button[type=submit]")
        page.wait_for_url(f"{BASE}/")
        time.sleep(0.5)

        # Trouver les bons IDs dans les donnees demo
        secret_id  = find_secret_id(page, "AD_ADMIN_DA") or find_secret_id(page, "SQL_SA_PROD")
        secret_archived_id = find_secret_id(page, "OLD_PROXY_ADMIN")

        page.goto(f"{BASE}/audit", wait_until="networkidle")
        audit_rows = page.query_selector_all("table tbody tr")
        audit_closed_id = None
        audit_open_id   = None
        for row in audit_rows:
            text = row.inner_text()
            link = row.query_selector("a")
            if not link:
                continue
            href = link.get_attribute("href")
            if "Coffre 1" in text and audit_closed_id is None:
                audit_closed_id = href.split("/")[2]
            if "Coffre 2" in text and audit_open_id is None:
                audit_open_id = href.split("/")[2]

        pages = [
            ("02_dashboard",        f"{BASE}/",                                     "Tableau de bord",              False),
            ("03_secrets_list",     f"{BASE}/secrets",                              "Liste des secrets",            False),
            ("04_secret_detail",    f"{BASE}/secrets/{secret_id}",                  "Fiche d'un secret",            False),
            ("05_secret_history",   f"{BASE}/secrets/{secret_id}",                  "Historique (scroll bas)",      True),
            ("06_secret_new",       f"{BASE}/secrets/new",                          "Formulaire nouveau secret",    False),
            ("07_secrets_archived", f"{BASE}/secrets?archived=1",                   "Secrets archives",             False),
            ("08_audit_list",       f"{BASE}/audit",                                "Liste des sessions d'audit",   False),
            ("09_audit_session",    f"{BASE}/audit/{audit_open_id}",                "Session audit en cours",       False),
            ("10_audit_report",     f"{BASE}/audit/{audit_closed_id}/report",       "Rapport audit cloture",        False),
            ("11_audit_new",        f"{BASE}/audit/new",                            "Nouvelle session d'audit",     False),
            ("12_activity",         f"{BASE}/activity",                             "Journal d'activite",           False),
            ("13_users",            f"{BASE}/users/",                               "Gestion des comptes",          False),
            ("14_settings_general", f"{BASE}/settings/",                            "Parametres generaux",          False),
            ("15_settings_theme",   f"{BASE}/settings/?tab=theme",                  "Parametres theme",             False),
            ("16_settings_ldap",    f"{BASE}/settings/?tab=ldap",                   "Parametres Active Directory",  False),
            ("17_settings_danger",  f"{BASE}/settings/?tab=danger",                 "Zone dangereuse",              False),
            ("18_import",           f"{BASE}/secrets/import",                       "Import CSV/Excel",             False),
            ("19_guide",            f"{BASE}/guide",                                "Guide d'utilisation",          False),
        ]

        for filename, url, label, scroll_bottom in pages:
            try:
                page.goto(url, wait_until="networkidle")
                time.sleep(0.4)
                if scroll_bottom:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(0.3)
                full = filename in ("19_guide",)
                page.screenshot(path=os.path.join(OUT, f"{filename}.png"), full_page=full)
                print(f"  OK  {filename}.png  —  {label}")
            except Exception as e:
                print(f"  ERR {filename}.png  —  {label} : {e}")

        ctx.close()
        browser.close()

    print(f"\n  {len(pages) + 1} screenshots dans le dossier '{OUT}/'")


if __name__ == "__main__":
    run()
