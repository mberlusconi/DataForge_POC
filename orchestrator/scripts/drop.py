import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import snowflake.connector

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

ENV = os.getenv("RESET_ENV", "DEV")  # DEV, UAT, PROD

# RESET_SQL = f"""
# TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.BRONZE_{ENV}.RAW_CUSTOMERS;
# TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.BRONZE_{ENV}.STG_BRONZE_CUSTOMERS;
# DROP STAGE IF EXISTS POC_MEDALLION_CICD.BRONZE_{ENV}.RAW_FILES_STAGE;
# CREATE STAGE POC_MEDALLION_CICD.BRONZE_{ENV}.RAW_FILES_STAGE FILE_FORMAT = (FORMAT_NAME = 'POC_MEDALLION_CICD.BRONZE_{ENV}.FF_CSV');
# DROP VIEW IF EXISTS POC_MEDALLION_CICD.SILVER_{ENV}.SILVER_CUSTOMERS;
# TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.GOLD_{ENV}.GOLD_DIM_CUSTOMERS;
# TRUNCATE TABLE IF EXISTS POC_MEDALLION_CICD.GOLD_{ENV}.GOLD_COUNTRY_METRICS;
# """

RESET_SQL = f"""
DROP DATABASE IF EXISTS POC_MEDALLION_CICD;
"""

# RESET_SQL = f"""

# """

def main():
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
    for statement in RESET_SQL.strip().split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        print(f"🔄 Ejecutando: {stmt[:80]}...")
        cursor.execute(stmt)
        print("✅ OK")

    cursor.close()
    conn.close()
    print(f"\n🎉 Reset completo de {ENV}!")

if __name__ == "__main__":
    main()
