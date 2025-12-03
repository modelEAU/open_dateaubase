# datEAUbase

This repo contains the reference implementation of the dat*EAU*base relational database and data model for use in water resource recovery facilities (WRRFs). The purpose of dat*EAU*base is to allow WRRF data to be stored *along with their context* to ensure that they are correctly interpreted in data mining, modelling and decision support activities.

dat*EAU*base is published under the MIT license.


# datEAUbase – Metadata API

Cette API FastAPI sert de couche d’accès pour l’ingestion de valeurs dans la base de données `proposed_2025_11` (SQL Server dans Docker).  
Elle résout automatiquement le `Metadata_ID` à partir d’une combinaison d’IDs (equipment, parameter, unit, purpose, sampling_point, project) et de la date de mesure, puis insère la valeur dans la table `[value]`.

---

## 1. Prérequis

- **Docker** installé et fonctionnel
- **SQL Server** dans un conteneur Docker nommé `dateaubase-sql`
- **Python 3** installé
- Environnement virtuel avec les dépendances (dans `api_metadata/.venv`) :
  - `fastapi`
  - `uvicorn[standard]`
  - `pyodbc`
  - `python-dotenv`

Fichier `.env` dans `api_metadata/` :

```env
DB_SERVER=127.0.0.1,1433
DB_NAME=proposed_2025_11
DB_USER=SA
DB_PASSWORD=StrongPwd123!


# datEAUbase – Metadata API & UI

Petit prototype pour gérer les métadonnées et l’ingestion de valeurs dans **datEAUbase**.

---

## 1. Prérequis

- Docker Desktop (SQL Server dans un conteneur)
- Python 3.9+
- `sqlcmd` et `ODBC Driver 18` installés (pour tester la BD)

---

## 2. Démarrer SQL Server

Le projet suppose un conteneur SQL Server déjà créé, nommé par exemple `dateaubase-sql`.

```bash
# voir l’état
docker ps -a

# démarrer le conteneur
docker start dateaubase-sql

Dans le dossier api_metadata, créer un fichier .env :

DB_SERVER=127.0.0.1,1433
DB_NAME=proposed_2025_11
DB_USER=SA
DB_PASSWORD=StrongPwd123!

UI_ADMIN_PASSWORD=admin123
UI_USER_PASSWORD=user123

Installation des dépendances
cd open_dateaubase/api_metadata

python3 -m venv .venv
source .venv/bin/activate  # sous Windows: .venv\Scripts\activate

pip install fastapi "uvicorn[standard]" pyodbc python-dotenv streamlit pandas pytest httpx

Lancer l’API (FastAPI)

Depuis api_metadata avec le venv activé :

uvicorn main:app --reload --port 8000


Endpoints utiles :

Santé : http://127.0.0.1:8000/health

Docs interactives : http://127.0.0.1:8000/docs

Exemple d’appel /ingest :

curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": 1,
    "parameter_id": 1,
    "unit_id": 1,
    "purpose_id": 1,
    "sampling_point_id": 1,
    "project_id": 1,
    "value": 12.34,
    "timestamp": "2025-11-30T01:30:00"
  }'

6. Lancer l’interface UI (Streamlit)

Dans un deuxième terminal, toujours dans api_metadata avec le même venv :

streamlit run app.py


L’UI est accessible sur :
http://localhost:8501

Page Dashboard : KPIs + graphes sur les 30 derniers jours

Page Liste des métadonnées : lecture de la table metadata

Page Créer une métadonnée : formulaire complet qui crée/relie toutes les FKs.

7. Lancer les tests
cd open_dateaubase/api_metadata
source .venv/bin/activate

python -m pytest