from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.preference.embeddings import KeywordEmbeddingModel
from src.types import Candidate, Recommendation
from src.utils import normalize_url


class RecommendationScorer:
    def __init__(self, feedback_adjustments: Optional[Dict[str, float]] = None):
        self.model = KeywordEmbeddingModel()
        self.feedback_adjustments = feedback_adjustments or {}

    def score(self, candidate: Candidate, category: str, profile: Dict) -> Recommendation:
        category_profile = next((p for p in profile.get("categories", []) if p.get("category") == category), {})
        candidate_text = " ".join([candidate.title, candidate.text, " ".join(candidate.tags)])
        profile_text = " ".join(category_profile.get("positive_features", []))
        similarity = self.model.similarity(self.model.embed(candidate_text), self.model.embed(profile_text))
        category_match = min(1.0, similarity * 2.0)
        preferred_domains = set(category_profile.get("preferred_domains", []))
        author_domain = 1.0 if candidate.domain in preferred_domains else 0.2 if candidate.author else 0.0
        visual = 1.0 if candidate.media_type in {"image", "video"} else 0.35
        usefulness = self._usefulness(candidate_text)
        novelty = 0.9 if candidate.discovery else 0.45
        freshness = self._freshness(candidate)
        reliability = self._reliability(candidate_text, candidate.domain)
        discovery_value = 1.0 if candidate.discovery else 0.35
        breakdown = {
            "semantic_similarity": 30 * min(1.0, similarity),
            "category_match": 15 * category_match,
            "author_domain": 10 * author_domain,
            "visual_match": 10 * visual,
            "usefulness": 10 * usefulness,
            "novelty": 10 * novelty,
            "freshness": 5 * freshness,
            "reliability": 5 * reliability,
            "discovery_value": 5 * discovery_value,
        }
        penalties = self._penalties(candidate_text)
        raw = sum(breakdown.values()) - penalties
        raw += self.feedback_adjustments.get(normalize_url(candidate.url), 0.0)
        score = max(0, min(100, int(round(raw))))
        reasons = self._reasons(candidate, category_profile, similarity, usefulness, reliability)
        novelty_notes = ["既存カテゴリを横断する候補"] if candidate.discovery else ["直近保存傾向に近い候補"]
        destination = "discovery" if candidate.discovery else "high" if score >= 78 and reliability >= 0.5 else "inbox"
        if self._health_risk(candidate_text) and reliability < 0.8:
            destination = "inbox"
            score = min(score, 69)
        return Recommendation(candidate, score, category, reasons, novelty_notes, breakdown, destination)

    @staticmethod
    def _freshness(candidate: Candidate) -> float:
        if not candidate.published_at:
            return 0.25
        hours = (datetime.now(timezone.utc) - candidate.published_at).total_seconds() / 3600
        return 1.0 if hours <= 24 else 0.6 if hours <= 48 else 0.1

    @staticmethod
    def _usefulness(text: str) -> float:
        words = ["tips", "breakdown", "case", "study", "utility", "functional", "参考", "制作", "実用"]
        return min(1.0, 0.35 + 0.2 * sum(word in text.lower() for word in words))

    @staticmethod
    def _reliability(text: str, domain: str) -> float:
        lower = text.lower()
        if any(word in lower for word in ["miracle", "cure", "no evidence", "根拠なし"]):
            return 0.1
        if domain.endswith(".edu") or domain.endswith(".go.jp"):
            return 1.0
        return 0.75

    @staticmethod
    def _penalties(text: str) -> float:
        lower = text.lower()
        penalty = 0.0
        for word in ["affiliate", "coupon", "buy now", "まとめ", "転載", "sale"]:
            if word in lower:
                penalty += 12
        if len(lower.strip()) < 20:
            penalty += 15
        return penalty

    @staticmethod
    def _health_risk(text: str) -> bool:
        return any(word in text.lower() for word in ["health", "健康", "cure", "posture"])

    @staticmethod
    def _reasons(candidate: Candidate, category_profile: Dict, similarity: float, usefulness: float, reliability: float) -> List[str]:
        reasons = []
        if similarity > 0.1:
            reasons.append(f"{category_profile.get('category', '既存カテゴリ')}の保存語彙と近い")
        if candidate.author:
            reasons.append(f"作者または発信元を抽出できる: {candidate.author}")
        if usefulness >= 0.7:
            reasons.append("制作や生活への応用可能性が高い")
        if candidate.media_type in {"image", "video"}:
            reasons.append("視覚・映像表現の評価対象として扱える")
        if reliability < 0.5:
            reasons.append("信頼性に注意が必要な表現を含むため高精度枠から除外")
        return reasons or ["候補本文と既存プロファイルに弱い関連がある"]
