from typing import List, Dict, Optional
from uuid import UUID
import os

from config import Config, ModelTier
from models.base import CollaborativeFilter, PopularityModel, GenreBasedModel
from models.premium import ContentBasedModel, SimpleHybridModel, DailyMixGenerator
from models.enterprise import NeuralCF, TasteProfiler
from utils.redis_client import get_redis_client, get_cached_recommendations, cache_recommendations
from utils.db import get_db_connection, fetch_user_play_history


class RecommendationEngine:
    def __init__(self):
        self.models = {}
        self.redis_client = None
        self.model_paths = Config.MODEL_SAVE_PATH

        self._load_models()

    def _load_models(self):
        free_path = os.path.join(self.model_paths, "free")
        starter_path = os.path.join(self.model_paths, "starter")
        pro_path = os.path.join(self.model_paths, "pro")

        if os.path.exists(os.path.join(free_path, "collaborative_filter.pt")):
            try:
                self.models['collaborative_filter'] = CollaborativeFilter.load(
                    os.path.join(free_path, "collaborative_filter.pt")
                )
            except Exception as e:
                print(f"Failed to load collaborative_filter: {e}")

        if os.path.exists(os.path.join(free_path, "popularity.pkl")):
            try:
                self.models['popularity'] = PopularityModel.load(
                    os.path.join(free_path, "popularity.pkl")
                )
            except Exception as e:
                print(f"Failed to load popularity: {e}")

        if os.path.exists(os.path.join(free_path, "genre_based.pkl")):
            try:
                self.models['genre_based'] = GenreBasedModel.load(
                    os.path.join(free_path, "genre_based.pkl")
                )
            except Exception as e:
                print(f"Failed to load genre_based: {e}")

        if os.path.exists(os.path.join(starter_path, "content_based.pkl")):
            try:
                self.models['content_based'] = ContentBasedModel.load(
                    os.path.join(starter_path, "content_based"),
                    use_gpu=Config.ENABLE_GPU
                )
            except Exception as e:
                print(f"Failed to load content_based: {e}")

        if os.path.exists(os.path.join(starter_path, "daily_mix.pkl")):
            try:
                self.models['daily_mix'] = DailyMixGenerator.load(
                    os.path.join(starter_path, "daily_mix.pkl")
                )
            except Exception as e:
                print(f"Failed to load daily_mix: {e}")

        if os.path.exists(os.path.join(pro_path, "neural_cf.pt")):
            try:
                self.models['neural_cf'] = NeuralCF.load(
                    os.path.join(pro_path, "neural_cf.pt"),
                    device='cuda' if Config.ENABLE_GPU else 'cpu'
                )
            except Exception as e:
                print(f"Failed to load neural_cf: {e}")

        if os.path.exists(os.path.join(pro_path, "taste_profiler.pkl")):
            try:
                self.models['taste_profiler'] = TasteProfiler.load(
                    os.path.join(pro_path, "taste_profiler.pkl")
                )
            except Exception as e:
                print(f"Failed to load taste_profiler: {e}")

        try:
            self.redis_client = get_redis_client()
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")

    async def get_recommendations(
        self,
        user_id: UUID,
        limit: int = 20,
        tier: ModelTier = ModelTier.FREE,
        filters: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        if self.redis_client:
            cached = get_cached_recommendations(self.redis_client, user_id)
            if cached:
                return cached[:limit]

        recommendations = []

        if tier == ModelTier.FREE:
            recommendations = await self._get_free_recommendations(user_id, limit, filters)
        elif tier == ModelTier.STARTER:
            recommendations = await self._get_starter_recommendations(user_id, limit, filters)
        elif tier == ModelTier.PRO:
            recommendations = await self._get_pro_recommendations(user_id, limit, filters, context)
        elif tier == ModelTier.ENTERPRISE:
            recommendations = await self._get_enterprise_recommendations(user_id, limit, filters, context)

        if self.redis_client and recommendations:
            cache_recommendations(self.redis_client, user_id, recommendations)

        return recommendations

    async def _get_free_recommendations(
        self,
        user_id: UUID,
        limit: int,
        filters: Optional[Dict]
    ) -> List[Dict]:
        recommendations = []

        if 'collaborative_filter' in self.models:
            cf_recs = self.models['collaborative_filter'].recommend(user_id, k=limit)
            for track_id, score in cf_recs:
                recommendations.append({
                    'track_id': track_id,
                    'score': score,
                    'reason': 'Users with similar taste also enjoyed this',
                    'model_used': 'collaborative_filter'
                })

        if not recommendations and 'popularity' in self.models:
            pop_recs = self.models['popularity'].recommend_popular(k=limit)
            for track_id, score in pop_recs:
                recommendations.append({
                    'track_id': track_id,
                    'score': score,
                    'reason': 'Popular right now',
                    'model_used': 'popularity'
                })

        return recommendations[:limit]

    async def _get_starter_recommendations(
        self,
        user_id: UUID,
        limit: int,
        filters: Optional[Dict]
    ) -> List[Dict]:
        recommendations = []

        conn = await get_db_connection()
        user_history = await fetch_user_play_history(conn, user_id, limit=100)
        await conn.close()

        if 'content_based' in self.models and user_history:
            taste_profile = self.models['content_based'].build_user_taste_profile(user_history)

            if taste_profile and 'features' in taste_profile:
                content_recs = self.models['content_based'].recommend_by_features(
                    target_features=taste_profile['features'],
                    k=limit,
                    exclude_tracks=user_history
                )
                for track_id, score in content_recs:
                    recommendations.append({
                        'track_id': track_id,
                        'score': score,
                        'reason': 'Matches your audio taste',
                        'model_used': 'content_based'
                    })

        if not recommendations:
            return await self._get_free_recommendations(user_id, limit, filters)

        return recommendations[:limit]

    async def _get_pro_recommendations(
        self,
        user_id: UUID,
        limit: int,
        filters: Optional[Dict],
        context: Optional[Dict]
    ) -> List[Dict]:
        recommendations = []

        if 'neural_cf' in self.models:
            ncf_recs = self.models['neural_cf'].recommend(user_id, k=limit)
            for track_id, score in ncf_recs:
                recommendations.append({
                    'track_id': track_id,
                    'score': float(score),
                    'reason': 'Deep learning prediction based on your taste',
                    'model_used': 'neural_cf'
                })

        if not recommendations:
            return await self._get_starter_recommendations(user_id, limit, filters)

        return recommendations[:limit]

    async def _get_enterprise_recommendations(
        self,
        user_id: UUID,
        limit: int,
        filters: Optional[Dict],
        context: Optional[Dict]
    ) -> List[Dict]:
        return await self._get_pro_recommendations(user_id, limit, filters, context)

    async def get_similar_tracks(
        self,
        track_id: UUID,
        limit: int = 10,
        use_audio: bool = True,
        min_similarity: float = 0.7
    ) -> List[Dict]:
        if 'content_based' not in self.models:
            return []

        similar = self.models['content_based'].find_similar(
            track_id=track_id,
            k=limit,
            min_similarity=min_similarity
        )

        return [
            {
                'track_id': tid,
                'score': similarity,
                'reason': f'Audio similarity: {similarity:.2%}',
                'model_used': 'content_based'
            }
            for tid, similarity in similar
        ]

    async def generate_daily_mixes(
        self,
        user_id: UUID,
        mix_count: int = 6,
        tracks_per_mix: int = 50
    ) -> List[Dict]:
        if 'daily_mix' not in self.models:
            return []

        conn = await get_db_connection()
        user_history = await fetch_user_play_history(conn, user_id)
        await conn.close()

        mixes = self.models['daily_mix'].generate_mixes(
            user_id=user_id,
            user_played_tracks=user_history,
            mix_count=mix_count,
            tracks_per_mix=tracks_per_mix
        )

        return mixes

    async def compute_taste_profile(self, user_id: UUID) -> Dict:
        if 'taste_profiler' not in self.models:
            return {}

        conn = await get_db_connection()

        from utils.db import fetch_interactions, fetch_tracks, fetch_audio_features

        interactions = await fetch_interactions(conn, user_id=user_id, limit=1000)

        track_ids = list(set(i['track_id'] for i in interactions))
        tracks = await fetch_tracks(conn, track_ids=track_ids)
        audio_features = await fetch_audio_features(conn, track_ids=track_ids)

        await conn.close()

        profile = self.models['taste_profiler'].build_profile(
            user_id=user_id,
            interactions=interactions,
            tracks=tracks,
            audio_features=audio_features
        )

        return profile

    async def generate_radio(
        self,
        seed_type: str,
        seed_id: Optional[UUID],
        seed_genre: Optional[str],
        diversity: float,
        limit: int
    ) -> List[Dict]:
        if seed_type == 'genre' and seed_genre and 'genre_based' in self.models:
            recs = self.models['genre_based'].recommend(
                user_id=UUID('00000000-0000-0000-0000-000000000000'),
                k=limit
            )
            return [
                {
                    'track_id': tid,
                    'score': score,
                    'reason': f'{seed_genre} radio',
                    'model_used': 'genre_based'
                }
                for tid, score in recs
            ]

        return []

    async def record_feedback(
        self,
        recommendation_id: UUID,
        user_id: UUID,
        track_id: UUID,
        action: str,
        score: Optional[float]
    ):
        pass

    async def reload_models(self):
        self._load_models()

    def get_models_info(self) -> Dict:
        return {
            'loaded_models': list(self.models.keys()),
            'model_paths': self.model_paths,
            'redis_connected': self.redis_client is not None,
        }

    def is_ready(self) -> bool:
        return len(self.models) > 0