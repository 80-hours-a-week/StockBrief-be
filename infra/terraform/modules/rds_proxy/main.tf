locals {
  enabled = var.enabled && var.db_instance_identifier != "" && length(var.subnet_ids) > 0
}

data "aws_iam_policy_document" "assume_rds" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "proxy" {
  count = local.enabled ? 1 : 0

  name               = "${var.name_prefix}-rds-proxy-role"
  assume_role_policy = data.aws_iam_policy_document.assume_rds.json
}

data "aws_iam_policy_document" "secret_access" {
  count = local.enabled ? 1 : 0

  statement {
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = [var.secret_arn]
  }
}

resource "aws_iam_role_policy" "secret_access" {
  count = local.enabled ? 1 : 0

  name   = "${var.name_prefix}-rds-proxy-secret-access"
  role   = aws_iam_role.proxy[0].id
  policy = data.aws_iam_policy_document.secret_access[0].json
}

resource "aws_db_proxy" "postgres" {
  count = local.enabled ? 1 : 0

  name                   = "${var.name_prefix}-postgres-proxy"
  debug_logging          = false
  engine_family          = "POSTGRESQL"
  idle_client_timeout    = var.idle_client_timeout_seconds
  require_tls            = var.require_tls
  role_arn               = aws_iam_role.proxy[0].arn
  vpc_security_group_ids = var.security_group_ids
  vpc_subnet_ids         = var.subnet_ids

  auth {
    auth_scheme               = "SECRETS"
    client_password_auth_type = "POSTGRES_SCRAM_SHA_256"
    iam_auth                  = "DISABLED"
    secret_arn                = var.secret_arn
  }
}

resource "aws_db_proxy_default_target_group" "postgres" {
  count = local.enabled ? 1 : 0

  db_proxy_name = aws_db_proxy.postgres[0].name

  connection_pool_config {
    connection_borrow_timeout    = 120
    max_connections_percent      = 90
    max_idle_connections_percent = 50
  }
}

resource "aws_db_proxy_target" "postgres" {
  count = local.enabled ? 1 : 0

  db_instance_identifier = var.db_instance_identifier
  db_proxy_name          = aws_db_proxy.postgres[0].name
  target_group_name      = aws_db_proxy_default_target_group.postgres[0].name
}
