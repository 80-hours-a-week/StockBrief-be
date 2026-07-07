"""Backward-compatible re-exports for external provider clients.

The implementation moved into ``base.py`` / ``opendart.py`` / ``naver.py`` /
``krx.py``. This module re-exports every name that was previously defined
here so existing imports (``from app.services.external.clients import ...``)
and monkeypatch targets keep working unchanged.
"""

from __future__ import annotations

from app.services.external.base import (
    BaseExternalApiClient,
    _cache_payload,
    _duration_ms,
    _error_code,
    _iter_dicts,
    _missing_data,
    _request_with_backoff,
    _result_from_cached,
)
from app.services.external.krx import KRX_PROVIDER, KrxClient, _krx_market_key
from app.services.external.naver import (
    NAVER_PROVIDER,
    NaverNewsClient,
    _fallback_news_payload,
    _normalize_naver_payload,
)
from app.services.external.opendart import (
    OPENDART_PROVIDER,
    OpenDartClient,
    _opendart_status_ok,
)

__all__ = [
    "BaseExternalApiClient",
    "KRX_PROVIDER",
    "KrxClient",
    "NAVER_PROVIDER",
    "NaverNewsClient",
    "OPENDART_PROVIDER",
    "OpenDartClient",
]
