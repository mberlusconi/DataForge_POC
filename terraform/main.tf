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

#Permissions

# Grant USAGE en database (igual, solo uno)
resource "snowflake_grant_privileges_to_account_role" "developer_db_usage" {
  privileges        = ["USAGE"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.poc_medallion_cicd.name
  }
}

# Grants USAGE en TODOS los schemas (dinámico)
resource "snowflake_grant_privileges_to_account_role" "developer_schema_usage" {
  for_each = snowflake_schema.medallion_schemas

  privileges        = ["USAGE"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema {
    schema_name = "${snowflake_database.poc_medallion_cicd.name}.${each.value.name}"
  }
}

# Grants READ en TODOS los stages (dinámico)
resource "snowflake_grant_privileges_to_account_role" "developer_stage_read" {
  for_each = snowflake_stage.internal_stage

  privileges        = ["READ"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema_object {
    object_type = "STAGE"
    object_name = "${snowflake_database.poc_medallion_cicd.name}.BRONZE_${each.key}.${each.value.name}"
  }
}
