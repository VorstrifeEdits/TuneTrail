import asyncpg
from typing import List, Dict, Optional
from uuid import UUID
from config import Config


async def get_db_connection():
    return await asyncpg.connect(Config.DATABASE_URL)


async def fetch_interactions(
    conn: asyncpg.Connection,
    user_id: Optional[UUID] = None,
    limit: Optional[int] = None
) -> List[Dict]:
    query = """
        SELECT
            id, user_id, track_id, interaction_type,
            created_at, context
        FROM interactions
    """

    params = []
    if user_id:
        query += " WHERE user_id = $1"
        params.append(user_id)

    query += " ORDER BY created_at DESC"

    if limit:
        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)

    rows = await conn.fetch(query, *params)

    return [
        {
            'id': row['id'],
            'user_id': row['user_id'],
            'track_id': row['track_id'],
            'interaction_type': row['interaction_type'],
            'timestamp': row['created_at'],
            'context': row.get('context', {}),
        }
        for row in rows
    ]


async def fetch_tracks(
    conn: asyncpg.Connection,
    track_ids: Optional[List[UUID]] = None,
    org_id: Optional[UUID] = None,
    limit: Optional[int] = None
) -> Dict[UUID, Dict]:
    query = """
        SELECT
            id, title, artist, album, genre,
            duration_seconds, release_year, created_at
        FROM tracks
    """

    params = []
    conditions = []

    if track_ids:
        conditions.append(f"id = ANY(${len(params) + 1})")
        params.append(track_ids)

    if org_id:
        conditions.append(f"org_id = ${len(params) + 1}")
        params.append(org_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if limit:
        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)

    rows = await conn.fetch(query, *params)

    tracks = {}
    for row in rows:
        tracks[row['id']] = {
            'id': row['id'],
            'title': row['title'],
            'artist': row['artist'],
            'album': row['album'],
            'genre': row['genre'],
            'duration_seconds': row['duration_seconds'],
            'release_year': row['release_year'],
            'created_at': row['created_at'],
        }

    return tracks


async def fetch_audio_features(
    conn: asyncpg.Connection,
    track_ids: Optional[List[UUID]] = None,
    limit: Optional[int] = None
) -> Dict[UUID, Dict]:
    query = """
        SELECT
            track_id, tempo, energy, valence, danceability,
            acousticness, instrumentalness, speechiness,
            embedding, mfcc_features
        FROM audio_features
    """

    params = []
    if track_ids:
        query += f" WHERE track_id = ANY(${len(params) + 1})"
        params.append(track_ids)

    if limit:
        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)

    rows = await conn.fetch(query, *params)

    features = {}
    for row in rows:
        features[row['track_id']] = {
            'track_id': row['track_id'],
            'tempo': row['tempo'],
            'energy': row['energy'],
            'valence': row['valence'],
            'danceability': row['danceability'],
            'acousticness': row['acousticness'],
            'instrumentalness': row['instrumentalness'],
            'speechiness': row['speechiness'],
            'embedding': list(row['embedding']) if row['embedding'] else None,
            'mfcc_features': list(row['mfcc_features']) if row['mfcc_features'] else None,
        }

    return features


async def fetch_user_play_history(
    conn: asyncpg.Connection,
    user_id: UUID,
    limit: int = 100
) -> List[UUID]:
    query = """
        SELECT DISTINCT track_id
        FROM interactions
        WHERE user_id = $1 AND interaction_type = 'play'
        ORDER BY created_at DESC
        LIMIT $2
    """

    rows = await conn.fetch(query, user_id, limit)
    return [row['track_id'] for row in rows]


async def record_recommendation_impression(
    conn: asyncpg.Connection,
    user_id: UUID,
    track_id: UUID,
    model_type: str,
    score: float,
    reason: str,
    position: int
):
    query = """
        INSERT INTO recommendation_impressions
        (user_id, track_id, model_type, score, reason, position, shown_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        RETURNING id
    """

    result = await conn.fetchrow(query, user_id, track_id, model_type, score, reason, position)
    return result['id']