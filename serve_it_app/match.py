from __future__ import annotations

from typing import Dict, List, Tuple

from .models import Provider


def rank_providers(request: Dict[str, object], providers: List[Provider]) -> List[Tuple[Provider, float]]:
    """Return providers sorted by heuristic match score.

    Score weights: skills match (0-1), jobs done, rating. Distance is not
    computed to keep implementation simple; use lat/lon from request later.
    """

    desired_skill = str(request.get("service_type_id", "")).lower()
    results: List[Tuple[Provider, float]] = []
    for provider in providers:
        skill_match = 0.0
        if desired_skill:
            skill_match = 1.0 if desired_skill in [skill.lower() for skill in provider.skills] else 0.5
        score = skill_match * 0.6 + min(provider.rating / 5.0, 1.0) * 0.3 + min(provider.jobs_done / 10.0, 1.0) * 0.1
        results.append((provider, score))
    results.sort(key=lambda pair: pair[1], reverse=True)
    return results
