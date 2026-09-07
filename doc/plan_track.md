# Proof of Concept (POC): Data Ingestion & Medallion Architecture

This repository contains the Proof of Concept (POC) for an end-to-end modern data platform using **Snowflake**, **Terraform**, **dbt Core**, **Dagster**, and **GitHub Actions**.

---

## Technical Stack

* **Data Warehouse:** Snowflake
* **Infrastructure as Code (IaC):** Terraform
* **Transformation Engine:** dbt Core (Medallion Architecture)
* **Orchestrator:** Dagster (`dagster-dbt`)
* **Data Quality & Governance:** SQLFluff, dbt-tests
* **CI/CD:** GitHub Actions (Multi-environment: DEV, UAT, PROD)

---

## Project Roadmap & Tracking

### Phase 1: Base Infrastructure & Snowflake Setup
* [ ] Initialize GitHub repository structure for Terraform, dbt, Dagster, and GitHub Actions.
* [ ] Define Terraform HCL scripts to provision Snowflake infrastructure:
  * Databases (`DEV_DB`, `UAT_DB`, `PROD_DB`).
  * Schemas (`BRONZE`, `SILVER`, `GOLD`).
  * Access roles, service accounts, and Virtual Warehouses (`COMPUTE_WH`).
  * Internal Stage within the `BRONZE` schema.
* [ ] Apply initial Terraform state to provision environment bases.

---

### Phase 2: Ingestion & Medallion Layer Development (dbt)
* [ ] Initialize and configure `dbt Core` project connecting to Snowflake.
* [ ] **Bronze Layer:** Implement raw landing tables and script execution for `COPY INTO` from Internal Stage.
* [ ] **Silver Layer:** Implement dbt models for data cleaning, type casting, standardization, and deduplication.
* [ ] **Gold Layer:** Implement dbt models for dimensional modeling (Facts/Dimensions) and business aggregations.
* [ ] Implement data quality tests (`not_null`, `unique`, referential integrity) and definitions in `schema.yml`.

---

### Phase 3: Workflow Orchestration with Dagster
* [ ] Initialize Dagster environment and install `dagster-dbt`.
* [ ] Implement Ingestion Asset/Op to handle raw file loading (`PUT` into Internal Stage -> `COPY INTO` Bronze).
* [ ] Configure dbt Software-Defined Assets (SDA) to trigger automatically upon Bronze load completion.
* [ ] Validate end-to-end pipeline executions using the Dagster UI.

---

### Phase 4: Quality & Code Governance Setup
* [ ] Configure `.sqlfluff` rules for standardized SQL linting.
* [ ] Standardize local execution commands (`dbt parse`, `dbt test`, `sqlfluff lint`).
* [ ] Configure **Slim CI** state comparison logic (`state:modified+`) to isolate downstream impacts.

---

### Phase 5: CI/CD Pipeline Implementation (GitHub Actions)
* [ ] **Continuous Integration (CI) Pipeline (Pull Requests):**
  * Automated code linting via `sqlfluff`.
  * Dynamic creation of ephemeral build schemas (`PR_SCHEMA_<PR_NUMBER>`).
  * Execution of Slim CI testing on modified assets and dependents.
  * Automatic teardown of ephemeral PR schemas.
* [ ] **Continuous Deployment (CD) Pipeline (Merge to Main):**
  * Automatic build and deploy to **DEV**.
  * Gated deployment to **UAT** (requires approval via GitHub Environments).
  * Gated deployment to **PROD** (requires approval via GitHub Environments).
* [ ] Execute complete PR dry-run to validate CI impact reporting and CD gating.