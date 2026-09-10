terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 0.87.0"
    }
  }
}

provider "snowflake" {
  account        = "mu75918.us-east-2.aws"
  user           = var.snowflake_svc_user
  role           = var.snowflake_role
  authenticator  = "JWT"
  
  private_key = file(var.snowflake_private_key_path)
}

# Database
resource "snowflake_database" "poc_medallion_cicd" {
  name    = var.database_name
  comment = "Database container for POC environments and Medallion layers"
}

# Schema matrix
locals {
  schema_matrix = setproduct(var.layers, var.environments)
}

resource "snowflake_schema" "medallion_schemas" {
  for_each = {
    for pair in local.schema_matrix : "${pair[0]}_${pair[1]}" => {
      layer = pair[0]
      env   = pair[1]
    }
  }

  database = snowflake_database.poc_medallion_cicd.name
  name     = each.key
  comment  = "${each.value.layer} layer for ${each.value.env} environment"
}

# Stages
resource "snowflake_stage" "internal_stage" {
  for_each = toset(var.environments)

  name     = "RAW_FILES_STAGE"
  database = snowflake_database.poc_medallion_cicd.name
  schema   = "BRONZE_${each.key}"
  comment  = "Internal stage for raw landing files in ${each.key}"

  depends_on = [snowflake_schema.medallion_schemas]
}

# =====================================================
# PERMISSIONS
# =====================================================

# Database usage
resource "snowflake_grant_privileges_to_account_role" "developer_db_usage" {
  privileges        = ["USAGE"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.poc_medallion_cicd.name
  }
}

# Schema usage for all schemas
resource "snowflake_grant_privileges_to_account_role" "developer_schema_usage" {
  for_each = snowflake_schema.medallion_schemas

  privileges        = ["USAGE"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema {
    schema_name = "${snowflake_database.poc_medallion_cicd.name}.${each.value.name}"
  }
}

# Stage read for all stages
resource "snowflake_grant_privileges_to_account_role" "developer_stage_read" {
  for_each = snowflake_stage.internal_stage

  privileges        = ["READ"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema_object {
    object_type = "STAGE"
    object_name = "${snowflake_database.poc_medallion_cicd.name}.BRONZE_${each.key}.${each.value.name}"
  }
}
# Grant SELECT on current tables
resource "snowflake_grant_privileges_to_account_role" "developer_all_tables" {
  for_each = snowflake_schema.medallion_schemas

  privileges        = ["SELECT"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema           = "${snowflake_database.poc_medallion_cicd.name}.${each.value.name}"
    }
  }
}

# Grant SELECT current views
resource "snowflake_grant_privileges_to_account_role" "developer_all_views" {
  for_each = snowflake_schema.medallion_schemas

  privileges        = ["SELECT"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema_object {
    all {
      object_type_plural = "VIEWS"
      in_schema           = "${snowflake_database.poc_medallion_cicd.name}.${each.value.name}"
    }
  }
}
