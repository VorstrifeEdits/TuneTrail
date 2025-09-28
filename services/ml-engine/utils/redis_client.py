import redis
import json
from typing import List, Dict, Optional
from uuid import UUID
from config import Config


def get_redis_client() -> redis.Redis:
    return redis.from_url(Config.REDIS_URL, decode_responses=True)


def cache_recommendations(
    redis_client: redis.Redis,
    user_id: UUID,
    recommendations: List[Dict],
    ttl: int = None
):
    if ttl is None:
        ttl = Config.RECOMMENDATION_CACHE_TTL

    key = f"recommendations:{user_id}"

    serialized = json.dumps([
        {
            'track_id': str(r['track_id']),
            'score': r['score'],
            'reason': r['reason'],
            'model_used': r['model_used'],
        }
        for r in recommendations
    ])

    redis_client.setex(key, ttl, serialized)


def get_cached_recommendations(
    redis_client: redis.Redis,
    user_id: UUID
) -> Optional[List[Dict]]:
    key = f"recommendations:{user_id}"

    cached = redis_client.get(key)

    if cached:
        recommendations = json.loads(cached)
        for r in recommendations:
            r['track_id'] = UUID(r['track_id'])
        return recommendations

    return None


def cache_similar_tracks(
    redis_client: redis.Redis,
    track_id: UUID,
    similar_tracks: List[Dict],
    ttl: int = None
):
    if ttl is None:
        ttl = Config.SIMILARITY_CACHE_TTL

    key = f"similar:{track_id}"

    serialized = json.dumps([
        {
            'track_id': str(t['track_id']),
            'similarity': t['similarity'],
        }
        for t in similar_tracks
    ])

    redis_client.setex(key, ttl, serialized)


def get_cached_similar_tracks(
    redis_client: redis.Redis,
    track_id: UUID
) -> Optional[List[Dict]]:
    key = f"similar:{track_id}"

    cached = redis_client.get(key)

    if cached:
        similar_tracks = json.loads(cached)
        for t in similar_tracks:
            t['track_id'] = UUID(t['track_id'])
        return similar_tracks

    return None


def cache_taste_profile(
    redis_client: redis.Redis,
    user_id: UUID,
    profile: Dict,
    ttl: int = 86400
):
    key = f"taste_profile:{user_id}"

    profile_copy = profile.copy()
    if 'user_id' in profile_copy:
        profile_copy['user_id'] = str(profile_copy['user_id'])

    serialized = json.dumps(profile_copy)
    redis_client.setex(key, ttl, serialized)


def get_cached_taste_profile(
    redis_client: redis.Redis,
    user_id: UUID
) -> Optional[Dict]:
    key = f"taste_profile:{user_id}"

    cached = redis_client.get(key)

    if cached:
        profile = json.loads(cached)
        if 'user_id' in profile:
            profile['user_id'] = UUID(profile['user_id'])
        return profile

    return None