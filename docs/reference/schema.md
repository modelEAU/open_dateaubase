Schema generation not yet implemented!


# 📘 datEAUbase Schema Documentation (AS-IS 2025)

> **Version :** 2025-09-12  
> **Auteur :** Lala (documentation interne – datEAUbase)  
> **Source :** Schéma Lucidchart “datEAUbase_AS-IS_2025.pdf”  
> **Contexte :** Base de données centrale du SI pilEAUte / datEAUbase, interconnectée avec FactoryTalk, API Python et MQTT pour la gestion, l’ingestion et la validation de données hydrologiques, environnementales et opérationnelles.

---

## 1. Conventions et domaines fonctionnels

| Couleur | Domaine | Description |
|----------|----------|-------------|
| 🟩 Vert | **Géospatiale et environnement** | Sites, bassins versants, caractéristiques urbaines et hydrologiques |
| 🟧 Orange | **Métadonnées et valeurs** | Données scientifiques et de mesure |
| 🟪 Rose | **Instrumentation & procédures** | Équipements, modèles, paramètres et procédures associées |
| 🟨 Jaune | **Projets & liaisons** | Relations projet-équipement-contact-points |
| 🟦 Bleu | **Référentiels de support** | Unités, statuts, types, sources et opérations |
| ⚙️ Gris | **Systèmes & contrôle** | Boucles de régulation, synchronisation, historisation |

---

## 2. Structure générale et dépendances

```text
value ─┬──▶ metadata ─┬──▶ parameter
        │              ├──▶ equipment
        │              ├──▶ project
        │              ├──▶ sampling_points ─▶ site ─▶ watershed
        │              ├──▶ purpose
        │              ├──▶ condition (weather_condition)
        │              └──▶ contact
        │
        └──▶ comment
```

Relations secondaires :
- `equipment_model` ←→ `parameter` via `equipment_model_has_specification`
- `equipment_model` ←→ `procedures` via `equipment_model_has_procedures`
- `parameter` ←→ `procedures` via `parameter_has_procedures`
- `project` ←→ (`equipment`, `contact`, `sampling_points`) via tables d’association
- `source`, `operations`, `type_data`, `status` : nouveaux référentiels pour ingestion et contrôle qualité
- `control_loop` : lie `measurement`, `controller` et `actuator`

---

##  3. Détail des domaines

### 3.1 Métadonnées et valeurs

| Table | Description | Clés | Relations |
|-------|--------------|------|------------|
| **value** | Données brutes et validées (mesures, résultats d’expériences, etc.) | `Value_ID (PK)` | `Metadata_ID → metadata`, `Comment_ID → comments` |
| **metadata** | Contexte complet d’une valeur : paramètre, unité, site, équipement, projet, condition météo, etc. | `Metadata_ID (PK)` | FK vers `parameter`, `unit`, `equipment`, `contact`, `project`, `sampling_points`, `weather_condition`, `purpose`, `type_data`, `source`, `status` |
| **purpose** | Objectif de la donnée (ex. suivi, calibration, simulation) | `Purpose_ID (PK)` | 1-N avec `metadata` |
| **unit** | Référentiel d’unités (mg/L, m³/s, °C…) | `Unit_ID (PK)` | Référencée par `parameter`, `metadata`, `equipment_model_has_specification` |
| **comments** | Notes descriptives ou remarques sur une valeur | `Comment_ID (PK)` | 1-N avec `value` |
| **status** | Référentiel qualité (raw, flagged, validated, replaced, rejected) | `Status_ID (PK)` | FK depuis `metadata` ou `value` |
| **type_data** | Catégorisation du type d’enregistrement (measurement, laboratory, control_signal…) | `Type_ID (PK)` | FK depuis `metadata` |

---

### 3.2 Instrumentation et procédures

| Table | Description | Clés | Relations |
|-------|--------------|------|------------|
| **equipment_model** | Modèle d’équipement (méthode, fonctions, fabricant, manuels) | `Equipment_model_ID (PK)` | Liée à `equipment`, `parameter`, `procedures` |
| **equipment** | Équipement individuel (identifiant, numéro de série, propriétaire, date d’achat, mise en service) | `Equipment_ID (PK)` | FK `Equipment_model_ID` |
| **parameter** | Variable mesurée (température, NH₄, débit, etc.) avec unité et description | `Parameter_ID (PK)` | FK `Unit_ID` |
| **procedures** | Procédures opératoires ou de maintenance | `Procedure_ID (PK)` | liées à `parameter` et `equipment_model` |
| **equipment_model_has_specification** | Table de correspondance (remplace l’ancienne `equipment_model_has_parameter`) | `Equipment_model_ID`, `Parameter_ID` (CK) | inclut champs `Range_min`, `Range_max`, `Resolution`, `Unit_ID` |
| **parameter_has_procedures** | Relation N-N entre paramètres et procédures | `Parameter_ID`, `Procedure_ID` (CK) |
| **equipment_model_has_procedures** | Relation N-N entre modèles et procédures | `Equipment_model_ID`, `Procedure_ID` (CK) |

---

### 3.3 Référentiels d’ingestion et d’opérations

| Table | Description | Clés | Relations |
|-------|--------------|------|------------|
| **source** | Provenance du signal ou des fichiers (MQTT, API, OPC, CSV, manuel) | `Source_ID (PK)` | FK depuis `metadata` |
| **operations** | Seuils et paramètres opérationnels (NO3_min, NO3_max, alarmes) | `Operation_ID (PK)` | reliée à `source` |
| **syncdiagrams**, **maxtimestamp** | Tables internes de synchronisation et historique de timestamps | `AK`, `PK` divers | utilisées pour ingestion automatisée |
| **holiday** | Gestion des jours fériés pour planification | `Message_ID (PK)` | sans dépendances externes |

---

### 3.4 Domaine géospatial et environnemental

| Table | Description | Clés | Relations |
|-------|--------------|------|------------|
| **site** | Localisation physique d’un échantillonnage (adresse, ville, pays, type) | `Site_ID (PK)` | FK `Watershed_ID` |
| **sampling_points** | Points d’échantillonnage liés à un site, avec GPS et photos | `Sampling_point_ID (PK)` | FK `Site_ID` |
| **watershed** | Bassin versant associé au site | `Watershed_ID (PK)` | 1-N vers `site` |
| **urban_characteristics** | Surfaces urbaines, industrielles, agricoles, etc. | `Watershed_ID (FK)` | 1-1 avec `watershed` |
| **hydrological_characteristics** | Données hydrologiques détaillées (zones humides, forêts, prairies) | `Watershed_ID (FK)` | 1-1 avec `watershed` |
| **weather_condition** | Conditions météorologiques observées | `Condition_ID (PK)` | FK depuis `metadata` |

---

### 3.5 Projets et associations

| Table | Description | Clés | Relations |
|-------|--------------|------|------------|
| **project** | Projet de recherche ou d’exploitation lié à des sites et instruments | `Project_ID (PK)` | central |
| **project_has_equipment** | N-N entre projet et équipement | `(Project_ID, Equipment_ID)` (CK) |
| **project_has_contact** | N-N entre projet et contact | `(Project_ID, Contact_ID)` (CK) |
| **project_has_sampling_points** | N-N entre projet et points d’échantillonnage | `(Project_ID, Sampling_point_ID)` (CK) |
| **equipment_has_sampling_points** | N-N entre équipement et points d’échantillonnage | `(Equipment_ID, Sampling_point_ID)` (CK) |
| **contact** | Informations sur les personnes et organisations liées aux projets | `Contact_ID (PK)` | partagée entre projets, métadonnées, équipement_model |

---

### 3.6 Contrôle, automatisation et validation

| Table | Description | Clés | Relations |
|-------|--------------|------|------------|
| **control_loop** | Décrit les boucles de régulation automatiques (capteur-contrôleur-actionneur) | `Measurement (FK)`, `Controller (FK)`, `Actuator (FK)` | intégrée avec les flux en temps réel |
| **value_before_12_04_2025**, **value_test_hedi** | Tables d’historisation ou de test (migration & validation) | `Value_ID (PK)` | même structure que `value` |

---

## 4. Contraintes clés et intégrité référentielle

- **PK :** toutes les tables principales utilisent un `INT` auto-increment (SQL Server IDENTITY).
- **FK :** contraints en cascade `ON UPDATE CASCADE` / `ON DELETE NO ACTION` pour la plupart.
- **CK :** relations N-N avec `compositeKeyFirst`, `compositeKeySecond`.
- **Indexes :** `IX_Metadata_Parameter`, `IX_Value_Timestamp`, `IX_Site_Watershed`.
- **FK notables :**
    - `value.Metadata_ID → metadata.Metadata_ID`
    - `metadata.Parameter_ID → parameter.Parameter_ID`
    - `metadata.Equipment_ID → equipment.Equipment_ID`
    - `equipment.Equipment_model_ID → equipment_model.Equipment_model_ID`
    - `site.Watershed_ID → watershed.Watershed_ID`

---

## 5. Interconnexions externes (AS-IS)

| Source | Type | Description |
|--------|------|-------------|
| **FactoryTalk Historian** | OPC/CSV | Extraction automatique vers table `source` |
| **Python API (pilEAUte)** | REST | Insertion contrôlée vers `value` et `metadata` |
| **MQTT Broker** | Temps réel | Publication de `value` vers `control_loop` |
| **Grafana** | Visualisation | Lecture sur `value`, `metadata`, `status` |
| **Power BI / CSV Export** | Reporting | Requêtes consolidées multi-projets |

---

## 6. Évolution prévisible (TO-BE 2025+)

- Uniformisation du modèle vers une architecture **Docker + PostgreSQL + API REST**
- Ajout d’une couche **data lineage** (audit, tracking de corrections)
- Simplification des relations N-N (`project_has_*`) via vues logiques
- Dépréciation des tables `value_before_12_04_2025` et `value_test_hedi`
- Extension du domaine “operations” vers les boucles de contrôle prédictives (IA embarquée)

---

## 7. Références croisées

| Fichier | Usage |
|----------|-------|
| `tables.md` | Détail des champs, types SQL, descriptions |
| `valuesets.md` | Vocabulaire contrôlé (status, type_data, source_protocol, etc.) |
| `schema.md` | Vue d’ensemble du modèle relationnel |
| `architecture.md` *(à venir)* | Flux de données et interconnexions (API, MQTT, Historian) |
