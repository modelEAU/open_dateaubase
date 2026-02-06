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

## datEAUbase

Reference implementation of the dat*EAU*base relational model for water resource recovery facilities (WRRFs). The goal is to store WRRF data **with full context** so downstream mining, modelling, and decision-support steps interpret measurements correctly. Licensed under MIT.

## Metadata API (overview)

FastAPI service targeting the `proposed_2025_11` SQL Server database (runs in Docker). It resolves `Metadata_ID` from domain identifiers (equipment, parameter, unit, purpose, sampling_point, project) plus measurement date, then inserts values into `[value]`.

## Local stack (Docker Compose)

Everything runs in containers: SQL Server, FastAPI backend, Streamlit frontend. No local Python or SQL Server install required.

### 1) Prerequisites
- Docker Desktop
- Git

### 2) Clone the repo
```bash
git clone <REPO_URL>
cd open_dateaubase
```

### 3) Create env file
```bash
cp .env.docker.example .env.docker
```

### 4) (Optional) Tweak `.env.docker`
Defaults work out of the box. Example values:
```env
DB_HOST=db
DB_PORT=1433
DB_NAME=proposed_2025_11
DB_USER=SA
DB_PASSWORD=StrongPwd123!
```

### 5) Start the stack
```bash
docker compose up --build
```
This boots SQL Server, runs `init.sql`, then starts FastAPI and Streamlit.

### 6) Access
- FastAPI docs: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501
- SQL Server: localhost:14330

### 7) Verify database (optional)
```bash
sqlcmd -S localhost,14330 -U sa -P 'StrongPwd123!' -C \
  -Q "SELECT name FROM sys.databases;"
```
Expected: `proposed_2025_11`.

### 8) Stop everything
```bash
docker compose down
```
