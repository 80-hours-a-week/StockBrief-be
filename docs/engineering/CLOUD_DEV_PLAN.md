# Cloud Dev Plan — StockBrief

> 작성일: 2026-06-17
> 대상 환경: dev (ap-northeast-2, AWS account 420615923610)
> 이 문서는 설계/계획 전용이다. `terraform apply`나 실제 AWS 리소스 변경은 수행하지 않는다.

---

## 1. 프로젝트 Cloud 방향

StockBrief는 국내 주식 검토 후보 추천 서비스다. 공개 데이터 기반의 deterministic score engine이 점수를 계산하고, AI는 이미 계산된 결과만 설명한다. 아키텍처는 서버리스 우선, 비용 가시성 우선, MVP는 guest-first로 운영한다.

**핵심 원칙**

- 투자 조언 서비스가 아니다. AI는 score/evidence/risk_tag를 설명할 뿐이다.
- 서버리스 우선 (Lambda + API Gateway HTTP API). 컨테이너 런타임은 조건부.
- Terraform IaC, GitHub Actions OIDC CI/CD, 팀 레포 PR 워크플로우.
- dev/prod 비용 정책은 Terraform 변수로 명확히 분리한다.

---

## 2. Architecture Tool Map

### FE

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| Next.js App Router | 필수 | |
| React + TypeScript | 필수 | |
| Tailwind CSS | 필수 | |
| Vitest | 필수 | |
| ESLint | 필수 | |

### FE Hosting

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| AWS Amplify Hosting | 필수 | console-managed, Terraform 외부 |
| CloudFront custom distribution | 선택 | Amplify 내장 CDN으로 MVP 충분 |

### BE

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| FastAPI + Pydantic | 필수 | |
| SQLAlchemy + Alembic | 필수 | |
| PyJWT | 필수 | |
| pytest | 필수 | |

### BE Runtime

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| API Gateway HTTP API | 필수 | WAF 직접 연결 불가. throttling + JWT authorizer로 1차 방어 |
| Lambda (Mangum) | 필수 | |
| API Gateway REST API | 비추천 | WAF가 꼭 필요한 시점에 재검토 |

### DB

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| RDS PostgreSQL 16 | 필수 | |
| Alembic migration | 필수 | |
| RDS Proxy | 조건부 | `enable_rds_proxy` toggle로 dev는 선택, prod는 권장 |

### Auth

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| Cognito User Pool | 필수 | |
| API Gateway JWT Authorizer | 필수 | |
| PyJWT fallback (local/test) | 필수 | |

### Secrets

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| Secrets Manager | 필수 | |
| customer-managed KMS | 조건부 | prod 또는 규정 요구 시 |

### IaC/CI

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| Terraform | 필수 | |
| GitHub Actions OIDC | 필수 | deploy role: `stockbrief-dev-github-actions-deploy` |
| staging/prod required reviewers | 조건부 | staging 진입 시점에 설정 |

### Observability

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| CloudWatch Logs | 필수 | Phase 2 완료 기준 |
| CloudWatch Alarms | 필수 | Phase 2 완료 기준 |
| CloudWatch Dashboard | 필수 | Phase 2 완료 기준 |
| SNS email alert | 필수 | Phase 2 완료 기준 |
| X-Ray / ADOT | 조건부 | Bedrock provider 붙은 후 |
| Glue + Athena | 조건부 | S3 raw 누적 후 ad hoc 분석 필요 시 |

### Security

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| API Gateway throttling | 필수 | |
| Cognito JWT Authorizer | 필수 | |
| CORS allowlist | 필수 | |
| IAM least privilege | 필수 | |
| WAF | 조건부 | Amplify/CloudFront 또는 별도 CloudFront API proxy 구성 시 |

**WAF 정책 요약**: HTTP API에 WAF를 직접 붙이는 계획은 금지. WAF는 AWS WAF가 지원하는 리소스(CloudFront, ALB, API Gateway REST API 등)에만 연결 가능하며, HTTP API는 지원 범위 외다. MVP에서는 throttling + JWT Authorizer + CORS + IAM으로 1차 방어를 구성한다.

참고: https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works-resources.html

### Data / Ingestion

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| EventBridge Scheduler | 필수 (Phase 3) | ingestion 트리거 |
| ingestion Lambda | 필수 (Phase 3) | |
| SQS DLQ | 필수 (Phase 3) | |
| S3 raw storage | 필수 (Phase 3) | |
| RDS (ingestion target) | 필수 | |
| Glue / Athena | 조건부 | Phase 3 이후 |

### AI

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| Bedrock direct provider | 필수 (Phase 5) | mock 다음 단계 |
| AgentCore Runtime | 조건부 | 조건 충족 시 Phase 5 후반 |
| Vector RAG (PostgreSQL pgvector) | Phase 5 후반 | embedding dimension 확정 후 |

### Cost

| 도구 | 필수 여부 | 비고 |
|------|-----------|------|
| AWS Budgets | 필수 | |
| Cost Anomaly Detection | 필수 | |
| project-level CloudTrail | 조건부 | 운영 성숙 후 |

---

## 3. Phase 계획

### Phase 1 — dev 배포 안정화

목표: dev 환경에서 API가 정상 응답하는 것.

- [ ] 기존 팀원 AWS 계정 handoff 완료 (→ CLOUD_ACCOUNT_HANDOFF.md 참조)
- [ ] Terraform state bucket/key 확인
- [ ] RDS dev 정책 변수 (`db_deletion_protection = false`, `db_skip_final_snapshot = true`, `db_backup_retention_period = 1`) 적용
- [ ] `enable_rds_proxy` toggle 확인 (disabled 시 DATABASE_HOST = RDS endpoint)
- [ ] dev secret placeholder 교체
- [ ] Amplify app env 확인
- [ ] `GET /v1/health` smoke test 통과

### Phase 2 — 운영 품질 보강

목표: CloudWatch Logs/Alarms/Dashboard 필수 범위 완료.

필수 대시보드 지표:
- Lambda: errors, throttles, duration p95/p99
- API Gateway: 4xx, 5xx, latency
- RDS: CPU, storage, connections
- ingestion: success/failure count (Phase 3 연계)

- [ ] SNS email subscription confirm
- [ ] CloudWatch Dashboard 생성 확인
- [ ] Alarm 임계값 문서화

조건부 (Phase 2 이후):
- X-Ray/ADOT: Bedrock provider 연결 후
- Glue/Athena: S3 raw 누적 후

### Phase 3 — 실데이터 ingestion

목표: EventBridge Scheduler + ingestion Lambda + S3 raw + ingestion_runs idempotency.

idempotency 기준 (provider별 upsert key):

| 소스 | upsert 기준 |
|------|------------|
| OpenDART disclosure | `provider + receipt_no` |
| NAVER news | `provider + source_url_hash` 또는 provider article id |
| KRX price | `ticker + trade_date + source` |
| financial statement | `ticker + fiscal_year + fiscal_period + source_document_id` |
| source document | `source_type + source_name + external_id`, 없으면 `content_hash` |
| score | `ticker + as_of_date + score_version` |

모든 ingestion row에 남길 키:
- `run_id` (→ ingestion_runs 참조)
- `provider`
- `ticker`
- `source_date`
- `request_hash`

ingestion_runs 테이블 status:
- `started` → `succeeded` / `partial_failed` / `failed` / `replayed`

### Phase 4 — Cognito 계정/동기화

목표: 로그인 · 관심종목 서버 동기화.

- Cognito Hosted UI 도메인 prefix 결정 (전 세계 유일값)
- `users`, `user_preferences`, `watchlists` 테이블 (0002 migration에 포함)
- JWT authorizer → `/v1/me/*` 보호
- FE localStorage watchlist → server sync migration UX

### Phase 5 — AI 강화

목표: Bedrock direct provider → mock 대체.

순서:
1. mock composer 유지 (현재)
2. Bedrock direct provider 추가 (`provider=bedrock`)
3. AgentCore Runtime은 조건부 PoC

AI 입력 허용 범위:
- `score`, `recommendation_reasons`, `evidence`, `risk_tags`, `data_freshness`, `missing_data`

AI 절대 금지:
- score 생성/변경
- 투자 판단 지시
- 가격 지점 제시
- 수익 확정 표현

AgentCore Runtime 도입 조건 (모두 충족 시):
1. Bedrock direct provider가 dev에서 안정화됨
2. 장시간 세션 격리 또는 agent runtime 필요성이 확인됨
3. ECR image / runtime endpoint / IAM / observability 비용이 승인됨

Vector RAG 선행 작업 (Phase 5 후반):
- PostgreSQL vector extension (`pgvector`)
- embedding dimension 확정
- `evidence_chunks.embedding` 컬럼 추가
- vector index strategy 결정
- Alembic migration

---

## 4. WAF / HTTP API 정책 (상세)

**현재 BE runtime**: API Gateway HTTP API + Lambda + Mangum

**정책**:
- MVP에서 HTTP API 유지. REST API 전환은 MVP에서 비추천.
- WAF를 API Gateway HTTP API에 직접 붙이는 계획 금지 (AWS가 HTTP API를 WAF 보호 대상으로 지원하지 않음).
- HTTP API 1차 방어 구성:
  1. API Gateway throttling (route-level 및 stage-level)
  2. Cognito JWT Authorizer (보호 경로)
  3. CORS allowlist (`CORS_ALLOWED_ORIGINS` 환경변수)
  4. IAM least privilege (Lambda execution role)

**WAF 조건부 도입 경로**:
- Amplify/CloudFront 앞단 보호가 필요할 때
- API Gateway 앞에 별도 CloudFront API proxy를 둘 때
- API Gateway를 REST API로 전환할 때

---

## 5. RDS dev/prod 비용 정책

환경별 권장값:

| 변수 | dev | staging | prod |
|------|-----|---------|------|
| `db_deletion_protection` | `false` | `false` | `true` |
| `db_skip_final_snapshot` | `true` | `true` | `false` |
| `db_backup_retention_period` | `1` | `3` | `7` |
| `db_instance_class` | `db.t4g.micro` | `db.t4g.small` | `db.t4g.medium` |

**apply 금지 조건**: `db_deletion_protection = true` + `db_skip_final_snapshot = false`가 dev에 적용되는 경우 apply 금지.

---

## 6. RDS Proxy Toggle 정책

`enable_rds_proxy` 변수로 on/off.

| proxy 상태 | `DATABASE_HOST` |
|-----------|----------------|
| enabled | RDS Proxy endpoint |
| disabled | RDS endpoint |

- dev는 비용 절감을 위해 `enable_rds_proxy = false` 허용.
- prod는 Lambda cold-start 연결 안정성을 위해 `enable_rds_proxy = true` 권장.
- proxy disabled 시 Lambda connection pool 설정을 보수적으로 유지 (`pool_size=2`, `max_overflow=3`).

---

## 7. Observability 범위 정리

### Phase 2 필수 (CloudWatch only)

- CloudWatch Logs: Lambda, API Gateway, RDS
- CloudWatch Alarms: errors, throttles, 5xx, CPU
- CloudWatch Dashboard: 위 지표 시각화
- SNS email alert: alarm 트리거 시 이메일 수신

### 조건부 / Post-MVP

| 도구 | 도입 조건 |
|------|-----------|
| X-Ray | Bedrock provider 연결 후 트레이스 필요 시 |
| ADOT | X-Ray와 동시 |
| Glue Data Catalog | S3 raw 누적 + ad hoc 품질 분석 반복 요청 시 |
| Athena | Glue와 동시 |
| AgentCore Observability | AgentCore Runtime 도입 후 |
| project-level CloudTrail | 운영 성숙 + 보안 감사 필요 시 |
| customer-managed KMS | prod 규정 요구 시 |

---

## 8. AI 강화 정책 (Bedrock direct 우선)

현재 상태: mock composer (`provider=mock`)
다음 단계: Bedrock direct provider (`provider=bedrock`)
조건부: AgentCore Runtime

**내부 provider flag**:

```
CHAT_PROVIDER=mock    # 현재 기본값
CHAT_PROVIDER=bedrock # Phase 5 전환
```

**`/v1/chat` public contract 불변**: 내부 provider가 바뀌어도 API 응답 구조는 동일하게 유지.

---

## 9. 내일 Codex 리팩토링 예정 범위

PR 분리 권장:

**PR 1**: cloud plan/docs/account handoff
- `docs/engineering/CLOUD_DEV_PLAN.md`
- `docs/engineering/CLOUD_ACCOUNT_HANDOFF.md`
- `docs/engineering/DB_SCHEMA.md` (ingestion_runs 섹션 추가)

**PR 2**: Terraform/RDS/ingestion schema changes
- `infra/terraform/modules/rds/variables.tf` (신규 변수)
- `infra/terraform/modules/rds/main.tf` (변수 적용)
- `infra/terraform/variables.tf` (root 변수)
- `infra/terraform/main.tf` (module 전달)
- `infra/terraform/envs/*/terraform.tfvars.example` (환경별 값)
- `migrations/versions/0003_ingestion_runs.py`
- `app/orm.py` (IngestionRun 모델)
- `tests/test_schema.py` (ingestion_runs 검증)

내일 Codex 체크리스트:
- [ ] Terraform 변수명/default/module input/output 정리
- [ ] `enable_rds_proxy = false` 경로에서 `DATABASE_HOST = RDS endpoint` 검증
- [ ] tfvars example과 docs 일치화
- [ ] ingestion_runs migration/ORM/test 최종 정리
- [ ] unique/upsert 기준 테스트 추가
- [ ] 문서 중복/충돌 제거
- [ ] CI 전체 검증 (pytest, terraform validate, prohibited terms)
- [ ] PR body 정리
