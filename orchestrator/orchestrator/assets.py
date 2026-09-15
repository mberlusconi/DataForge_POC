import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import subprocess
from pathlib import Path

os.environ["SF_USE_CACHED_TOKEN"] = "true"
os.environ["PYTHON_CONNECTOR_DISABLE_KEYRING"] = "true"

from typing import Mapping, Any
from dagster import asset, AssetExecutionContext, AssetKey, Config
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator
import snowflake.connector
from .project import dbt_project


class CustomDagsterDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        resource_type = dbt_resource_props.get("resource_type")
        name = dbt_resource_props.get("name")

        # Map the dbt source to the exact key of the Python ingestion asset
        if resource_type == "source" and name == "raw_customers":
            return AssetKey("raw_customers_ingestion")

        return super().get_asset_key(dbt_resource_props)

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        return "medallion_dbt"


def _load_private_key_der(path: str, passphrase: str | None = None) -> bytes:
    """Read a PEM file and return it as DER PKCS8 bytes, the format expected
    by snowflake-connector-python in the private_key parameter."""
    with open(path, "rb") as key_file:
        p_key = serialization.load_pem_private_key(
            key_file.read(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend(),
        )
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


class IngestionConfig(Config):
    # Target environment for ingestion: DEV, UAT, PROD
    environment: str = "DEV"


# 1. Native Python asset for Snowflake ingestion
@asset(
    key=AssetKey("raw_customers_ingestion"),
    group_name="bronze_ingestion",
    compute_kind="snowflake"
)
def raw_customers_ingestion(context: AssetExecutionContext, config: IngestionConfig):
    """Ingests CSV files from the Snowflake stage into RAW_CUSTOMERS,
    in the environment (schema) specified by config.environment."""

    env = config.environment.upper()
    schema = f"BRONZE_{env}"

    key_path = os.getenv(
        "SNOWFLAKE_PRIVATE_KEY_PATH",
        r"C:\Martin\Projects\DataForge_POC\terraform\svc_dbt_pipeline_deploy_key.p8"
    )
    private_key_der = _load_private_key_der(
        key_path,
        os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None,
    )

    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER", "SVC_DBT_PIPELINE_DEPLOY"),
        account=os.getenv("SNOWFLAKE_ACCOUNT", "mu75918.us-east-2.aws"),
        private_key=private_key_der,
        warehouse="COMPUTE_WH",
        database="POC_MEDALLION_CICD",
        schema=schema,
        role=os.getenv("SNOWFLAKE_ROLE", "DBT_PIPELINE_DEPLOYER"),
    )

    copy_sql = f"""
    COPY INTO POC_MEDALLION_CICD.{schema}.RAW_CUSTOMERS (
        id, first_name, last_name, email, phone, country, _file_name
    )
    FROM (
        SELECT $1, $2, $3, $4, $5, $6, METADATA$FILENAME
        FROM @POC_MEDALLION_CICD.{schema}.RAW_FILES_STAGE
    )
    FILE_FORMAT = (FORMAT_NAME = 'POC_MEDALLION_CICD.{schema}.FF_CSV')
    ON_ERROR = 'CONTINUE'
    FORCE = TRUE;
    """

    cursor = conn.cursor()
    cursor.execute(copy_sql)
    result = cursor.fetchall()
    context.log.info(f"[{env}] COPY INTO result: {result}")

    cursor.close()
    conn.close()

class DbtBuildConfig(Config):
    # dbt profile target to use: dev_jwt, uat, prod
    dbt_target: str = "dev_jwt"


# 2. dbt assets with the custom translator
@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=CustomDagsterDbtTranslator()
)
def medallion_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    dbt_invocation = dbt.cli(["build"], context=context, raise_on_error=False)

    yield from dbt_invocation.stream()

    try:
        run_results = dbt_invocation.get_artifact("run_results.json")
    except FileNotFoundError:
        run_results = None

    if run_results is None and dbt_invocation.process.returncode != 0:
        dbt_invocation._raise_on_error()


# ------------
# Grants
# ------------
TERRAFORM_DIR = Path(__file__).joinpath("..", "..", "..", "terraform").resolve()
DBT_MANAGED_SCHEMAS = ["BRONZE_DEV", "SILVER_DEV", "GOLD_DEV"]
class GrantsConfig(Config):
    # Environment whose schemas should get grants refreshed: DEV, UAT, PROD
    environment: str = "DEV"


@asset(
    deps=[medallion_dbt_assets],
    group_name="permissions",
    compute_kind="terraform",
)
def refresh_developer_grants(context: AssetExecutionContext, config: GrantsConfig):
    """Re-grants SELECT to DBT_PIPELINE_DEVELOPER on the tables/views that
    dbt has just (re)created in BRONZE/SILVER/GOLD, for the given environment.
    This is necessary because dbt uses CREATE OR REPLACE, which generates
    a new object_id in Snowflake and causes the previous grants to be lost.
    Only the grants are explicitly re-applied (-replace), never a general
    apply, to avoid putting any other infrastructure resources at risk.
    """
    env = config.environment.upper()
    schemas = [f"BRONZE_{env}", f"SILVER_{env}", f"GOLD_{env}"]

    args = ["terraform", "apply", "-auto-approve"]
    for schema in schemas:
        args.append(
            f'-replace=snowflake_grant_privileges_to_account_role.developer_all_tables["{schema}"]'
        )
        args.append(
            f'-replace=snowflake_grant_privileges_to_account_role.developer_all_views["{schema}"]'
        )
    context.log.info(f"Running: {' '.join(args)}")
    result = subprocess.run(
        args,
        cwd=str(TERRAFORM_DIR),
        capture_output=True,
        text=True,
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        context.log.error(result.stderr)
        raise Exception(f"terraform apply failed:\n{result.stderr}")
    context.log.info(f"DBT_PIPELINE_DEVELOPER grants refreshed for {env}.")
