from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field
import asyncio

from config import Config, ModelTier
from inference.recommender import RecommendationEngine
from utils.redis_client import get_redis_client

app = FastAPI(
    title="TuneTrail ML Engine",
    description="Machine Learning recommendation engine for TuneTrail",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recommender = RecommendationEngine()


class RecommendationRequest(BaseModel):
    user_id: UUID
    limit: int = Field(default=20, ge=1, le=100)
    model_tier: ModelTier = ModelTier.FREE
    filters: Optional[dict] = None
    context: Optional[dict] = None


class RecommendationResponse(BaseModel):
    track_id: UUID
    score: float = Field(..., ge=0.0, le=1.0)
    reason: str
    model_used: str


class SimilarTrackRequest(BaseModel):
    track_id: UUID
    limit: int = Field(default=10, ge=1, le=50)
    use_audio: bool = True
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


class DailyMixRequest(BaseModel):
    user_id: UUID
    mix_count: int = Field(default=6, ge=1, le=10)
    tracks_per_mix: int = Field(default=50, ge=10, le=100)


class TasteProfileResponse(BaseModel):
    user_id: UUID
    top_genres: List[dict]
    diversity_score: float
    adventurousness_score: float
    predicted_likes: List[str]
    audio_preferences: dict


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ml-engine",
        "version": "1.0.0",
        "models_loaded": recommender.is_ready()
    }


@app.post("/recommend/user", response_model=List[RecommendationResponse])
async def recommend_for_user(request: RecommendationRequest):
    try:
        recommendations = await recommender.get_recommendations(
            user_id=request.user_id,
            limit=request.limit,
            tier=request.model_tier,
            filters=request.filters,
            context=request.context
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend/similar", response_model=List[RecommendationResponse])
async def recommend_similar_tracks(request: SimilarTrackRequest):
    try:
        similar_tracks = await recommender.get_similar_tracks(
            track_id=request.track_id,
            limit=request.limit,
            use_audio=request.use_audio,
            min_similarity=request.min_similarity
        )
        return similar_tracks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/daily-mix")
async def generate_daily_mix(request: DailyMixRequest):
    try:
        if request.mix_count < 1 or request.mix_count > 10:
            raise HTTPException(status_code=400, detail="mix_count must be between 1 and 10")

        mixes = await recommender.generate_daily_mixes(
            user_id=request.user_id,
            mix_count=request.mix_count,
            tracks_per_mix=request.tracks_per_mix
        )
        return mixes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/taste-profile/{user_id}", response_model=TasteProfileResponse)
async def get_taste_profile(user_id: UUID):
    try:
        profile = await recommender.compute_taste_profile(user_id)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/radio/generate")
async def generate_radio(
    seed_type: str = Query(..., pattern="^(track|artist|genre|playlist)$"),
    seed_id: Optional[UUID] = None,
    seed_genre: Optional[str] = None,
    diversity: float = Query(default=0.5, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=10, le=200)
):
    try:
        radio_tracks = await recommender.generate_radio(
            seed_type=seed_type,
            seed_id=seed_id,
            seed_genre=seed_genre,
            diversity=diversity,
            limit=limit
        )
        return radio_tracks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def record_feedback(
    recommendation_id: UUID,
    user_id: UUID,
    track_id: UUID,
    action: str = Query(..., pattern="^(played|liked|skipped|dismissed|saved)$"),
    score: Optional[float] = Query(None, ge=0.0, le=1.0)
):
    try:
        await recommender.record_feedback(
            recommendation_id=recommendation_id,
            user_id=user_id,
            track_id=track_id,
            action=action,
            score=score
        )
        return {"message": "Feedback recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/reload")
async def reload_models():
    try:
        await recommender.reload_models()
        return {"message": "Models reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/info")
async def get_models_info():
    return recommender.get_models_info()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)