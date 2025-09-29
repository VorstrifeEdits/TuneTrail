import asyncpg
from typing import List, Dict, Tuple
import sys
import os

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


async def load_training_data(
    train_ratio: float = 0.8
) -> Tuple[List[Dict], List[Dict]]:
    conn = await asyncpg.connect(Config.DATABASE_URL)

    query = """
        SELECT
            user_id,
            track_id,
            interaction_type,
            created_at
        FROM interactions
        WHERE interaction_type IN ('play', 'like', 'skip')
        ORDER BY created_at ASC
    """

    rows = await conn.fetch(query)
    await conn.close()

    interactions = [
        {
            'user_id': row['user_id'],
            'track_id': row['track_id'],
            'interaction_type': row['interaction_type'],
            'timestamp': row['created_at'],
        }
        for row in rows
    ]

    split_idx = int(len(interactions) * train_ratio)
    train_data = interactions[:split_idx]
    test_data = interactions[split_idx:]

    return train_data, test_data


async def load_tracks() -> Dict:
    conn = await asyncpg.connect(Config.DATABASE_URL)

    query = """
        SELECT
            id, title, artist, album, genre,
            duration_seconds, release_year
        FROM tracks
    """

    rows = await conn.fetch(query)
    await conn.close()

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
        }

    return tracks


async def load_audio_features() -> List[Dict]:
    conn = await asyncpg.connect(Config.DATABASE_URL)

    query = """
        SELECT
            track_id,
            tempo,
            energy,
            valence,
            danceability,
            acousticness,
            instrumentalness,
            speechiness,
            loudness,
            embedding,
            mfcc_features
        FROM audio_features
        WHERE embedding IS NOT NULL
    """

    rows = await conn.fetch(query)
    await conn.close()

    features = []
    for row in rows:
        features.append({
            'track_id': row['track_id'],
            'tempo': row['tempo'],
            'energy': row['energy'],
            'valence': row['valence'],
            'danceability': row['danceability'],
            'acousticness': row['acousticness'],
            'instrumentalness': row['instrumentalness'],
            'speechiness': row['speechiness'],
            'loudness': row['loudness'],
            'embedding': list(row['embedding']) if row['embedding'] else None,
            'mfcc_features': list(row['mfcc_features']) if row['mfcc_features'] else None,
        })

    return features