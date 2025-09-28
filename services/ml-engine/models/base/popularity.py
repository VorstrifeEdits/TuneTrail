from typing import List, Dict, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict


class PopularityModel:
    def __init__(self, time_decay_days: int = 30, min_plays: int = 5):
        self.time_decay_days = time_decay_days
        self.min_plays = min_plays
        self.track_scores = {}
        self.genre_scores = defaultdict(dict)
        self.trending_scores = {}

    def fit(self, interactions: List[Dict]):
        track_stats = defaultdict(lambda: {'plays': 0, 'likes': 0, 'skips': 0, 'last_played': None, 'genre': None})

        for interaction in interactions:
            track_id = interaction['track_id']
            interaction_type = interaction['interaction_type']
            timestamp = interaction.get('timestamp', datetime.utcnow())
            genre = interaction.get('genre')

            track_stats[track_id]['genre'] = genre

            if interaction_type == 'play':
                track_stats[track_id]['plays'] += 1
            elif interaction_type == 'like':
                track_stats[track_id]['likes'] += 1
            elif interaction_type == 'skip':
                track_stats[track_id]['skips'] += 1

            if track_stats[track_id]['last_played'] is None or timestamp > track_stats[track_id]['last_played']:
                track_stats[track_id]['last_played'] = timestamp

        for track_id, stats in track_stats.items():
            if stats['plays'] < self.min_plays:
                continue

            play_score = stats['plays']
            like_bonus = stats['likes'] * 2
            skip_penalty = stats['skips'] * 0.5

            base_score = play_score + like_bonus - skip_penalty

            time_decay = 1.0
            if stats['last_played']:
                days_ago = (datetime.utcnow() - stats['last_played']).days
                time_decay = np.exp(-days_ago / self.time_decay_days)

            popularity_score = base_score * time_decay

            self.track_scores[track_id] = popularity_score

            if stats['genre']:
                self.genre_scores[stats['genre']][track_id] = popularity_score

            if time_decay > 0.7:
                self.trending_scores[track_id] = popularity_score * time_decay

        return self

    def recommend_popular(self, k: int = 20, genre: str = None) -> List[Tuple[UUID, float]]:
        if genre and genre in self.genre_scores:
            scores = self.genre_scores[genre]
        else:
            scores = self.track_scores

        sorted_tracks = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return sorted_tracks

    def recommend_trending(self, k: int = 20, genre: str = None) -> List[Tuple[UUID, float]]:
        if genre:
            scores = {
                tid: score for tid, score in self.trending_scores.items()
                if tid in self.genre_scores.get(genre, {})
            }
        else:
            scores = self.trending_scores

        sorted_tracks = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return sorted_tracks

    def get_score(self, track_id: UUID) -> float:
        return self.track_scores.get(track_id, 0.0)

    def get_top_genres(self, k: int = 10) -> List[Tuple[str, float]]:
        genre_popularity = {
            genre: sum(scores.values())
            for genre, scores in self.genre_scores.items()
        }
        sorted_genres = sorted(genre_popularity.items(), key=lambda x: x[1], reverse=True)[:k]
        return sorted_genres

    def save(self, path: str):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'track_scores': self.track_scores,
                'genre_scores': dict(self.genre_scores),
                'trending_scores': self.trending_scores,
                'time_decay_days': self.time_decay_days,
                'min_plays': self.min_plays,
            }, f)

    @classmethod
    def load(cls, path: str):
        import pickle
        with open(path, 'rb') as f:
            data = pickle.load(f)

        model = cls(
            time_decay_days=data['time_decay_days'],
            min_plays=data['min_plays']
        )
        model.track_scores = data['track_scores']
        model.genre_scores = defaultdict(dict, data['genre_scores'])
        model.trending_scores = data['trending_scores']

        return model