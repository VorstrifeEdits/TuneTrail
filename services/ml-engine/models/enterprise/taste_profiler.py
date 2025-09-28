import numpy as np
from typing import List, Dict
from uuid import UUID
from collections import Counter, defaultdict
from datetime import datetime, timedelta


class TasteProfiler:
    def __init__(self):
        self.user_profiles = {}

    def build_profile(
        self,
        user_id: UUID,
        interactions: List[Dict],
        tracks: Dict[UUID, Dict],
        audio_features: Dict[UUID, Dict]
    ) -> Dict:
        user_interactions = [i for i in interactions if i['user_id'] == user_id]

        if not user_interactions:
            return self._empty_profile(user_id)

        played_tracks = [i['track_id'] for i in user_interactions if i['interaction_type'] == 'play']
        liked_tracks = [i['track_id'] for i in user_interactions if i['interaction_type'] == 'like']
        skipped_tracks = [i['track_id'] for i in user_interactions if i['interaction_type'] == 'skip']

        top_genres = self._analyze_genres(played_tracks, tracks)
        top_artists = self._analyze_artists(played_tracks, tracks)
        top_decades = self._analyze_decades(played_tracks, tracks)

        diversity_score = self._compute_diversity(played_tracks, tracks)
        adventurousness = self._compute_adventurousness(user_interactions)

        audio_prefs = self._analyze_audio_preferences(played_tracks, audio_features)

        listening_patterns = self._analyze_listening_patterns(user_interactions)

        predicted_likes = self._predict_likes(played_tracks, liked_tracks, tracks)

        profile = {
            'user_id': user_id,
            'top_genres': top_genres,
            'top_artists': top_artists,
            'top_decades': top_decades,
            'diversity_score': diversity_score,
            'adventurousness_score': adventurousness,
            'audio_preferences': audio_prefs,
            'listening_patterns': listening_patterns,
            'predicted_likes': predicted_likes,
            'total_plays': len(played_tracks),
            'total_likes': len(liked_tracks),
            'skip_rate': len(skipped_tracks) / len(played_tracks) if played_tracks else 0,
        }

        self.user_profiles[user_id] = profile
        return profile

    def _analyze_genres(self, track_ids: List[UUID], tracks: Dict) -> List[Dict]:
        genre_counter = Counter()

        for tid in track_ids:
            track = tracks.get(tid)
            if track and track.get('genre'):
                genre_counter[track['genre']] += 1

        total = sum(genre_counter.values())
        top_genres = [
            {
                'genre': genre,
                'play_count': count,
                'percentage': round((count / total * 100), 2) if total > 0 else 0,
                'trend': 'stable'
            }
            for genre, count in genre_counter.most_common(10)
        ]

        return top_genres

    def _analyze_artists(self, track_ids: List[UUID], tracks: Dict) -> List[Dict]:
        artist_counter = Counter()

        for tid in track_ids:
            track = tracks.get(tid)
            if track and track.get('artist'):
                artist_counter[track['artist']] += 1

        top_artists = [
            {'artist': artist, 'play_count': count}
            for artist, count in artist_counter.most_common(10)
        ]

        return top_artists

    def _analyze_decades(self, track_ids: List[UUID], tracks: Dict) -> List[Dict]:
        decade_counter = Counter()

        for tid in track_ids:
            track = tracks.get(tid)
            if track and track.get('release_year'):
                decade = (track['release_year'] // 10) * 10
                decade_counter[decade] += 1

        total = sum(decade_counter.values())
        top_decades = [
            {
                'decade': f"{decade}s",
                'play_count': count,
                'percentage': round((count / total * 100), 2) if total > 0 else 0
            }
            for decade, count in decade_counter.most_common(5)
        ]

        return top_decades

    def _compute_diversity(self, track_ids: List[UUID], tracks: Dict) -> float:
        genres = set()

        for tid in track_ids:
            track = tracks.get(tid)
            if track and track.get('genre'):
                genres.add(track['genre'])

        max_expected_genres = 20
        diversity = min(len(genres) / max_expected_genres, 1.0)

        return round(diversity, 2)

    def _compute_adventurousness(self, interactions: List[Dict]) -> float:
        if len(interactions) < 10:
            return 0.5

        recent_cutoff = datetime.utcnow() - timedelta(days=30)

        recent_tracks = set()
        for interaction in interactions:
            if interaction.get('timestamp', datetime.utcnow()) >= recent_cutoff:
                recent_tracks.add(interaction['track_id'])

        all_tracks = set(i['track_id'] for i in interactions)

        if not all_tracks:
            return 0.5

        exploration_rate = len(recent_tracks) / len(all_tracks)

        return round(min(exploration_rate, 1.0), 2)

    def _analyze_audio_preferences(
        self,
        track_ids: List[UUID],
        audio_features: Dict[UUID, Dict]
    ) -> Dict:
        tempo_values = []
        energy_values = []
        valence_values = []
        danceability_values = []
        acousticness_values = []

        for tid in track_ids:
            features = audio_features.get(tid)
            if not features:
                continue

            if features.get('tempo'):
                tempo_values.append(features['tempo'])
            if features.get('energy') is not None:
                energy_values.append(features['energy'])
            if features.get('valence') is not None:
                valence_values.append(features['valence'])
            if features.get('danceability') is not None:
                danceability_values.append(features['danceability'])
            if features.get('acousticness') is not None:
                acousticness_values.append(features['acousticness'])

        def classify_value(values, thresholds):
            if not values:
                return "unknown"
            avg = np.mean(values)
            for label, (low, high) in thresholds.items():
                if low <= avg < high:
                    return label
            return "unknown"

        energy_label = classify_value(energy_values, {
            "low": (0.0, 0.4),
            "medium": (0.4, 0.7),
            "high": (0.7, 1.0)
        })

        return {
            'preferred_tempo_range': [int(np.percentile(tempo_values, 25)), int(np.percentile(tempo_values, 75))] if tempo_values else [100, 140],
            'preferred_energy_level': energy_label,
            'avg_valence': round(np.mean(valence_values), 2) if valence_values else 0.5,
            'avg_danceability': round(np.mean(danceability_values), 2) if danceability_values else 0.5,
            'acoustic_preference': round(np.mean(acousticness_values), 2) if acousticness_values else 0.5,
        }

    def _analyze_listening_patterns(self, interactions: List[Dict]) -> Dict:
        hour_counter = Counter()

        for interaction in interactions:
            timestamp = interaction.get('timestamp', datetime.utcnow())
            hour = timestamp.hour
            hour_counter[hour] += 1

        peak_hours = [hour for hour, _ in hour_counter.most_common(4)]

        return {
            'peak_hours': sorted(peak_hours),
            'total_listening_sessions': len(interactions),
        }

    def _predict_likes(
        self,
        played_tracks: List[UUID],
        liked_tracks: List[UUID],
        tracks: Dict
    ) -> List[str]:
        played_genres = Counter()
        liked_genres = Counter()

        for tid in played_tracks:
            track = tracks.get(tid)
            if track and track.get('genre'):
                played_genres[track['genre']] += 1

        for tid in liked_tracks:
            track = tracks.get(tid)
            if track and track.get('genre'):
                liked_genres[track['genre']] += 1

        predicted = []
        for genre in played_genres.keys():
            if genre not in liked_genres and played_genres[genre] >= 3:
                predicted.append(genre)

        return predicted[:5]

    def _empty_profile(self, user_id: UUID) -> Dict:
        return {
            'user_id': user_id,
            'top_genres': [],
            'top_artists': [],
            'top_decades': [],
            'diversity_score': 0.0,
            'adventurousness_score': 0.5,
            'audio_preferences': {},
            'listening_patterns': {},
            'predicted_likes': [],
            'total_plays': 0,
            'total_likes': 0,
            'skip_rate': 0.0,
        }

    def save(self, path: str):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({'user_profiles': self.user_profiles}, f)

    @classmethod
    def load(cls, path: str):
        import pickle
        with open(path, 'rb') as f:
            data = pickle.load(f)

        profiler = cls()
        profiler.user_profiles = data['user_profiles']
        return profiler