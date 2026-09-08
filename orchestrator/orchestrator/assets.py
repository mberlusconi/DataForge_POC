import os

os.environ["SF_USE_CACHED_TOKEN"] = "true"
os.environ["PYTHON_CONNECTOR_DISABLE_KEYRING"] = "true"

from typing import Mapping, Any
from dagster import asset, AssetExecutionContext, AssetKey
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator
import snowflake.connector
from .project import dbt_project

class CustomDagsterDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        resource_type = dbt_resource_props.get("resource_type")
        name = dbt_resource_props.get("name")

        # 1. Mapeamos la fuente dbt a la clave exacta de la ingesta Python
        if resource_type == "source" and name == "raw_customers":
            return AssetKey("raw_customers_ingestion")

        # 2. Desambiguamos el seed 'raw_customers.csv'
        if resource_type == "seed" and name == "raw_customers":
            return AssetKey("seed_raw_customers")

        return super().get_asset_key(dbt_resource_props)

# 1. Asset NATIVO de Python para la ingesta Snowflake
@asset(
    key=AssetKey("raw_customers_ingestion"),
    group_name="bronze_ingestion",
    compute_kind="snowflake"
)
def raw_customers_ingestion(context: AssetExecutionContext):
    """Ingesta de archivos CSV desde Snowflake Stage hacia RAW_CUSTOMERS."""
    
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER", "MARTIN.BERLUSCONI@ALLATA.COM"),
        account=os.getenv("SNOWFLAKE_ACCOUNT", "mu75918.us-east-2.aws"),
        authenticator="externalbrowser",
        warehouse="COMPUTE_WH",
        database="POC_MEDALLION_CICD",
        schema="BRONZE_DEV",
        role="DBT_PIPELINE_DEVELOPER",

        client_store_temporary_credential=False,
        client_request_mfa_token=False
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

# 2. DBT Assets con el traductor
@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=CustomDagsterDbtTranslator()
)
def medallion_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    dbt_invocation = dbt.cli(["build"], context=context, raise_on_error=False)
    
    yield from dbt_invocation.stream()
    
    if dbt_invocation.get_artifact("run_results.json") is None and dbt_invocation.process.returncode != 0:
        dbt_invocation._raise_on_error()