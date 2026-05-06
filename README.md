# BaseSecrets

Portail de gestion des secrets d'entreprise (mots de passe, clés d'API, certificats…) stockés dans des enveloppes scellées en coffre-fort.

Remplace une base Access obsolète. Déploiement local Windows, aucune dépendance cloud.

---

## Fonctionnalités

- **Registre des secrets** — référentiel centralisé avec recherche full-text (libellé, identifiant, nom technique, numéro d'enveloppe actuel et anciens numéros)
- **Changement d'enveloppe** — flux dédié avec traçabilité complète : ancien numéro, nouveau numéro, opérateur, date, note optionnelle
- **Audit annuel** — session de scan en temps réel avec une douchette USB code-barres ; rapport de conformité (enveloppes conformes / inconnues / non scannées)
- **Journal d'activité** — toutes les actions tracées (connexions, modifications, audits)
- **Gestion des comptes** — création, modification, suppression avec protection du dernier responsable
- **Guide intégré** — accessible sur `/guide` sans authentification

## Rôles

| Action | Auditeur | Responsable |
|---|:---:|:---:|
| Consulter les secrets | ✓ | ✓ |
| Rechercher | ✓ | ✓ |
| Audit annuel | ✓ | ✓ |
| Journal d'activité | ✓ | ✓ |
| Créer / modifier un secret | — | ✓ |
| Changer un numéro d'enveloppe | — | ✓ |
| Gérer les comptes | — | ✓ |

## Stack technique

- **Backend** : Python 3.10+ · FastAPI · SQLAlchemy 2 · SQLite
- **Frontend** : Jinja2 · Tailwind CSS (CDN) · Alpine.js v3
- **Auth** : sessions Starlette · bcrypt

## Installation

**Prérequis** : Python 3.10 ou supérieur, avec `pip` dans le PATH.

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer l'application
python run.py
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000)

Comptes par défaut (à changer après la première connexion) :

| Compte | Mot de passe | Rôle |
|---|---|---|
| `admin` | `noukie2017` | responsable |
| `auditeur` | `audit123` | auditeur |

## Structure

```
basesecrets/
├── run.py                  # point d'entrée
├── requirements.txt
├── install.txt             # guide d'installation simplifié
├── app/
│   ├── main.py
│   ├── models.py           # Secret, SecretHistory, AuditSession, User…
│   ├── auth.py
│   ├── utils.py
│   ├── routers/
│   │   ├── secrets.py
│   │   ├── audit.py
│   │   ├── activity.py
│   │   └── users.py
│   └── templates/
├── data/                   # secrets.db — généré au premier lancement
└── uploads/scans/          # images des enveloppes
```

## Douchette USB

La douchette fonctionne en mode clavier : aucun pilote requis. Elle tape le numéro d'enveloppe puis envoie `Entrée`. Les pages d'audit et de changement d'enveloppe focalisent automatiquement le champ de saisie.
