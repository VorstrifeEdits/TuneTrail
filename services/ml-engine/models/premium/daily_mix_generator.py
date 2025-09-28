from typing import List, Dict
from uuid import UUID
from collections import Counter
import random


class DailyMixGenerator:
    def __init__(self, familiarity_ratio: float = 0.8):
        self.familiarity_ratio = familiarity_ratio
        self.discovery_ratio = 1.0 - familiarity_ratio

        self.user_genre_history = {}
        self.genre_tracks = {}

    def fit(self, interactions: List[Dict], tracks: Dict[UUID, Dict]):
        user_plays = {}
        for interaction in interactions:
            if interaction['interaction_type'] != 'play':
                continue

            user_id = interaction['user_id']
            track_id = interaction['track_id']

            if user_id not in user_plays:
                user_plays[user_id] = []

            user_plays[user_id].append(track_id)

        for user_id, played_tracks in user_plays.items():
            genre_counter = Counter()

            for track_id in played_tracks:
                track = tracks.get(track_id)
                if track and track.get('genre'):
                    genre_counter[track['genre']] += 1

            self.user_genre_history[user_id] = genre_counter

        for track_id, track_data in tracks.items():
            genre = track_data.get('genre')
            if genre:
                if genre not in self.genre_tracks:
                    self.genre_tracks[genre] = []
                self.genre_tracks[genre].append(track_id)

        return self

    def generate_mixes(
        self,
        user_id: UUID,
        user_played_tracks: List[UUID],
        mix_count: int = 6,
        tracks_per_mix: int = 50
    ) -> List[Dict]:
        if user_id not in self.user_genre_history:
            return self._generate_cold_start_mixes(mix_count, tracks_per_mix)

        genre_counts = self.user_genre_history[user_id]
        top_genres = [genre for genre, _ in genre_counts.most_common(mix_count)]

        mixes = []
        for idx, genre in enumerate(top_genres):
            if genre not in self.genre_tracks:
                continue

            all_genre_tracks = self.genre_tracks[genre]
            played_in_genre = [tid for tid in user_played_tracks if tid in all_genre_tracks]
            unplayed_in_genre = [tid for tid in all_genre_tracks if tid not in user_played_tracks]

            familiar_count = int(tracks_per_mix * self.familiarity_ratio)
            discovery_count = tracks_per_mix - familiar_count

            familiar_tracks = random.sample(
                played_in_genre,
                min(familiar_count, len(played_in_genre))
            )

            discovery_tracks = random.sample(
                unplayed_in_genre,
                min(discovery_count, len(unplayed_in_genre))
            )

            mix_tracks = familiar_tracks + discovery_tracks
            random.shuffle(mix_tracks)

            mixes.append({
                'mix_id': f'daily-mix-{idx+1}',
                'name': f'{genre.title()} Mix',
                'description': f'Your favorite {genre} tracks and new discoveries',
                'genre': genre,
                'tracks': mix_tracks,
                'total_tracks': len(mix_tracks),
                'familiar_ratio': len(familiar_tracks) / len(mix_tracks) if mix_tracks else 0,
            })

        return mixes

    def _generate_cold_start_mixes(self, mix_count: int, tracks_per_mix: int) -> List[Dict]:
        available_genres = list(self.genre_tracks.keys())[:mix_count]

        mixes = []
        for idx, genre in enumerate(available_genres):
            genre_track_list = self.genre_tracks[genre]
            sampled_tracks = random.sample(
                genre_track_list,
                min(tracks_per_mix, len(genre_track_list))
            )

            mixes.append({
                'mix_id': f'daily-mix-{idx+1}',
                'name': f'{genre.title()} Mix',
                'description': f'Discover great {genre} music',
                'genre': genre,
                'tracks': sampled_tracks,
                'total_tracks': len(sampled_tracks),
                'familiar_ratio': 0.0,
            })

        return mixes

    def save(self, path: str):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'user_genre_history': self.user_genre_history,
                'genre_tracks': self.genre_tracks,
                'familiarity_ratio': self.familiarity_ratio,
            }, f)

    @classmethod
    def load(cls, path: str):
        import pickle
        with open(path, 'rb') as f:
            data = pickle.load(f)

        model = cls(familiarity_ratio=data['familiarity_ratio'])
        model.user_genre_history = data['user_genre_history']
        model.genre_tracks = data['genre_tracks']

        return model