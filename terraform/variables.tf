variable "snowflake_account" {
  description = "Snowflake account identifier (e.g., orgname-accountname)"
  type        = string
}

variable "snowflake_user" {
  description = "Corporate Snowflake username or SSO email"
  type        = string
}

variable "snowflake_svc_user" {
  description = "Corporate Snowflake service username "
  type        = string
}

variable "snowflake_role" {
  description = "Snowflake role with permissions to create databases and schemas"
  type        = string
  default     = "DBT_PIPELINE_DEVELOPER"
}

variable "database_name" {
  description = "Single database name for the POC"
  type        = string
  default     = "POC_MEDALLION_CICD"
}

variable "environments" {
  description = "List of target environments"
  type        = list(string)
  default     = ["DEV", "UAT", "PROD"]
}

variable "layers" {
  description = "List of Medallion architecture layers"
  type        = list(string)
  default     = ["BRONZE", "SILVER", "GOLD"]
}

variable "snowflake_private_key_path" {
  type        = string
  description = "Path to Snowflake service account private key"
}
