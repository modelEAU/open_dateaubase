# datEAUbase

This repo contains the reference implementation of the dat*EAU*base relational database and data model for use in water resource recovery facilities (WRRFs). The purpose of dat*EAU*base is to allow WRRF data to be stored *along with their context* to ensure that they are correctly interpreted in data mining, modelling and decision support activities.

dat*EAU*base is published under the MIT license.


# datEAUbase – Metadata API

Cette API FastAPI sert de couche d’accès pour l’ingestion de valeurs dans la base de données `proposed_2025_11` (SQL Server dans Docker).  
Elle résout automatiquement le `Metadata_ID` à partir d’une combinaison d’IDs (equipment, parameter, unit, purpose, sampling_point, project) et de la date de mesure, puis insère la valeur dans la table `[value]`.

---

# datEAUbase – Metadata API (Local Setup)

Cette application est une **API FastAPI** permettant :
- de résoudre un `Metadata_ID` à partir d’identifiants métiers,
- d’insérer des valeurs dans la base **datEAUbase (SQL Server)**,
- d’exposer des endpoints REST pour ingestion et consultation.

Ce README explique **pas à pas** comment lancer l’application **en local**.

---

## Prérequis

Avant de commencer, assure-toi d’avoir :

- Python ≥ 3.9
- Git
- SQL Server en cours d’exécution (local ou distant)
- Accès à une base datEAUbase existante

---

## 1️⃣ Cloner le dépôt

```bash
git clone https://github.com/modelEAU/open_dateaubase.git
cd open_dateaubase
```

---

## 2️⃣ Créer un environnement virtuel 

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
```

---

## 3️⃣ Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4️⃣ Créer le fichier `.env.local`

Ce fichier est utilisé **uniquement en local**.

À la racine du projet, créer le fichier `.env.local` :

```env
DB_HOST=127.0.0.1
DB_PORT=1433
DB_NAME=proposed_2025_11
DB_USER=SA
DB_PASSWORD=StrongPwd123!
```

⚠️ Important :
- `127.0.0.1` doit être utilisé en local
- Ne pas versionner ce fichier

---

## 5️⃣ Vérifier la connexion à la base (optionnel)

```bash
python api_metadata/db.py
```

Sortie attendue :
```text
DB connection OK
```

---

## 6️⃣ Lancer l’application

```bash
python3 -m uvicorn api_metadata.main:app --reload
```

L’API est disponible sur :
```
http://127.0.0.1:8000
```

---

## 7️⃣ Tester l’API

### Health check
```
http://127.0.0.1:8000/health
```

Réponse attendue :
```json
{
  "status": "ok",
  "db": "connected"
}
```

### Documentation interactive
```
http://127.0.0.1:8000/docs
```

---

## Notes importantes

- `.env.local` → exécution locale
- `.env` → réservé à Docker
- Les imports utilisent des imports relatifs (`from .db import ...`)

---

## Prêt à l’emploi

Si `/health` et `/docs` fonctionnent, l’application est correctement lancée !

Pour lancer streamlit: 

python3 -m streamlit run api_metadata/app.py
