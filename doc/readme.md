## ADD TITLE

### Architecture
# Pipeline Architecture — Medallion CI/CD POC

```mermaid
graph TB
    subgraph LOCAL["Local Developer Environment"]
        DEV_USER["Martin<br/>DBT_PIPELINE_DEVELOPER<br/>(read-only on data)"]
        DAGSTER["Dagster<br/>Orchestrator"]
        DEV_USER -->|"Materialize<br/>(ingestion + dbt build + grants)"| DAGSTER
    end

    subgraph GIT["Version Control"]
        REPO["Git Repository<br/>main branch"]
    end

    subgraph CICD["CI/CD — GitHub Actions"]
        CI["Slim CI<br/>(Pull Requests)<br/>Lint + Test on ephemeral schema"]
        CD_DEV["Deploy DEV<br/>Automatic"]
        CD_UAT["Deploy UAT<br/>Requires approval"]
        CD_PROD["Deploy PROD<br/>Requires approval"]
        CD_DEV --> CD_UAT --> CD_PROD
    end

    subgraph SNOWFLAKE["Snowflake — POC_MEDALLION_CICD"]
        subgraph DEVSCHEMA["BRONZE/SILVER/GOLD _DEV"]
            direction LR
            BDEV["Bronze"] --> SDEV["Silver"] --> GDEV["Gold"]
        end
        subgraph UATSCHEMA["BRONZE/SILVER/GOLD _UAT"]
            direction LR
            BUAT["Bronze"] --> SUAT["Silver"] --> GUAT["Gold"]
        end
        subgraph PRODSCHEMA["BRONZE/SILVER/GOLD _PROD"]
            direction LR
            BPROD["Bronze"] --> SPROD["Silver"] --> GPROD["Gold"]
        end
    end

    subgraph IAC["Infrastructure as Code"]
        TF["Terraform<br/>Database, Schemas, Stages,<br/>Grants, Roles"]
    end

    subgraph AUTH["Authentication"]
        SVC["Service Account<br/>SVC_DBT_PIPELINE_DEPLOY<br/>JWT + Key-Pair<br/>(no passwords, no manual SSO)"]
    end

    DEV_USER -->|"git push"| REPO
    REPO -->|"trigger"| CI
    REPO -->|"trigger"| CD_DEV

    DAGSTER -->|"raw data ingestion"| BDEV
    DAGSTER -->|"raw data ingestion<br/>(manual, per environment)"| BUAT
    DAGSTER -->|"raw data ingestion<br/>(manual, per environment)"| BPROD

    CD_DEV -->|"dbt build --target cd_dev"| DEVSCHEMA
    CD_UAT -->|"dbt build --target uat"| UATSCHEMA
    CD_PROD -->|"dbt build --target prod"| PRODSCHEMA

    TF -.->|"provisions"| SNOWFLAKE
    SVC -.->|"authenticates"| TF
    SVC -.->|"authenticates"| DAGSTER
    SVC -.->|"authenticates"| CD_DEV
    SVC -.->|"authenticates"| CD_UAT
    SVC -.->|"authenticates"| CD_PROD

    classDef approval fill:#8B0000,stroke:#5c0000,color:#ffffff,stroke-width:2px
    classDef secure fill:#003366,stroke:#001a33,color:#ffffff,stroke-width:2px
    classDef infra fill:#1b5e20,stroke:#0d3311,color:#ffffff,stroke-width:2px
    classDef bronze fill:#8B5A2B,stroke:#5c3b1c,color:#ffffff
    classDef silver fill:#5A6268,stroke:#3a3f42,color:#ffffff
    classDef gold fill:#B8860B,stroke:#7a5a07,color:#ffffff

    class CD_UAT,CD_PROD approval
    class SVC secure
    class TF infra
    class BDEV,BUAT,BPROD bronze
    class SDEV,SUAT,SPROD silver
    class GDEV,GUAT,GPROD gold
```


### Flow
```Text
                  ┌──────────────────────────────────────────────┐
                  │              SNOWFLAKE STAGE                 │
                  │   (@POC_MEDALLION_CICD.BRONZE_DEV.RAW_STAGE) │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         │ (1) Dagster Asset: COPY INTO
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │              RAW_CUSTOMERS                   │
                  │       (Tabla Landing en BRONZE_DEV)          │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         │ (2) Dagster Asset: dbt build
                                         ▼
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │                                 dbt PIPELINE                                  │
 │                                                                               │
 │  [stg_bronze_customers] ──► [silver_customers] ──► [gold_dim_customers]       │
 │          │                         │                        │                 │
 │          ▼                         ▼                        ▼                 │
 │     dbt test (Bronze)         dbt test (Silver)         dbt test (Gold)       │
 │                                                             │                 │
 │                                                             ▼                 │
 │                                                  [gold_country_metrics]       │
 │                                                             │                 │
 │                                                             ▼                 │
 │                                                    Singular Data Test         │
 └───────────────────────────────────────────────────────────────────────────────┘
```
