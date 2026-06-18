# New AWS Bootstrap

Use this runbook when the previous AWS dev account is unavailable and StockBrief
must be created in a new AWS account.

## Current Dev Status

As of 2026-06-18, the new `dev` baseline is provisioned in `ap-northeast-2`
from the current AWS account. Do not treat previous AWS account resources as
available.

Provisioned:

- Terraform remote state S3 bucket and DynamoDB lock table
- GitHub Actions OIDC deploy role
- API Gateway HTTP API
- Lambda backend runtime
- Cognito User Pool and web app client
- Cognito Hosted UI domain
- Private RDS PostgreSQL 16
- Secrets Manager VPC endpoint
- CloudWatch log groups and baseline alarms

Runtime outputs:

- API base URL: `https://hazfha7995.execute-api.ap-northeast-2.amazonaws.com`
- Cognito issuer:
  `https://cognito-idp.ap-northeast-2.amazonaws.com/ap-northeast-2_VPOccT5rI`
- Cognito User Pool ID: `ap-northeast-2_VPOccT5rI`
- Cognito App Client ID: `3pgg4n3hda2pqf9q8ij9m79glk`
- Cognito Hosted UI:
  `https://stockbrief-dev-560271561793.auth.ap-northeast-2.amazoncognito.com`
- RDS endpoint is managed by Terraform output and must not be copied into app
  code.

Completed validation:

- Lambda maintenance operation `migrate_and_seed`
- `GET /v1/health`
- `GET /v1/stocks/candidates?limit=3`
- `GET /v1/recommendations/candidates?limit=3`
- `POST /v1/chat`
- Local FE sign-in through Cognito Hosted UI on `http://localhost:3001`
- Authenticated `GET /v1/me`, `GET /v1/me/preferences`, and
  `GET /v1/me/chat-sessions`

Still intentionally disabled or pending:

- Amplify Hosting
- RDS Proxy
- AgentCore Runtime
- Bedrock direct provider
- Real external API secret values and provider ingestion jobs
- Amplify-hosted Cognito callback smoke tests

## Preconditions

- AWS CLI is authenticated to the new account.
- The selected region is `ap-northeast-2`.
- GitHub access can set repository or environment variables for the team repo.
- A monthly AWS Budget is configured before application resources are applied.

## Bootstrap Steps

1. Confirm the active AWS account:

   ```bash
   aws sts get-caller-identity
   aws configure list
   ```

2. Run the bootstrap script from the backend repository root:

   ```bash
   scripts/bootstrap_github_oidc.sh \
     --environment dev \
     --region ap-northeast-2 \
     --github-owner 80-hours-a-week \
     --github-repo StockBrief-be \
     --alarm-emails-json '["REPLACE_WITH_ALERT_EMAIL"]'
   ```

3. Record the generated state bucket, lock table, and deploy role ARN in the PR
   or team handoff. Do not commit credentials or secret values.

4. Replace the placeholder bucket in `infra/terraform/backend.tf` with the
   generated state bucket.

5. Initialize Terraform against the new backend:

   ```bash
   cd infra/terraform
   terraform init -reconfigure
   terraform state list
   ```

6. Keep `envs/dev/deploy.auto.tfvars.json` on safe defaults until VPC, subnet,
   Cognito URL, and Amplify URL values are known.

## Safe Defaults For Free-Tier Dev

- `enable_amplify = false`
- `agentcore_runtime_enabled = false`
- `enable_rds_proxy = false`
- `db_deletion_protection = false`
- `db_skip_final_snapshot = true`
- `db_backup_retention_period = 1`
- Empty subnet lists until the target VPC/subnets are confirmed
- Empty Cognito Hosted UI domain prefix until uniqueness is checked

## Apply Gate

Run `terraform apply` only after all of these are true:

- Active AWS account is the new target account.
- `backend.tf` points to the new state bucket.
- `terraform state list` does not show resources from an old account.
- `terraform plan` contains only expected resources.
- High-cost resources are disabled or explicitly approved.
- RDS dev deletion, final snapshot, and backup settings are set to dev values.
- Secret values will be filled outside git.

## Post-Deploy Smoke

- `GET /v1/health`
- `GET /v1/stocks/candidates`
- `GET /v1/recommendations/candidates`
- `POST /v1/chat`
- Amplify `/recommendations`
- Amplify `/stocks/[ticker]`
- Cognito callback
- `GET /v1/me/watchlist` with a valid token
