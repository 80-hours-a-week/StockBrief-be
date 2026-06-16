# Deployment Bootstrap

This document explains how to prepare a new AWS account or environment so the
backend can deploy from GitHub Actions without long-lived AWS access keys.

The current dev account is already bootstrapped:

- AWS account: `420615923610`
- Region: `ap-northeast-2`
- Terraform state bucket: `stockbrief-terraform-state-420615923610-ap-northeast-2`
- Terraform lock table: `stockbrief-terraform-locks`
- GitHub Actions deploy role: `stockbrief-dev-github-actions-deploy`
- Frontend Amplify app: console-managed, not Terraform-managed

## Why Bootstrap Is One-Time

GitHub Actions can deploy after it can assume an AWS IAM role through OIDC. The
first OIDC provider, IAM role, Terraform state bucket, and lock table cannot be
created by that role because it does not exist yet.

For a new AWS account, run the bootstrap script once with an administrator or
platform-admin AWS identity. After that, pushes to `main` can deploy through
GitHub Actions.

AWS recommends using an IAM OIDC provider and short-term role credentials for
GitHub Actions instead of storing long-lived IAM user keys. The provider URL must
be lowercase: `https://token.actions.githubusercontent.com`, and the audience is
`sts.amazonaws.com`.

## Prerequisites

- AWS CLI authenticated to the target AWS account.
- GitHub CLI authenticated with permission to write repository variables.
- Permission to create or update IAM OIDC providers, IAM roles, S3 buckets, and
  DynamoDB tables in the target AWS account.
- Permission to set variables on `80-hours-a-week/StockBrief-be`.

Check the active AWS account before running:

```bash
aws sts get-caller-identity
```

Check GitHub CLI authentication:

```bash
gh auth status -h github.com
```

## Bootstrap Command

Run from the backend repository root:

```bash
scripts/bootstrap_github_oidc.sh \
  --environment dev \
  --region ap-northeast-2 \
  --github-owner 80-hours-a-week \
  --github-repo StockBrief-be \
  --alarm-emails-json '["ops@example.com"]'
```

The script creates or updates:

- S3 remote Terraform state bucket.
- DynamoDB Terraform lock table.
- IAM OIDC provider for GitHub Actions.
- IAM deploy role scoped to `80-hours-a-week/StockBrief-be` `main`.
- GitHub Environment named `dev` with a custom deployment branch policy that
  allows only `main`.
- GitHub repository variables:
  - `AWS_DEV_DEPLOY_ROLE_ARN`
  - `OPERATIONAL_ALARM_EMAILS_JSON`

The deploy role policy is intentionally broad enough for the current dev
Terraform deployment. Tighten it after the deployment surface stabilizes.

`--alarm-emails-json` must be valid JSON and must be an array of strings. The
script validates this with Python before writing the GitHub repository variable.

## After Bootstrap

Make sure Terraform uses the state backend printed by the script. Terraform
backend configuration is evaluated during `terraform init`, before regular
variables are loaded, so the selected backend is an operational choice that must
be checked explicitly.

```hcl
terraform {
  backend "s3" {
    bucket         = "stockbrief-terraform-state-<account-id>-<region>"
    key            = "stockbrief/dev/terraform.tfstate"
    region         = "<region>"
    dynamodb_table = "stockbrief-terraform-locks"
    encrypt        = true
  }
}
```

Environment state convention:

| Environment | Backend key | Expected use |
| --- | --- | --- |
| `dev` | `stockbrief/dev/terraform.tfstate` | Current automated backend deployment |
| `staging` | `stockbrief/staging/terraform.tfstate` | Future pre-production environment |
| `prod` | `stockbrief/prod/terraform.tfstate` | Future production environment |

Use a separate account, bucket, or key per environment. Do not point staging or
prod at the dev state key.

When switching an existing local checkout to a different backend:

- Use `terraform init -reconfigure` when the target backend is empty or you are
  intentionally selecting a different existing state.
- Use `terraform init -migrate-state` only when moving the same state to a new
  backend location.
- Never run `terraform apply` after changing `backend.tf` until
  `terraform state list` shows the expected environment resources.

Then check the dev deploy variable file:

```text
infra/terraform/envs/dev/deploy.auto.tfvars.json
```

Confirm these values match the target AWS account:

- `aws_region`
- `vpc_id`
- `db_subnet_ids`
- `lambda_subnet_ids`
- `cors_allowed_origins`
- `cognito_callback_urls`
- `cognito_logout_urls`
- `cognito_hosted_ui_domain_prefix`

For the current approach, keep this value:

```json
"enable_amplify": false
```

Amplify Hosting is managed from the AWS console. Backend resources, RDS, Lambda,
API Gateway, Cognito, Secrets Manager, and alarms are managed by Terraform.

## Deployment Flow After Bootstrap

1. Merge backend changes into `main`.
2. GitHub Actions runs `backend-dev-deploy` in the `dev` GitHub Environment.
3. The workflow assumes `AWS_DEV_DEPLOY_ROLE_ARN` through OIDC.
4. The workflow packages Lambda, runs Terraform plan, and applies the dev stack.
5. Update Secrets Manager values outside git when keys or DB connection values
   change.

Because `backend-dev-deploy` uses `environment: dev`, the OIDC trust policy uses
this subject:

```text
repo:80-hours-a-week/StockBrief-be:environment:dev
```

The branch restriction is enforced by the GitHub Environment deployment branch
policy. The bootstrap script configures the `dev` environment to allow only the
`main` branch.

The dev workflow uses `infra/terraform/backend.tf`, so it always targets the
backend committed in that file. If a new environment needs a different backend,
create a dedicated workflow or update the backend configuration in the same PR
as the environment tfvars change.

`AWS_DEV_DEPLOY_ROLE_ARN` and `OPERATIONAL_ALARM_EMAILS_JSON` may live as
repository variables or `dev` environment variables. Prefer environment
variables when the repository has multiple deploy environments. Add GitHub
Environment required reviewers later if the team wants manual approval before
dev apply.

## Deploy Role Permission Model

The bootstrap script creates a GitHub Actions deploy role for Terraform-driven
backend changes. The role is separate from the administrator identity used to run
bootstrap:

- Bootstrap identity: creates the first state bucket, lock table, OIDC provider,
  deploy role, and GitHub variables.
- Deploy role: assumed by GitHub Actions jobs that target the `dev` Environment.
  The `dev` Environment branch policy allows only `main` deployments.

The deploy role keeps Terraform state bucket and lock table permissions scoped
to exact ARNs. Service deployment actions are enumerated instead of using broad
service wildcards such as `lambda:*` or `iam:*`. Some create, describe, and tag
APIs still require `Resource: "*"` because the resource ARN is not known before
creation or the AWS API does not support resource-level permissions for that
operation.

After changing Terraform resources, re-run:

```bash
scripts/bootstrap_github_oidc.sh --alarm-emails-json '["ops@example.com"]'
```

Then verify the updated role with a real `backend-dev-deploy` workflow run.

## New Environment Checklist

- Run the bootstrap script once in the target AWS account.
- Update `infra/terraform/backend.tf` for that account and region.
- Update `infra/terraform/envs/dev/deploy.auto.tfvars.json` for that network and
  frontend URL.
- Run `terraform init -reconfigure` or `terraform init -migrate-state` according
  to the backend change type.
- Confirm `terraform state list` points to the intended environment before
  applying.
- Confirm SNS alert email subscriptions after Terraform creates them.
- Fill secret values in AWS Secrets Manager. Do not commit secret values.
- Keep FE Amplify app setup in the console unless the team decides to manage
  Amplify with Terraform later.
