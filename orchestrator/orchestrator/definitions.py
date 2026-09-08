from dagster import Definitions
from dagster_dbt import DbtCliResource
from .assets import raw_customers_ingestion, medallion_dbt_assets
from .project import dbt_project

defs = Definitions(
    assets=[raw_customers_ingestion, medallion_dbt_assets],
    resources={
        "dbt": DbtCliResource(project_dir=dbt_project),
    },
)