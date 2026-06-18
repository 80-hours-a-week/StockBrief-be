variable "name_prefix" {
  type = string
}

variable "enabled" {
  description = "Whether to create RDS Proxy resources."
  type        = bool
  default     = true
}

variable "db_instance_identifier" {
  type = string
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

variable "require_tls" {
  type    = bool
  default = true
}

variable "idle_client_timeout_seconds" {
  type    = number
  default = 1800
}
