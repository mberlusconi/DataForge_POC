import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

os.environ["SF_USE_CACHED_TOKEN"] = "true"
os.environ["PYTHON_CONNECTOR_DISABLE_KEYRING"] = "true"

from typing import Mapping, Any
from dagster import asset, AssetExecutionContext, AssetKey
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator
import snowflake.connector
from .project import dbt_project
import subprocess
from pathlib import Path

class CustomDagsterDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        resource_type = dbt_resource_props.get("resource_type")
        name = dbt_resource_props.get("name")

        if resource_type == "source" and name == "raw_customers":
            return AssetKey("raw_customers_ingestion")

        return super().get_asset_key(dbt_resource_props)

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        return "medallion_dbt"


def _load_private_key_der(path: str, passphrase: str | None = None) -> bytes:
    """Reads a PEM file and returns it as PKCS#8 DER bytes, the format
    expected by snowflake-connector-python for the private_key parameter."""

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


# 1. Natice asset
@asset(
    key=AssetKey("raw_customers_ingestion"),
    group_name="bronze_ingestion",
    compute_kind="snowflake"
)
def raw_customers_ingestion(context: AssetExecutionContext):
    """Ingests CSV files from a Snowflake Stage into RAW_CUSTOMERS."""


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
        schema="BRONZE_DEV",
        role=os.getenv("SNOWFLAKE_ROLE", "DBT_PIPELINE_DEPLOYER"),
    )

    copy_sql = """
    COPY INTO POC_MEDALLION_CICD.BRONZE_DEV.RAW_CUSTOMERS (
        id, first_name, last_name, email, phone, country, _file_name
    )
    FROM (
        SELECT $1, $2, $3, $4, $5, $6, METADATA$FILENAME
        FROM @POC_MEDALLION_CICD.BRONZE_DEV.RAW_FILES_STAGE
    )
    FILE_FORMAT = (FORMAT_NAME = 'POC_MEDALLION_CICD.BRONZE_DEV.FF_CSV')
    ON_ERROR = 'CONTINUE';
    """

    cursor = conn.cursor()
    cursor.execute(copy_sql)
    result = cursor.fetchall()
    context.log.info(f"Resultado COPY INTO: {result}")

    cursor.close()
    conn.close()

# 2. DBT Assets with translator
@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=CustomDagsterDbtTranslator()
)
def medallion_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    dbt_invocation = dbt.cli(["build"], context=context, raise_on_error=False)

    yield from dbt_invocation.stream()

    if dbt_invocation.get_artifact("run_results.json") is None and dbt_invocation.process.returncode != 0:
        dbt_invocation._raise_on_error()

#------------
# Grants
#------------
TERRAFORM_DIR = Path(__file__).joinpath("..", "..", "..", "terraform").resolve()
DBT_MANAGED_SCHEMAS = ["BRONZE_DEV", "SILVER_DEV", "GOLD_DEV"]
@asset(
    deps=[medallion_dbt_assets],
    group_name="permissions",
    compute_kind="terraform",
)
def refresh_developer_grants(context: AssetExecutionContext):
    """Re-grants SELECT to DBT_PIPELINE_DEVELOPER on the tables/views that
    dbt has just (re)created in BRONZE/SILVER/GOLD DEV.
    This is necessary because dbt uses CREATE OR REPLACE, which generates
    a new object_id in Snowflake and causes the previous grants to be lost.
    Only the grants are explicitly re-applied (-replace), never a general
    apply, to avoid putting any other infrastructure resources at risk.
    """

    args = ["terraform", "apply", "-auto-approve"]
    for schema in DBT_MANAGED_SCHEMAS:
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
    context.log.info("DBT_PIPELINE_DEVELOPER grants executed OK.")
