variable "name_prefix" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_instance_class" {
  type = string
}

variable "allocated_storage_gb" {
  type = number
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "secret_arn" {
  type      = string
  sensitive = true
}

variable "log_group_name" {
  type = string
}

variable "deletion_protection" {
  description = "Protect the RDS instance from accidental deletion. Set false for dev to allow teardown."
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip the final snapshot on deletion. Set true for dev to avoid leftover snapshots."
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Number of days to retain automated backups. Use 1 for dev and 7 or more for prod; valid range is 1 to 35."
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_period >= 1 && var.backup_retention_period <= 35
    error_message = "backup_retention_period must be between 1 and 35 days. Use 1 for dev and 7 or more for prod."
  }
}
