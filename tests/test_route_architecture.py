from pathlib import Path

from app.services.candidate_service import CandidateService


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_public_routes_are_split_by_domain() -> None:
    assert not (REPOSITORY_ROOT / "app/routes.py").exists()
    for route_module in [
        "app/routes/candidates.py",
        "app/routes/stocks.py",
        "app/routes/chat.py",
        "app/routes/evidence.py",
        "app/routes/meta.py",
    ]:
        assert (REPOSITORY_ROOT / route_module).exists()


def test_candidate_business_logic_has_service_layer() -> None:
    assert hasattr(CandidateService, "list_stock_candidates")
    assert hasattr(CandidateService, "list_recommendation_candidates")
