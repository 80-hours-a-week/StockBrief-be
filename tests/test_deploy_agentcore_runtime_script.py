from __future__ import annotations

import json
from pathlib import Path

from scripts.deploy_agentcore_runtime import (
    _patch_tfvars,
    _runtime_environment,
    _write_tfvars,
)


def test_agentcore_metadata_patches_external_runtime_tfvars() -> None:
    tfvars = {
        "environment": "dev-owen",
        "agentcore_runtime_external_arn": "",
        "agentcore_runtime_external_id": "",
        "agentcore_runtime_endpoint_name": "",
    }

    changed = _patch_tfvars(
        tfvars,
        {
            "runtime_arn": "arn:aws:bedrock-agentcore:ap-northeast-2:123456789012:runtime/test",
            "runtime_id": "stockbrief_dev_owen_agent-ABCDEFGHIJ",
            "endpoint_name": "stockbrief_dev_owen_default",
        },
    )

    assert changed is True
    assert tfvars["agentcore_runtime_external_arn"].endswith(":runtime/test")
    assert tfvars["agentcore_runtime_external_id"] == "stockbrief_dev_owen_agent-ABCDEFGHIJ"
    assert tfvars["agentcore_runtime_endpoint_name"] == "stockbrief_dev_owen_default"


def test_agentcore_runtime_environment_matches_tfvars() -> None:
    env = _runtime_environment(
        {
            "environment": "dev-owen",
            "aws_region": "ap-northeast-2",
            "bedrock_chat_region": "",
            "bedrock_chat_model_id": "apac.amazon.nova-micro-v1:0",
            "bedrock_chat_max_tokens": 2000,
            "bedrock_chat_temperature": 0.2,
            "bedrock_chat_timeout_seconds": 8,
            "agentcore_runtime_max_turns": 4,
        }
    )

    assert env["APP_ENV"] == "dev-owen"
    assert env["SERVICE_NAME"] == "stockbrief-agent"
    assert env["BEDROCK_CHAT_REGION"] == "ap-northeast-2"
    assert env["BEDROCK_CHAT_MAX_TOKENS"] == "2000"
    assert env["AGENTCORE_RUNTIME_USE_DEV_MODEL"] == "false"


def test_write_tfvars_preserves_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "deploy.auto.tfvars.json"
    _write_tfvars(path, {"environment": "dev-owen"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"environment": "dev-owen"}
