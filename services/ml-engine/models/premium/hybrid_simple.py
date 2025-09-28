from typing import List, Dict, Tuple
from uuid import UUID
import numpy as np


class SimpleHybridModel:
    def __init__(self, cf_model, content_model, cf_weight: float = 0.6):
        self.cf_model = cf_model
        self.content_model = content_model
        self.cf_weight = cf_weight
        self.content_weight = 1.0 - cf_weight

    def recommend(
        self,
        user_id: UUID,
        k: int = 20,
        exclude_tracks: List[UUID] = None,
        user_track_history: List[UUID] = None
    ) -> List[Tuple[UUID, float]]:
        cf_recommendations = {}
        if hasattr(self.cf_model, 'recommend'):
            cf_recs = self.cf_model.recommend(user_id, k=k*2, exclude_tracks=exclude_tracks)
            for track_id, score in cf_recs:
                cf_recommendations[track_id] = score

        content_recommendations = {}
        if user_track_history and self.content_model:
            taste_profile = self.content_model.build_user_taste_profile(user_track_history)

            if taste_profile and 'features' in taste_profile:
                content_recs = self.content_model.recommend_by_features(
                    target_features=taste_profile['features'],
                    k=k*2,
                    exclude_tracks=exclude_tracks
                )
                for track_id, score in content_recs:
                    content_recommendations[track_id] = score

        all_track_ids = set(cf_recommendations.keys()) | set(content_recommendations.keys())

        hybrid_scores = []
        for track_id in all_track_ids:
            cf_score = cf_recommendations.get(track_id, 0.0)
            content_score = content_recommendations.get(track_id, 0.0)

            if track_id in cf_recommendations and track_id in content_recommendations:
                hybrid_score = (self.cf_weight * cf_score + self.content_weight * content_score)
            elif track_id in cf_recommendations:
                hybrid_score = self.cf_weight * cf_score
            else:
                hybrid_score = self.content_weight * content_score

            hybrid_scores.append((track_id, hybrid_score))

        hybrid_scores.sort(key=lambda x: x[1], reverse=True)

        return hybrid_scores[:k]

    def save(self, path: str):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'cf_weight': self.cf_weight,
                'content_weight': self.content_weight,
            }, f)

    @classmethod
    def load(cls, path: str, cf_model, content_model):
        import pickle
        with open(path, 'rb') as f:
            data = pickle.load(f)

        return cls(
            cf_model=cf_model,
            content_model=content_model,
            cf_weight=data['cf_weight']
        )