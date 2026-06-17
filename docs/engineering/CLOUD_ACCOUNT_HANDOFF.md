# Cloud Account Handoff — StockBrief

> 작성일: 2026-06-17
> 이 문서는 "기존 팀원이 연결한 AWS 계정"과의 협업 기준을 정리한다.
> GitHub는 팀 레포를 그대로 사용하며, 코드/문서/Terraform 변경은 branch/PR 워크플로우로 진행한다.

---

## 1. 계정 분리 기준

### "기존 AWS 계정"의 의미

여기서 "기존 계정"은 **기존 팀원이 연결해 둔 AWS 계정 및 리소스**를 의미한다.  
GitHub 자체는 기존 계정 범위가 아니다.

### GitHub 작업 기준

Claude Code / 개인 로컬에서 할 수 있는 GitHub 작업:
- 로컬 branch에서 코드/문서/Terraform 수정
- 테스트·검증 실행 (로컬)
- PR 준비 및 PR body 작성
- PR 올리기 (팀 레포로 push)

오늘 하지 말아야 할 GitHub 작업:
- `main` 직접 push
- PR merge
- GitHub repository/environment variables 직접 변경
- GitHub Actions deploy를 의도적으로 트리거하는 작업
- AWS deploy role 또는 OIDC trust를 GitHub 설정에서 변경

**주의**: `StockBrief-be/.github/workflows/backend-dev-deploy.yml`은 `main` push 시 dev 배포를 실행할 수 있다.  
Terraform/AWS 영향이 있는 PR은 merge 전에 "기존 AWS 계정에 적용해도 되는 변경인지" 팀원이 확인해야 한다.

---

## 2. 기존 팀원 AWS 계정이 필요한 작업

아래 작업은 기존 팀원이 연결해 둔 AWS 계정 접근 또는 AWS 콘솔/권한이 필요하므로 오늘 Claude Code 범위에서 제외한다.

- AWS account `420615923610` 접근
- Terraform remote state bucket/key 확인 (`stockbrief-terraform-state-420615923610-ap-northeast-2`)
- DynamoDB Terraform lock table 확인 (`stockbrief-terraform-locks`)
- 기존 AWS IAM OIDC provider 확인
- GitHub Actions deploy role 확인 (`stockbrief-dev-github-actions-deploy`)
- AWS Secrets Manager 실제 secret 값 입력
- Amplify console-managed app 환경변수 확인/수정
- SNS alarm email subscription confirm
- Cognito Hosted UI domain 실제 생성/수정
- Terraform `apply`로 실제 dev resource 변경
- RDS/RDS Proxy 실제 생성·삭제·snapshot 정책 적용
- 배포 후 AWS 리소스 smoke test

---

## 3. 내가 로컬에서 할 수 있는 작업

- 코드, 문서, Terraform 변수화, migration 초안 작성
- `pytest` 로컬 실행
- `terraform fmt -check`, `terraform init -backend=false`, `terraform validate` 실행 (로컬)
- `python scripts/check_prohibited_terms.py` 실행
- PR-ready 변경 세트 준비 및 PR 올리기

---

## 4. 기존 계정 담당자에게 확인할 항목

| 항목 | 현재 문서 기준 값 | 확인 필요 |
|------|------------------|-----------|
| AWS account id | `420615923610` | 확인 |
| AWS region | `ap-northeast-2` | 확인 |
| Terraform state bucket | `stockbrief-terraform-state-420615923610-ap-northeast-2` | 확인 |
| Terraform state key (dev) | — | 확인 필요 |
| DynamoDB lock table | `stockbrief-terraform-locks` | 확인 |
| GitHub Actions deploy role ARN | `stockbrief-dev-github-actions-deploy` | 확인 |
| `AWS_DEV_DEPLOY_ROLE_ARN` (GitHub variable) | — | 확인 필요 |
| `OPERATIONAL_ALARM_EMAILS_JSON` (GitHub variable) | — | 확인 필요 |
| Amplify app connected branch | `main` (예상) | 확인 |
| Amplify app environment variables | — | 확인 필요 |
| Secrets Manager database secret name/ARN | — | 확인 필요 |
| Secrets Manager external API secret name/ARN | — | 확인 필요 |
| SNS alarm topic ARN | — | 확인 필요 |
| Cognito Hosted UI domain prefix | — | 결정 필요 (전 세계 유일값) |

---

## 5. 기존 계정에서 실행할 작업

PR merge 전에 기존 계정 담당자가 수행해야 할 작업:

1. `terraform state list`로 dev state 확인
2. `terraform plan` 결과 검토 및 공유
3. Secrets Manager placeholder → 실제 secret 값 교체
4. Amplify 환경변수 확인 (API Gateway URL, Cognito 값)
5. SNS subscription confirm (alarm 이메일 수신 확인)
6. Cognito Hosted UI domain prefix 충돌 확인
7. dev `terraform apply` 전 backend.tf state 대상 재확인
8. dev `terraform apply` 실행
9. 배포 후 smoke test 수행

---

## 6. Apply 금지 조건

아래 조건 중 하나라도 해당되면 `terraform apply` 금지:

- [ ] state bucket/key가 불명확하거나 `terraform state list`가 예상 리소스를 가리키지 않는 경우
- [ ] secret 값이 placeholder 상태인 경우
- [ ] Amplify env와 API Gateway URL이 불일치하는 경우
- [ ] `db_deletion_protection = true` + `db_skip_final_snapshot = false`가 dev에 적용되는 경우
- [ ] RDS Proxy enabled 상태에서 `DATABASE_HOST`가 잘못된 endpoint를 가리키는 경우

---

## 7. 배포 후 Smoke Test Checklist

dev 배포 완료 후 아래를 순서대로 확인한다.

```bash
# 1. Health check
GET /v1/health
# 기대: {"status": "ok"}

# 2. 주식 목록
GET /v1/stocks/candidates

# 3. 추천 후보
GET /v1/recommendations/candidates

# 4. Chat (mock)
POST /v1/chat
Content-Type: application/json
{"session_id": "test", "message": "삼성전자 설명해줘"}

# 5. FE — Amplify
브라우저: https://<amplify-url>/recommendations
브라우저: https://<amplify-url>/stocks/005930

# 6. Cognito callback (P1)
Cognito Hosted UI → callback redirect 확인

# 7. Watchlist (P1, JWT 필요)
GET /v1/me/watchlist
Authorization: Bearer <cognito-id-token>
```

---

## 8. Secret/Env 확인 Checklist

Amplify 환경변수 확인:
- [ ] `NEXT_PUBLIC_API_BASE_URL` = API Gateway invoke URL
- [ ] `NEXT_PUBLIC_COGNITO_REGION` = `ap-northeast-2`
- [ ] `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
- [ ] `NEXT_PUBLIC_COGNITO_APP_CLIENT_ID`
- [ ] `NEXT_PUBLIC_COGNITO_HOSTED_UI_DOMAIN`
- [ ] `NEXT_PUBLIC_COGNITO_REDIRECT_URI`

Lambda 환경변수 확인:
- [ ] `DATABASE_HOST` = RDS Proxy endpoint (또는 RDS endpoint if proxy disabled)
- [ ] `DATABASE_PORT` = `5432`
- [ ] `DATABASE_NAME` = `stockbrief`
- [ ] `APP_ENV` = `dev`
- [ ] `COGNITO_USER_POOL_ID`
- [ ] `COGNITO_APP_CLIENT_ID`
- [ ] `COGNITO_ISSUER`
- [ ] `CORS_ALLOWED_ORIGINS`

Secrets Manager:
- [ ] database secret: 실제 password/host 채워짐 (placeholder 아님)
- [ ] external API secret: OpenDART API key, NAVER API key 채워짐
