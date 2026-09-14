{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        
        {# 1. Slim CI for PRs #}
        {%- if target.name == 'ci' -%}
            {{ custom_schema_name | trim }}_{{ env_var('PR_SCHEMA') }}

        {# 2. CD Deployment to UAT #}
        {%- elif target.name == 'uat' -%}
            {{ custom_schema_name | trim | replace('_DEV', '_UAT') }}

        {# 3. CD Deployment to PROD #}
        {%- elif target.name == 'prod' -%}
            {{ custom_schema_name | trim | replace('_DEV', '_PROD') }}

        {# 4. Local execution, Dagster, Terraform, and DEV target (keeps original names) #}
        {%- else -%}
            {{ custom_schema_name | trim }}
        {%- endif -%}

    {%- endif -%}

{%- endmacro %}