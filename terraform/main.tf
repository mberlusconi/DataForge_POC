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

# File format para ingesta CSV
resource "snowflake_file_format" "csv_format" {
  for_each = toset(var.environments)

  name        = "FF_CSV"
  database    = snowflake_database.poc_medallion_cicd.name
  schema      = "BRONZE_${each.key}"
  format_type = "CSV"

  field_delimiter               = ","
  skip_header                   = 1
  field_optionally_enclosed_by  = "\""
  null_if                       = ["NULL", "null", ""]
  empty_field_as_null           = true

  depends_on = [snowflake_schema.medallion_schemas]
}

resource "snowflake_table" "raw_customers" {
  for_each = toset(var.environments)

  database = snowflake_database.poc_medallion_cicd.name
  schema   = "BRONZE_${each.key}"
  name     = "RAW_CUSTOMERS"

  column {
    name = "ID"
    type = "NUMBER"
  }
  column {
    name = "FIRST_NAME"
    type = "VARCHAR(16777216)"
  }
  column {
    name = "LAST_NAME"
    type = "VARCHAR(16777216)"
  }
  column {
    name = "EMAIL"
    type = "VARCHAR(16777216)"
  }
  column {
    name = "PHONE"
    type = "VARCHAR(16777216)"
  }
  column {
    name = "COUNTRY"
    type = "VARCHAR(16777216)"
  }
  column {
    name = "_FILE_NAME"
    type = "VARCHAR(16777216)"
  }

  depends_on = [snowflake_schema.medallion_schemas]

  lifecycle {
    ignore_changes = all
  }
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

# Stage READ for all stages
resource "snowflake_grant_privileges_to_account_role" "developer_stage_read" {
  for_each = snowflake_stage.internal_stage

  privileges        = ["READ"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema_object {
    object_type = "STAGE"
    object_name = "${snowflake_database.poc_medallion_cicd.name}.BRONZE_${each.key}.${each.value.name}"
  }
}


# File format USAGE
resource "snowflake_grant_privileges_to_account_role" "developer_file_format_usage" {
  for_each = snowflake_file_format.csv_format

  privileges        = ["USAGE"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema_object {
    object_type = "FILE FORMAT"
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

  depends_on = [snowflake_table.raw_customers]
}

# Grant SELECT on current views
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

# Stage WRITE for all stages (needed for PUT operations)
resource "snowflake_grant_privileges_to_account_role" "developer_stage_write" {
  for_each = snowflake_stage.internal_stage

  privileges        = ["WRITE"]
  account_role_name = "DBT_PIPELINE_DEVELOPER"
  on_schema_object {
    object_type = "STAGE"
    object_name = "${snowflake_database.poc_medallion_cicd.name}.BRONZE_${each.key}.${each.value.name}"
  }
}
