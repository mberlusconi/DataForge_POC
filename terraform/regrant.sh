#!/bin/bash
set -e

ENV="${1:-UAT}"  # uso: ./regrant.sh UAT  o  ./regrant.sh PROD

echo "Regranting DBT_PIPELINE_DEVELOPER on BRONZE_${ENV}, SILVER_${ENV}, GOLD_${ENV}..."

terraform apply -auto-approve \
  -replace="snowflake_grant_privileges_to_account_role.developer_all_tables[\"BRONZE_${ENV}\"]" \
  -replace="snowflake_grant_privileges_to_account_role.developer_all_views[\"BRONZE_${ENV}\"]" \
  -replace="snowflake_grant_privileges_to_account_role.developer_all_tables[\"SILVER_${ENV}\"]" \
  -replace="snowflake_grant_privileges_to_account_role.developer_all_views[\"SILVER_${ENV}\"]" \
  -replace="snowflake_grant_privileges_to_account_role.developer_all_tables[\"GOLD_${ENV}\"]" \
  -replace="snowflake_grant_privileges_to_account_role.developer_all_views[\"GOLD_${ENV}\"]"

echo "Done."
