#!/usr/bin/env python3
"""
TuneTrail ML Engine - Dataset Ingestion Script

Ingest music datasets from various sources for training ML models.

Supported datasets:
- Free Music Archive (FMA) - Creative Commons music
- Million Song Dataset - Metadata and features
- Spotify Web API - Preview tracks and metadata
- MusicBrainz - Comprehensive metadata

Usage:
    python scripts/ingest_dataset.py [dataset] [options]

Examples:
    python scripts/ingest_dataset.py fma --subset small --extract-features
    python scripts/ingest_dataset.py spotify --tracks 1000 --extract-features
    python scripts/ingest_dataset.py musicbrainz --artists "The Beatles"
"""

import asyncio
import argparse
import sys
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import zipfile
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from utils.db import get_db_connection


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("ingest_dataset")


class DatasetIngester:
    """Base class for dataset ingestion."""

    def __init__(self, extract_features: bool = False):
        self.extract_features = extract_features
        self.start_time = datetime.now()
        self.ingested_tracks = 0
        self.failed_tracks = 0

    async def ingest(self, **kwargs) -> Dict:
        """Override in subclasses."""
        raise NotImplementedError


class FMAIngester(DatasetIngester):
    """Free Music Archive dataset ingester."""

    def __init__(self, extract_features: bool = False):
        super().__init__(extract_features)
        self.fma_urls = {
            'small': 'https://os.unil.cloud.switch.ch/fma/fma_small.zip',
            'medium': 'https://os.unil.cloud.switch.ch/fma/fma_medium.zip',
            'metadata': 'https://os.unil.cloud.switch.ch/fma/fma_metadata.zip'
        }

    async def ingest(self, subset: str = 'small', data_dir: str = '/tmp/fma') -> Dict:
        """
        Ingest FMA dataset.

        Args:
            subset: FMA subset to download ('small', 'medium')
            data_dir: Directory to store downloaded data

        Returns:
            Ingestion results
        """
        logger.info(f"🎵 Ingesting FMA Dataset (subset: {subset})")

        try:
            # Create data directory
            data_dir = Path(data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)

            # Download and extract dataset
            dataset_path = await self._download_fma_dataset(subset, data_dir)
            metadata_path = await self._download_fma_metadata(data_dir)

            # Process metadata
            tracks_metadata = self._process_fma_metadata(metadata_path)

            # Ingest tracks to database
            await self._ingest_tracks_to_db(tracks_metadata, dataset_path)

            duration = datetime.now() - self.start_time

            result = {
                'dataset': 'FMA',
                'subset': subset,
                'ingested_tracks': self.ingested_tracks,
                'failed_tracks': self.failed_tracks,
                'duration_seconds': duration.total_seconds(),
                'data_directory': str(data_dir),
                'status': 'success'
            }

            logger.info(f"✅ FMA ingestion completed: {self.ingested_tracks} tracks in {duration}")
            return result

        except Exception as e:
            logger.error(f"❌ FMA ingestion failed: {e}")
            return {
                'dataset': 'FMA',
                'status': 'error',
                'error': str(e)
            }

    async def _download_fma_dataset(self, subset: str, data_dir: Path) -> Path:
        """Download FMA dataset."""
        if subset not in self.fma_urls:
            raise ValueError(f"Unknown FMA subset: {subset}")

        url = self.fma_urls[subset]
        filename = f"fma_{subset}.zip"
        file_path = data_dir / filename
        extract_path = data_dir / f"fma_{subset}"

        # Check if already downloaded
        if extract_path.exists() and any(extract_path.iterdir()):
            logger.info(f"FMA {subset} already exists at {extract_path}")
            return extract_path

        logger.info(f"Downloading FMA {subset} from {url}...")

        # Download file
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if downloaded % (1024 * 1024 * 10) == 0:  # Log every 10MB
                            logger.info(f"Download progress: {progress:.1f}%")

        logger.info(f"Download completed: {file_path}")

        # Extract archive
        logger.info(f"Extracting {filename}...")
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(data_dir)

        logger.info(f"Extraction completed: {extract_path}")
        return extract_path

    async def _download_fma_metadata(self, data_dir: Path) -> Path:
        """Download FMA metadata."""
        url = self.fma_urls['metadata']
        filename = "fma_metadata.zip"
        file_path = data_dir / filename
        extract_path = data_dir / "fma_metadata"

        if extract_path.exists():
            logger.info("FMA metadata already exists")
            return extract_path

        logger.info("Downloading FMA metadata...")

        response = requests.get(url)
        response.raise_for_status()

        with open(file_path, 'wb') as f:
            f.write(response.content)

        # Extract metadata
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(data_dir)

        return extract_path

    def _process_fma_metadata(self, metadata_path: Path) -> List[Dict]:
        """Process FMA metadata CSV files."""
        logger.info("Processing FMA metadata...")

        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required for FMA metadata processing")
            raise

        # Load tracks metadata
        tracks_file = metadata_path / "tracks.csv"
        if not tracks_file.exists():
            raise FileNotFoundError(f"Tracks metadata not found: {tracks_file}")

        # Read CSV with multi-level headers
        tracks_df = pd.read_csv(tracks_file, index_col=0, header=[0, 1])

        tracks_metadata = []

        for track_id, row in tracks_df.iterrows():
            try:
                # Extract basic track information
                track_data = {
                    'external_id': str(track_id),
                    'title': self._safe_get(row, ('track', 'title')),
                    'artist': self._safe_get(row, ('artist', 'name')),
                    'album': self._safe_get(row, ('album', 'title')),
                    'genre': self._safe_get(row, ('track', 'genre_top')),
                    'duration_seconds': self._safe_get(row, ('track', 'duration')),
                    'release_year': None,  # Not directly available in FMA
                    'source': 'FMA',
                    'license': self._safe_get(row, ('track', 'license')),
                }

                tracks_metadata.append(track_data)

            except Exception as e:
                logger.debug(f"Failed to process track {track_id}: {e}")
                continue

        logger.info(f"Processed metadata for {len(tracks_metadata)} tracks")
        return tracks_metadata

    def _safe_get(self, row, key_path):
        """Safely get value from multi-level DataFrame row."""
        try:
            value = row[key_path]
            return str(value) if pd.notna(value) else None
        except (KeyError, IndexError):
            return None

    async def _ingest_tracks_to_db(self, tracks_metadata: List[Dict], audio_path: Path):
        """Ingest tracks to database."""
        logger.info("Ingesting tracks to database...")

        conn = await get_db_connection()

        try:
            # Get default organization (assuming one exists)
            org_result = await conn.fetchrow("SELECT id FROM organizations LIMIT 1")
            if not org_result:
                logger.error("No organization found. Please create an organization first.")
                return

            org_id = org_result['id']

            for track_data in tracks_metadata:
                try:
                    # Check if track already exists
                    existing = await conn.fetchrow(
                        "SELECT id FROM tracks WHERE title = $1 AND artist = $2",
                        track_data['title'], track_data['artist']
                    )

                    if existing:
                        logger.debug(f"Track already exists: {track_data['title']}")
                        continue

                    # Insert track
                    track_id = await conn.fetchval("""
                        INSERT INTO tracks (
                            org_id, title, artist, album, genre,
                            duration_seconds, extra_metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id
                    """,
                        org_id,
                        track_data['title'],
                        track_data['artist'],
                        track_data['album'],
                        track_data['genre'],
                        track_data['duration_seconds'],
                        {
                            'source': track_data['source'],
                            'external_id': track_data['external_id'],
                            'license': track_data['license']
                        }
                    )

                    self.ingested_tracks += 1

                    if self.ingested_tracks % 100 == 0:
                        logger.info(f"Ingested {self.ingested_tracks} tracks...")

                except Exception as e:
                    logger.debug(f"Failed to ingest track {track_data['title']}: {e}")
                    self.failed_tracks += 1

        finally:
            await conn.close()


class SpotifyIngester(DatasetIngester):
    """Spotify Web API dataset ingester."""

    def __init__(self, extract_features: bool = False):
        super().__init__(extract_features)
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

        if not self.client_id or not self.client_secret:
            logger.warning("Spotify credentials not found. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")

    async def ingest(self, tracks: int = 1000, playlists: List[str] = None) -> Dict:
        """
        Ingest tracks from Spotify Web API.

        Args:
            tracks: Number of tracks to ingest
            playlists: List of playlist IDs to ingest from

        Returns:
            Ingestion results
        """
        logger.info(f"🎵 Ingesting Spotify Dataset ({tracks} tracks)")

        if not self.client_id:
            return {
                'dataset': 'Spotify',
                'status': 'error',
                'error': 'Spotify credentials not configured'
            }

        try:
            # Get access token
            access_token = await self._get_spotify_token()

            # Get tracks (either from playlists or search)
            if playlists:
                track_data = await self._get_tracks_from_playlists(access_token, playlists)
            else:
                track_data = await self._search_tracks(access_token, tracks)

            # Ingest to database
            await self._ingest_spotify_tracks(track_data)

            duration = datetime.now() - self.start_time

            result = {
                'dataset': 'Spotify',
                'ingested_tracks': self.ingested_tracks,
                'failed_tracks': self.failed_tracks,
                'duration_seconds': duration.total_seconds(),
                'status': 'success'
            }

            logger.info(f"✅ Spotify ingestion completed: {self.ingested_tracks} tracks in {duration}")
            return result

        except Exception as e:
            logger.error(f"❌ Spotify ingestion failed: {e}")
            return {
                'dataset': 'Spotify',
                'status': 'error',
                'error': str(e)
            }

    async def _get_spotify_token(self) -> str:
        """Get Spotify API access token."""
        import base64

        auth_url = "https://accounts.spotify.com/api/token"
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {'grant_type': 'client_credentials'}

        response = requests.post(auth_url, headers=headers, data=data)
        response.raise_for_status()

        return response.json()['access_token']

    async def _search_tracks(self, access_token: str, num_tracks: int) -> List[Dict]:
        """Search for tracks using various queries."""
        logger.info(f"Searching for {num_tracks} tracks...")

        headers = {'Authorization': f'Bearer {access_token}'}

        # Various search queries to get diverse tracks
        search_queries = [
            'genre:pop year:2020-2024',
            'genre:rock year:2015-2024',
            'genre:electronic year:2018-2024',
            'genre:jazz year:2010-2024',
            'genre:classical year:2020-2024',
            'genre:hip-hop year:2020-2024',
            'genre:country year:2015-2024',
            'genre:r&b year:2018-2024'
        ]

        all_tracks = []
        tracks_per_query = num_tracks // len(search_queries)

        for query in search_queries:
            try:
                offset = 0
                gathered = 0

                while gathered < tracks_per_query:
                    search_url = f"https://api.spotify.com/v1/search"
                    params = {
                        'q': query,
                        'type': 'track',
                        'limit': min(50, tracks_per_query - gathered),
                        'offset': offset
                    }

                    response = requests.get(search_url, headers=headers, params=params)
                    response.raise_for_status()

                    data = response.json()
                    tracks = data.get('tracks', {}).get('items', [])

                    if not tracks:
                        break

                    for track in tracks:
                        track_data = self._process_spotify_track(track)
                        if track_data:
                            all_tracks.append(track_data)
                            gathered += 1

                    offset += len(tracks)

                logger.info(f"Gathered {gathered} tracks for query: {query}")

            except Exception as e:
                logger.warning(f"Failed to search with query '{query}': {e}")

        logger.info(f"Total tracks gathered: {len(all_tracks)}")
        return all_tracks

    def _process_spotify_track(self, track: Dict) -> Dict:
        """Process Spotify track data."""
        try:
            return {
                'external_id': track['id'],
                'title': track['name'],
                'artist': ', '.join(artist['name'] for artist in track['artists']),
                'album': track['album']['name'],
                'duration_seconds': track['duration_ms'] // 1000,
                'preview_url': track['preview_url'],
                'release_year': int(track['album']['release_date'][:4]) if track['album']['release_date'] else None,
                'source': 'Spotify',
                'popularity': track.get('popularity'),
                'explicit': track.get('explicit', False),
                'external_urls': track.get('external_urls', {})
            }
        except Exception as e:
            logger.debug(f"Failed to process Spotify track: {e}")
            return None

    async def _ingest_spotify_tracks(self, tracks_data: List[Dict]):
        """Ingest Spotify tracks to database."""
        logger.info("Ingesting Spotify tracks to database...")

        conn = await get_db_connection()

        try:
            # Get default organization
            org_result = await conn.fetchrow("SELECT id FROM organizations LIMIT 1")
            if not org_result:
                logger.error("No organization found. Please create an organization first.")
                return

            org_id = org_result['id']

            for track_data in tracks_data:
                try:
                    # Check if track already exists
                    existing = await conn.fetchrow(
                        "SELECT id FROM tracks WHERE title = $1 AND artist = $2",
                        track_data['title'], track_data['artist']
                    )

                    if existing:
                        logger.debug(f"Track already exists: {track_data['title']}")
                        continue

                    # Insert track
                    await conn.execute("""
                        INSERT INTO tracks (
                            org_id, title, artist, album, duration_seconds,
                            release_year, audio_url, extra_metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        org_id,
                        track_data['title'],
                        track_data['artist'],
                        track_data['album'],
                        track_data['duration_seconds'],
                        track_data['release_year'],
                        track_data['preview_url'],
                        {
                            'source': track_data['source'],
                            'external_id': track_data['external_id'],
                            'popularity': track_data['popularity'],
                            'explicit': track_data['explicit'],
                            'external_urls': track_data['external_urls']
                        }
                    )

                    self.ingested_tracks += 1

                    if self.ingested_tracks % 50 == 0:
                        logger.info(f"Ingested {self.ingested_tracks} Spotify tracks...")

                except Exception as e:
                    logger.debug(f"Failed to ingest Spotify track {track_data['title']}: {e}")
                    self.failed_tracks += 1

        finally:
            await conn.close()


async def main():
    """Main function to run dataset ingestion."""
    parser = argparse.ArgumentParser(description='Ingest music datasets for TuneTrail')
    parser.add_argument(
        'dataset',
        choices=['fma', 'spotify', 'musicbrainz'],
        help='Dataset to ingest'
    )
    parser.add_argument(
        '--extract-features',
        action='store_true',
        help='Extract audio features after ingestion'
    )

    # FMA-specific arguments
    parser.add_argument(
        '--subset',
        choices=['small', 'medium'],
        default='small',
        help='FMA subset to download (default: small)'
    )
    parser.add_argument(
        '--data-dir',
        default='/tmp/fma',
        help='Directory to store downloaded data'
    )

    # Spotify-specific arguments
    parser.add_argument(
        '--tracks',
        type=int,
        default=1000,
        help='Number of tracks to ingest from Spotify (default: 1000)'
    )

    args = parser.parse_args()

    try:
        if args.dataset == 'fma':
            ingester = FMAIngester(extract_features=args.extract_features)
            result = await ingester.ingest(subset=args.subset, data_dir=args.data_dir)

        elif args.dataset == 'spotify':
            ingester = SpotifyIngester(extract_features=args.extract_features)
            result = await ingester.ingest(tracks=args.tracks)

        elif args.dataset == 'musicbrainz':
            logger.error("MusicBrainz ingestion not yet implemented")
            sys.exit(1)

        else:
            logger.error(f"Unknown dataset: {args.dataset}")
            sys.exit(1)

        # Print results
        if result['status'] == 'success':
            logger.info(f"✅ Dataset ingestion completed successfully!")
            logger.info(f"Ingested tracks: {result['ingested_tracks']}")
            logger.info(f"Duration: {result['duration_seconds']:.1f}s")
        else:
            logger.error(f"❌ Dataset ingestion failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Dataset ingestion interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Dataset ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())