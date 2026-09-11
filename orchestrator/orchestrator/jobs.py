# orchestrator/orchestrator/jobs.py
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import snowflake.connector
from dagster import op, job, OpExecutionContext, Config


def _load_private_key_der(path: str, passphrase: str | None = None) -> bytes:
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


class ResetEnvConfig(Config):
    environment: str = "DEV"  # DEV, UAT, PROD


@op
def reset_environment(context: OpExecutionContext, config: ResetEnvConfig):
    env = config.environment.upper()

    # reset_sql = f"""
    # TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.BRONZE_{env}.RAW_CUSTOMERS;
    # TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.BRONZE_{env}.STG_BRONZE_CUSTOMERS;
    # DROP STAGE IF EXISTS POC_MEDALLION_CICD.BRONZE_{env}.RAW_FILES_STAGE;
    # CREATE STAGE POC_MEDALLION_CICD.BRONZE_{env}.RAW_FILES_STAGE FILE_FORMAT = (FORMAT_NAME = 'POC_MEDALLION_CICD.BRONZE_{env}.FF_CSV');
    # DROP VIEW IF EXISTS POC_MEDALLION_CICD.SILVER_{env}.SILVER_CUSTOMERS;
    # TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.GOLD_{env}.GOLD_DIM_CUSTOMERS;
    # TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.GOLD_{env}.GOLD_COUNTRY_METRICS;
    # """
    RESET_SQL = f"""
    TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.BRONZE_{ENV}.RAW_CUSTOMERS;
    TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.BRONZE_{ENV}.STG_BRONZE_CUSTOMERS;
    REMOVE @POC_MEDALLION_CICD.BRONZE_{ENV}.RAW_FILES_STAGE;
    TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.GOLD_{ENV}.GOLD_DIM_CUSTOMERS;
    TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.GOLD_{ENV}.GOLD_COUNTRY_METRICS;
    """

    key_path = os.getenv(
        "SNOWFLAKE_PRIVATE_KEY_PATH",
        r"C:\Martin\Projects\DataForge_POC\terraform\svc_dbt_pipeline_deploy_key.p8"
    )
    private_key_der = _load_private_key_der(key_path)

    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER", "SVC_DBT_PIPELINE_DEPLOY"),
        account=os.getenv("SNOWFLAKE_ACCOUNT", "mu75918.us-east-2.aws"),
        private_key=private_key_der,
        warehouse="COMPUTE_WH",
        database="POC_MEDALLION_CICD",
        role=os.getenv("SNOWFLAKE_ROLE", "DBT_PIPELINE_DEPLOYER"),
    )

    cursor = conn.cursor()
    for statement in reset_sql.strip().split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        context.log.info(f"Ejecutando: {stmt[:80]}...")
        cursor.execute(stmt)

    cursor.close()
    conn.close()
    context.log.info(f"Reset completo de {env}")


@job
def reset_environment_job():
    reset_environment()
