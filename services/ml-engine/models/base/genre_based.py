from typing import List, Dict, Tuple
from uuid import UUID
from collections import defaultdict, Counter
import random


class GenreBasedModel:
    def __init__(self):
        self.user_genre_preferences = {}
        self.genre_tracks = defaultdict(list)
        self.track_genres = {}

    def fit(self, interactions: List[Dict], tracks: List[Dict]):
        user_genre_counts = defaultdict(Counter)

        for track in tracks:
            track_id = track['id']
            genre = track.get('genre')
            if genre:
                self.track_genres[track_id] = genre
                self.genre_tracks[genre].append(track_id)

        for interaction in interactions:
            if interaction['interaction_type'] not in ['play', 'like']:
                continue

            user_id = interaction['user_id']
            track_id = interaction['track_id']

            genre = self.track_genres.get(track_id)
            if genre:
                weight = 2 if interaction['interaction_type'] == 'like' else 1
                user_genre_counts[user_id][genre] += weight

        for user_id, genre_counts in user_genre_counts.items():
            total = sum(genre_counts.values())
            self.user_genre_preferences[user_id] = {
                genre: count / total
                for genre, count in genre_counts.items()
            }

        return self

    def recommend(self, user_id: UUID, k: int = 20, exclude_tracks: List[UUID] = None) -> List[Tuple[UUID, float]]:
        if user_id not in self.user_genre_preferences:
            return self._cold_start_recommend(k, exclude_tracks)

        genre_prefs = self.user_genre_preferences[user_id]

        exclude_set = set(exclude_tracks) if exclude_tracks else set()

        recommendations = []
        for genre, preference in sorted(genre_prefs.items(), key=lambda x: x[1], reverse=True):
            available_tracks = [
                tid for tid in self.genre_tracks[genre]
                if tid not in exclude_set
            ]

            num_to_sample = max(1, int(k * preference))
            sampled = random.sample(available_tracks, min(num_to_sample, len(available_tracks)))

            for track_id in sampled:
                recommendations.append((track_id, preference))

            if len(recommendations) >= k:
                break

        recommendations = sorted(recommendations, key=lambda x: x[1], reverse=True)[:k]

        return recommendations

    def _cold_start_recommend(self, k: int, exclude_tracks: List[UUID] = None) -> List[Tuple[UUID, float]]:
        all_tracks = []
        for tracks in self.genre_tracks.values():
            all_tracks.extend(tracks)

        exclude_set = set(exclude_tracks) if exclude_tracks else set()
        available = [tid for tid in all_tracks if tid not in exclude_set]

        sampled = random.sample(available, min(k, len(available)))

        return [(tid, 0.5) for tid in sampled]

    def get_user_top_genres(self, user_id: UUID, k: int = 5) -> List[Tuple[str, float]]:
        if user_id not in self.user_genre_preferences:
            return []

        prefs = self.user_genre_preferences[user_id]
        return sorted(prefs.items(), key=lambda x: x[1], reverse=True)[:k]

    def get_genre_similarity(self, genre1: str, genre2: str) -> float:
        if genre1 == genre2:
            return 1.0

        genre_map = {
            'rock': ['alternative', 'indie', 'punk'],
            'electronic': ['edm', 'techno', 'house', 'dubstep'],
            'pop': ['indie pop', 'synth-pop'],
            'hip-hop': ['rap', 'trap'],
            'jazz': ['blues', 'soul', 'funk'],
            'classical': ['orchestral', 'baroque'],
        }

        for base, similar in genre_map.items():
            if genre1 == base and genre2 in similar:
                return 0.7
            if genre2 == base and genre1 in similar:
                return 0.7
            if genre1 in similar and genre2 in similar:
                return 0.6

        return 0.0

    def save(self, path: str):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'user_genre_preferences': self.user_genre_preferences,
                'genre_tracks': dict(self.genre_tracks),
                'track_genres': self.track_genres,
            }, f)

    @classmethod
    def load(cls, path: str):
        import pickle
        with open(path, 'rb') as f:
            data = pickle.load(f)

        model = cls()
        model.user_genre_preferences = data['user_genre_preferences']
        model.genre_tracks = defaultdict(list, data['genre_tracks'])
        model.track_genres = data['track_genres']

        return model