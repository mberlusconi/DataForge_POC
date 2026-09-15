import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import snowflake.connector

def _load_private_key_der(path, passphrase=None):
    with open(path, "rb") as f:
        p_key = serialization.load_pem_private_key(
            f.read(), password=passphrase.encode() if passphrase else None,
            backend=default_backend()
        )
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

key_path = r"C:\Martin\Projects\DataForge_POC\terraform\svc_dbt_pipeline_deploy_key.p8"
private_key_der = _load_private_key_der(key_path)

conn = snowflake.connector.connect(
    user="SVC_DBT_PIPELINE_DEPLOY",
    account="mu75918.us-east-2.aws",
    private_key=private_key_der,
    warehouse="COMPUTE_WH",
    database="POC_MEDALLION_CICD",
    role="DBT_PIPELINE_DEPLOYER",
)

cursor = conn.cursor()
for schema in ["SILVER_UAT", "GOLD_UAT"]:
    cursor.execute(f"SHOW TABLES IN SCHEMA POC_MEDALLION_CICD.{schema}")
    print(f"--- TABLES in {schema} ---")
    for row in cursor.fetchall():
        print(row[1])  # nombre de la tabla

cursor.execute("SHOW VIEWS IN SCHEMA POC_MEDALLION_CICD.SILVER_UAT")
print("--- VIEWS in SILVER_UAT ---")
for row in cursor.fetchall():
    print(row[1])

cursor.close()
conn.close()
