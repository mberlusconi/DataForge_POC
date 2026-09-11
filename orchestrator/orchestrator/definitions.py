from dagster import Definitions
from dagster_dbt import DbtCliResource
from .assets import raw_customers_ingestion, medallion_dbt_assets, refresh_developer_grants
from .project import dbt_project
from .jobs import reset_environment_job

defs = Definitions(
    assets=[raw_customers_ingestion, medallion_dbt_assets, refresh_developer_grants],
    jobs=[reset_environment_job],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt_project,
            target="dev_jwt",
        ),
    },        
)