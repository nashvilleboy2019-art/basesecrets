# BaseSecrets

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/licence-MIT-green)

Portail de gestion des secrets d'entreprise (mots de passe, clés d'API, certificats…) stockés dans des enveloppes scellées en coffre-fort.

Déploiement local Windows ou Docker, aucune dépendance cloud.

---

## Fonctionnalités

- **Registre des secrets** — référentiel centralisé avec recherche full-text (libellé, identifiant, nom technique, numéro d'enveloppe actuel et anciens numéros)
- **Archivage** — désactiver un secret obsolète sans perdre la traçabilité ; les archivés sont masqués par défaut et exclus des audits
- **Import CSV / Excel** — import en masse depuis un fichier `.csv` ou `.xlsx` avec rapport détaillé (importés / doublons / erreurs)
- **Changement d'enveloppe** — flux dédié avec traçabilité complète : ancien numéro, nouveau numéro, opérateur, date, note optionnelle
- **Audit annuel par coffre** — session de scan en temps réel avec douchette USB ; périmètre limité à un coffre précis ; rapport de conformité imprimable (manquants filtrés par coffre, archivés exclus)
- **Journal d'activité** — toutes les actions tracées (connexions, modifications, audits, imports, archivages)
- **Gestion des comptes** — création, modification, suppression avec protection du dernier responsable
- **SSO Active Directory** — authentification LDAP avec restriction par OU et/ou groupe AD ; fallback local ; création automatique des comptes
- **Thème couleurs** — personnalisation de la couleur principale (sidebar) et secondaire (boutons/accents) depuis les paramètres
- **Logo société** — personnalisation de la page de connexion
- **Guide intégré** — accessible sur `/guide` sans authentification

## Rôles

| Action | Auditeur | Responsable |
|---|:---:|:---:|
| Consulter les secrets | ✓ | ✓ |
| Rechercher | ✓ | ✓ |
| Audit annuel + impression rapport | ✓ | ✓ |
| Journal d'activité | ✓ | ✓ |
| Créer / modifier un secret | — | ✓ |
| Archiver / désarchiver un secret | — | ✓ |
| Importer CSV / Excel | — | ✓ |
| Changer un numéro d'enveloppe | — | ✓ |
| Gérer les comptes | — | ✓ |
| Paramètres (logo, thème, SSO AD) | — | ✓ |

## Stack technique

- **Backend** : Python 3.10+ · FastAPI · SQLAlchemy 2 · SQLite
- **Frontend** : Jinja2 · Tailwind CSS (CDN) · Alpine.js v3
- **Auth** : sessions Starlette · bcrypt · ldap3 (SSO AD optionnel)
- **Import** : csv (stdlib) · openpyxl (Excel)

## Installation

### Mode classique (Windows / Linux)

**Prérequis** : Python 3.10 ou supérieur, avec `pip` dans le PATH.

```bash
pip install -r requirements.txt
python run.py
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Mode Docker

```bash
docker compose up --build -d
```

L'application écoute sur le port `8000`. Les données sont persistées dans des volumes Docker nommés (`basesecrets_data`, `basesecrets_uploads`).

Pour exposer sur le réseau local, modifier le port dans `docker-compose.yml` :
```yaml
ports:
  - "80:8000"
```

## Comptes par défaut

À changer après la première connexion.

| Compte | Mot de passe | Rôle |
|---|---|---|
| `admin` | `noukie2017` | responsable |
| `auditeur` | `audit123` | auditeur |

## Structure

```
basesecrets/
├── run.py                    # point d'entrée
├── requirements.txt
├── install.txt               # guide d'installation simplifié
├── Dockerfile
├── docker-compose.yml
├── app/
│   ├── main.py
│   ├── models.py             # Secret, SecretHistory, AuditSession, User…
│   ├── auth.py               # bcrypt + LDAP
│   ├── settings_manager.py   # lecture/écriture data/settings.json
│   ├── utils.py
│   ├── routers/
│   │   ├── secrets.py        # CRUD + import CSV/Excel
│   │   ├── audit.py
│   │   ├── activity.py
│   │   ├── users.py
│   │   └── settings.py       # logo, LDAP
│   └── templates/
│       ├── settings/
│       └── secrets/import.html
├── data/                     # secrets.db + settings.json (générés)
└── uploads/                  # scans enveloppes + logo société
```

## Douchette USB

La douchette fonctionne en mode clavier : aucun pilote requis. Elle tape le numéro d'enveloppe puis envoie `Entrée`. Les pages d'audit, de création de secret et de changement d'enveloppe focalisent automatiquement le champ de saisie.

## Archivage des secrets

Un secret archivé conserve toute sa traçabilité (historique, audits passés) mais n'apparaît plus dans l'inventaire actif ni dans les "manquants" d'un audit futur. Un bouton **Désarchiver** permet de le réactiver. L'accès aux archivés reste possible via le filtre "Afficher les archivés" dans la liste.

## Thème couleurs

Depuis **Paramètres → Thème**, les responsables peuvent personnaliser :
- **Couleur principale** — fond de la sidebar et de la page de connexion (défaut : bleu nuit `#0f172a`)
- **Couleur secondaire** — boutons d'action et élément de navigation actif (défaut : indigo `#4f46e5`)

## Licence

Distribué sous licence [MIT](LICENSE) — libre d'utilisation, de modification et de redistribution.
