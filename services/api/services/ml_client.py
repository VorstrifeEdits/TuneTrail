import httpx
from typing import List, Dict, Optional
from uuid import UUID
import logging
from datetime import datetime
import os

from models.user import User


logger = logging.getLogger("ml_client")


class MLEngineClient:
    """Client for communicating with the ML Engine service."""

    def __init__(self):
        self.base_url = os.getenv("ML_ENGINE_URL", "http://ml-engine:8001")
        self.timeout = 30.0
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self.client

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def health_check(self) -> Dict:
        """Check ML engine health."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"ML engine health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def get_recommendations(
        self,
        user_id: UUID,
        user: User,
        limit: int = 20,
        filters: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Get personalized recommendations from ML engine.

        Args:
            user_id: User UUID
            user: User object with tier information
            limit: Number of recommendations
            filters: Optional filters (genre, etc.)
            context: Optional context (time, device, etc.)

        Returns:
            List of recommendation dictionaries
        """
        try:
            client = await self._get_client()

            # Determine model tier based on user's plan
            model_tier = self._get_user_tier(user)

            request_data = {
                "user_id": str(user_id),
                "limit": limit,
                "model_tier": model_tier,
                "filters": filters or {},
                "context": context or {}
            }

            response = await client.post("/recommend/user", json=request_data)
            response.raise_for_status()

            recommendations = response.json()

            logger.info(f"Got {len(recommendations)} recommendations for user {user_id} (tier: {model_tier})")
            return recommendations

        except httpx.ConnectError:
            logger.warning("ML engine not available, falling back to simple recommendations")
            return []
        except Exception as e:
            logger.error(f"ML recommendation request failed: {e}")
            return []

    async def get_similar_tracks(
        self,
        track_id: UUID,
        user: User,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[Dict]:
        """Get tracks similar to a specific track."""
        try:
            client = await self._get_client()

            # Starter+ feature: use audio features
            use_audio = user.org.plan in ['starter', 'pro', 'enterprise']

            request_data = {
                "track_id": str(track_id),
                "limit": limit,
                "use_audio": use_audio,
                "min_similarity": min_similarity
            }

            response = await client.post("/recommend/similar", json=request_data)
            response.raise_for_status()

            similar_tracks = response.json()

            logger.info(f"Got {len(similar_tracks)} similar tracks for {track_id}")
            return similar_tracks

        except httpx.ConnectError:
            logger.warning("ML engine not available for similar tracks")
            return []
        except Exception as e:
            logger.error(f"Similar tracks request failed: {e}")
            return []

    async def generate_daily_mixes(
        self,
        user_id: UUID,
        user: User,
        mix_count: int = 6,
        tracks_per_mix: int = 50
    ) -> List[Dict]:
        """Generate daily mixes (Starter+ feature)."""
        try:
            if user.org.plan == 'free':
                logger.warning("Daily mixes not available for free tier")
                return []

            client = await self._get_client()

            request_data = {
                "user_id": str(user_id),
                "mix_count": mix_count,
                "tracks_per_mix": tracks_per_mix
            }

            response = await client.post("/daily-mix", json=request_data)
            response.raise_for_status()

            mixes = response.json()

            logger.info(f"Generated {len(mixes)} daily mixes for user {user_id}")
            return mixes

        except httpx.ConnectError:
            logger.warning("ML engine not available for daily mixes")
            return []
        except Exception as e:
            logger.error(f"Daily mix generation failed: {e}")
            return []

    async def get_taste_profile(
        self,
        user_id: UUID,
        user: User
    ) -> Optional[Dict]:
        """Get user taste profile (Pro+ feature)."""
        try:
            if user.org.plan not in ['pro', 'enterprise']:
                logger.warning("Taste profile not available for this tier")
                return None

            client = await self._get_client()

            response = await client.post(f"/taste-profile/{user_id}")
            response.raise_for_status()

            profile = response.json()

            logger.info(f"Retrieved taste profile for user {user_id}")
            return profile

        except httpx.ConnectError:
            logger.warning("ML engine not available for taste profile")
            return None
        except Exception as e:
            logger.error(f"Taste profile request failed: {e}")
            return None

    async def generate_radio(
        self,
        user: User,
        seed_type: str,
        seed_id: Optional[UUID] = None,
        seed_genre: Optional[str] = None,
        diversity: float = 0.5,
        limit: int = 50
    ) -> List[Dict]:
        """Generate radio station (Starter+ feature)."""
        try:
            if user.org.plan == 'free':
                logger.warning("Radio generation not available for free tier")
                return []

            client = await self._get_client()

            params = {
                "seed_type": seed_type,
                "diversity": diversity,
                "limit": limit
            }

            if seed_id:
                params["seed_id"] = str(seed_id)
            if seed_genre:
                params["seed_genre"] = seed_genre

            response = await client.post("/radio/generate", params=params)
            response.raise_for_status()

            radio_tracks = response.json()

            logger.info(f"Generated radio with {len(radio_tracks)} tracks")
            return radio_tracks

        except httpx.ConnectError:
            logger.warning("ML engine not available for radio generation")
            return []
        except Exception as e:
            logger.error(f"Radio generation failed: {e}")
            return []

    async def record_feedback(
        self,
        recommendation_id: UUID,
        user_id: UUID,
        track_id: UUID,
        action: str,
        score: Optional[float] = None
    ):
        """Record recommendation feedback for model improvement."""
        try:
            client = await self._get_client()

            params = {
                "recommendation_id": str(recommendation_id),
                "user_id": str(user_id),
                "track_id": str(track_id),
                "action": action
            }

            if score is not None:
                params["score"] = score

            response = await client.post("/feedback", params=params)
            response.raise_for_status()

            logger.debug(f"Recorded feedback: {action} for recommendation {recommendation_id}")

        except httpx.ConnectError:
            logger.debug("ML engine not available for feedback recording")
        except Exception as e:
            logger.error(f"Feedback recording failed: {e}")

    def _get_user_tier(self, user: User) -> str:
        """Map user's organization plan to ML model tier."""
        plan_to_tier = {
            'free': 'free',
            'starter': 'starter',
            'pro': 'pro',
            'enterprise': 'enterprise'
        }

        return plan_to_tier.get(user.org.plan, 'free')

    async def reload_models(self) -> Dict:
        """Trigger model reload in ML engine."""
        try:
            client = await self._get_client()
            response = await client.post("/models/reload")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Model reload failed: {e}")
            return {"error": str(e)}

    async def get_models_info(self) -> Dict:
        """Get information about loaded models."""
        try:
            client = await self._get_client()
            response = await client.get("/models/info")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Models info request failed: {e}")
            return {"error": str(e)}


# Global ML client instance
ml_client = MLEngineClient()