output "api_base_url" {
  description = "API Gateway invoke URL for the FastAPI Lambda target."
  value       = module.api_lambda.api_base_url
}

output "amplify_app_id" {
  description = "Amplify app id."
  value       = try(module.amplify[0].app_id, "")
}

output "amplify_default_domain" {
  description = "Amplify default domain for the web app."
  value       = try(module.amplify[0].default_domain, "")
}

output "database_secret_arn" {
  description = "Secrets Manager ARN used by Lambda for database connection material."
  value       = module.rds.db_secret_arn
  sensitive   = true
}

output "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint used by Lambda when enable_rds_proxy is true."
  value       = module.rds_proxy.proxy_endpoint
}

output "rds_endpoint" {
  description = "RDS endpoint used by Lambda when RDS Proxy is disabled."
  value       = module.rds.db_endpoint
}

output "external_api_secret_arn" {
  description = "Secrets Manager ARN for OpenDART/NAVER API credentials."
  value       = module.secrets.external_api_secret_arn
  sensitive   = true
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool id for email-based P1 auth."
  value       = module.cognito.user_pool_id
}

output "cognito_app_client_id" {
  description = "Public Cognito app client id for the Next.js frontend."
  value       = module.cognito.app_client_id
}

output "cognito_issuer" {
  description = "JWT issuer used by API Gateway HTTP API authorizer."
  value       = module.cognito.issuer
}

output "cognito_hosted_ui_domain" {
  description = "Cognito Hosted UI domain for the Next.js frontend."
  value = module.cognito.hosted_ui_domain == "" ? "" : (
    "https://${module.cognito.hosted_ui_domain}.auth.${var.aws_region}.amazoncognito.com"
  )
}

output "agentcore_runtime_arn" {
  description = "AgentCore Runtime ARN when agentcore_runtime_enabled is true."
  value       = module.agentcore_runtime.runtime_arn
}

output "agentcore_runtime_endpoint_name" {
  description = "AgentCore Runtime default endpoint name when enabled."
  value       = module.agentcore_runtime.runtime_endpoint_name
}
