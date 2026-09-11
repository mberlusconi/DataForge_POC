from pathlib import Path
from dagster_dbt import DbtProject

# (DataForge_POC/dbt_project)
dbt_project_dir = Path(__file__).joinpath("..", "..", "..", "dbt_project").resolve()
dbt_profiles_dir = Path.home().joinpath(".dbt").resolve()

dbt_project = DbtProject(
    project_dir=dbt_project_dir,
    packaged_project_dir=dbt_project_dir,
    profiles_dir=dbt_profiles_dir,
)

# Prepare & compile the manifest.json in the local development environment
if not dbt_project.manifest_path.exists():
    dbt_project.prepare_if_dev()
