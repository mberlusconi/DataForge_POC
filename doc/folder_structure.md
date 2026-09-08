## Folder Structure

```Text
.
├── .github/
│   └── workflows/          # Workflows para GitHub Actions (Fase 5)
├── demo_files/             # Files used for demo
├── doc/                    # Documentation Files
│   ├── folder_structure
│   ├── plan_track.md
│   └── readme.md
├── orchestrator/           # Dagster Orchestrator
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── assets.py
│   │   ├── definitions.py
│   │   └── project.py
│   ├── orchestrator_test/
│   │   ├── __init__.py
│   │   ├── assets.py
│   │   └── definitions.py    
│   ├── pyproject.toml
│   └── README.md    
├── dagster/                # Proyecto de Dagster (Fase 3)
├── dbt_project/            # Proyecto de dbt Core (Fase 2)
└── terraform/              # Infraestructura como Código (Fase 1)
    ├── main.tf
    ├── variables.tf
    ├── terraform.tfvars
    └── outputs.tf
```
