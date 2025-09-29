#!/usr/bin/env python3
"""
TuneTrail ML Engine - Training Setup Script

Set up the ML engine for training with proper data validation.

Usage:
    python scripts/setup_training.py [--check-data] [--create-sample]

Examples:
    python scripts/setup_training.py --check-data
    python scripts/setup_training.py --create-sample
"""

import asyncio
import argparse
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from utils.db import get_db_connection


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("setup_training")


class TrainingSetup:
    """Setup and validate ML training environment."""

    def __init__(self):
        self.start_time = datetime.now()

    async def check_training_readiness(self) -> Dict:
        """Check if the system is ready for ML training."""
        logger.info("🔍 Checking Training Readiness")
        logger.info("=" * 40)

        checks = {}

        # Database connectivity
        checks['database'] = await self._check_database()

        # Data availability
        checks['data'] = await self._check_data_availability()

        # Model directories
        checks['directories'] = self._check_model_directories()

        # Dependencies
        checks['dependencies'] = self._check_dependencies()

        # Generate summary
        checks['summary'] = self._generate_readiness_summary(checks)

        return checks

    async def _check_database(self) -> Dict:
        """Check database connectivity and schema."""
        logger.info("🔌 Checking database connectivity...")

        try:
            conn = await get_db_connection()

            # Check required tables exist
            tables_to_check = [
                'organizations', 'users', 'tracks', 'interactions',
                'audio_features', 'recommendation_impressions'
            ]

            table_status = {}
            for table in tables_to_check:
                try:
                    result = await conn.fetchrow(f"SELECT COUNT(*) as count FROM {table}")
                    table_status[table] = {
                        'exists': True,
                        'row_count': result['count']
                    }
                    logger.info(f"  ✅ {table}: {result['count']} rows")
                except Exception as e:
                    table_status[table] = {
                        'exists': False,
                        'error': str(e)
                    }
                    logger.error(f"  ❌ {table}: {e}")

            await conn.close()

            return {
                'status': 'success',
                'tables': table_status,
                'message': 'Database connectivity verified'
            }

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Database connection failed'
            }

    async def _check_data_availability(self) -> Dict:
        """Check data availability for training."""
        logger.info("📊 Checking data availability...")

        try:
            conn = await get_db_connection()

            # Check interaction data
            interaction_result = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_interactions,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT track_id) as unique_tracks,
                    COUNT(*) FILTER (WHERE interaction_type = 'play') as plays,
                    COUNT(*) FILTER (WHERE interaction_type = 'like') as likes,
                    COUNT(*) FILTER (WHERE interaction_type = 'skip') as skips
                FROM interactions
            """)

            # Check audio features
            audio_result = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_features,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as with_embeddings,
                    COUNT(*) FILTER (WHERE tempo IS NOT NULL) as with_tempo,
                    COUNT(*) FILTER (WHERE energy IS NOT NULL) as with_energy
                FROM audio_features
            """)

            # Check track data
            track_result = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_tracks,
                    COUNT(*) FILTER (WHERE genre IS NOT NULL) as with_genre,
                    COUNT(*) FILTER (WHERE artist IS NOT NULL) as with_artist,
                    COUNT(DISTINCT genre) as unique_genres
                FROM tracks
            """)

            await conn.close()

            # Validate sufficiency
            sufficient_data = (
                interaction_result['total_interactions'] >= 1000 and
                interaction_result['unique_users'] >= 10 and
                interaction_result['unique_tracks'] >= 100
            )

            data_quality = self._assess_data_quality(interaction_result, audio_result, track_result)

            logger.info(f"  📈 Interactions: {interaction_result['total_interactions']}")
            logger.info(f"  👥 Users: {interaction_result['unique_users']}")
            logger.info(f"  🎵 Tracks: {interaction_result['unique_tracks']}")
            logger.info(f"  🎯 Audio features: {audio_result['with_embeddings']}")

            return {
                'status': 'success' if sufficient_data else 'warning',
                'sufficient_for_training': sufficient_data,
                'interactions': dict(interaction_result),
                'audio_features': dict(audio_result),
                'tracks': dict(track_result),
                'quality_assessment': data_quality,
                'recommendations': self._get_data_recommendations(interaction_result, audio_result, track_result)
            }

        except Exception as e:
            logger.error(f"❌ Data availability check failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _assess_data_quality(self, interactions, audio_features, tracks) -> Dict:
        """Assess the quality of available data."""
        quality = {}

        # Interaction density
        if interactions['unique_users'] > 0 and interactions['unique_tracks'] > 0:
            density = interactions['total_interactions'] / (interactions['unique_users'] * interactions['unique_tracks'])
            quality['interaction_density'] = density

        # Audio feature coverage
        if tracks['total_tracks'] > 0:
            audio_coverage = audio_features['with_embeddings'] / tracks['total_tracks']
            quality['audio_feature_coverage'] = audio_coverage

        # Genre coverage
        if tracks['total_tracks'] > 0:
            genre_coverage = tracks['with_genre'] / tracks['total_tracks']
            quality['genre_coverage'] = genre_coverage

        return quality

    def _get_data_recommendations(self, interactions, audio_features, tracks) -> List[str]:
        """Get recommendations for improving data quality."""
        recommendations = []

        if interactions['total_interactions'] < 1000:
            recommendations.append("Increase interaction data - need at least 1,000 interactions for training")

        if interactions['unique_users'] < 50:
            recommendations.append("Need more users - aim for 50+ users with interaction history")

        if audio_features['with_embeddings'] < tracks['total_tracks'] * 0.5:
            recommendations.append("Extract audio features for more tracks using audio-processor service")

        if tracks['with_genre'] < tracks['total_tracks'] * 0.7:
            recommendations.append("Improve genre tagging - many tracks missing genre information")

        if interactions['plays'] < interactions['total_interactions'] * 0.5:
            recommendations.append("Increase play interactions - they are critical for collaborative filtering")

        if not recommendations:
            recommendations.append("Data looks good! Ready for ML training.")

        return recommendations

    def _check_model_directories(self) -> Dict:
        """Check that model directories exist and are writable."""
        logger.info("📁 Checking model directories...")

        directories = [
            Config.MODEL_SAVE_PATH,
            os.path.join(Config.MODEL_SAVE_PATH, "free"),
            os.path.join(Config.MODEL_SAVE_PATH, "starter"),
            os.path.join(Config.MODEL_SAVE_PATH, "pro"),
            os.path.join(Config.MODEL_SAVE_PATH, "enterprise"),
            Config.FAISS_INDEX_PATH,
        ]

        directory_status = {}

        for dir_path in directories:
            try:
                os.makedirs(dir_path, exist_ok=True)

                # Test write permissions
                test_file = os.path.join(dir_path, ".write_test")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)

                directory_status[dir_path] = {
                    'exists': True,
                    'writable': True
                }
                logger.info(f"  ✅ {dir_path}")

            except Exception as e:
                directory_status[dir_path] = {
                    'exists': os.path.exists(dir_path),
                    'writable': False,
                    'error': str(e)
                }
                logger.error(f"  ❌ {dir_path}: {e}")

        return {
            'status': 'success',
            'directories': directory_status
        }

    def _check_dependencies(self) -> Dict:
        """Check that required dependencies are available."""
        logger.info("🔧 Checking dependencies...")

        dependencies = [
            ('torch', 'PyTorch for deep learning'),
            ('sklearn', 'scikit-learn for traditional ML'),
            ('faiss', 'FAISS for similarity search'),
            ('numpy', 'NumPy for numerical computing'),
            ('asyncpg', 'AsyncPG for database connectivity'),
            ('redis', 'Redis for caching'),
        ]

        dep_status = {}

        for module_name, description in dependencies:
            try:
                __import__(module_name)
                dep_status[module_name] = {
                    'available': True,
                    'description': description
                }
                logger.info(f"  ✅ {module_name}: {description}")

            except ImportError as e:
                dep_status[module_name] = {
                    'available': False,
                    'description': description,
                    'error': str(e)
                }
                logger.error(f"  ❌ {module_name}: {e}")

        return {
            'status': 'success',
            'dependencies': dep_status
        }

    def _generate_readiness_summary(self, checks: Dict) -> Dict:
        """Generate a summary of training readiness."""
        issues = []
        warnings = []

        # Check database
        if checks['database']['status'] != 'success':
            issues.append("Database connectivity issues")

        # Check data sufficiency
        if 'data' in checks and checks['data']['status'] == 'warning':
            warnings.append("Insufficient training data")

        # Check dependencies
        if 'dependencies' in checks:
            missing_deps = [
                name for name, info in checks['dependencies']['dependencies'].items()
                if not info['available']
            ]
            if missing_deps:
                issues.append(f"Missing dependencies: {', '.join(missing_deps)}")

        # Determine overall readiness
        if issues:
            readiness = 'not_ready'
            message = f"Training not ready. Issues: {'; '.join(issues)}"
        elif warnings:
            readiness = 'ready_with_warnings'
            message = f"Training ready with warnings: {'; '.join(warnings)}"
        else:
            readiness = 'ready'
            message = "System ready for ML training!"

        return {
            'readiness': readiness,
            'message': message,
            'issues': issues,
            'warnings': warnings,
            'check_date': self.start_time.isoformat()
        }

    async def create_sample_data(self, num_users: int = 100, num_tracks: int = 500) -> Dict:
        """Create sample data for testing (development only)."""
        logger.info(f"🎭 Creating sample data ({num_users} users, {num_tracks} tracks)")

        try:
            conn = await get_db_connection()

            # Get or create organization
            org_result = await conn.fetchrow("SELECT id FROM organizations LIMIT 1")
            if not org_result:
                org_id = await conn.fetchval("""
                    INSERT INTO organizations (name, slug, plan)
                    VALUES ('Sample Org', 'sample', 'free')
                    RETURNING id
                """)
                logger.info("Created sample organization")
            else:
                org_id = org_result['id']

            # Create sample users
            created_users = 0
            for i in range(num_users):
                try:
                    await conn.execute("""
                        INSERT INTO users (org_id, email, username, full_name, is_active)
                        VALUES ($1, $2, $3, $4, true)
                    """,
                        org_id,
                        f"user{i}@sample.com",
                        f"user{i}",
                        f"Sample User {i}"
                    )
                    created_users += 1
                except Exception as e:
                    logger.debug(f"Failed to create user {i}: {e}")

            # Create sample tracks
            genres = ['Pop', 'Rock', 'Electronic', 'Hip-Hop', 'Jazz', 'Classical', 'Country', 'R&B']
            created_tracks = 0

            for i in range(num_tracks):
                try:
                    genre = genres[i % len(genres)]
                    await conn.execute("""
                        INSERT INTO tracks (org_id, title, artist, album, genre, duration_seconds, release_year)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        org_id,
                        f"Sample Track {i}",
                        f"Artist {i // 10}",
                        f"Album {i // 20}",
                        genre,
                        180 + (i % 120),  # 3-5 minutes
                        2020 + (i % 5)   # 2020-2024
                    )
                    created_tracks += 1
                except Exception as e:
                    logger.debug(f"Failed to create track {i}: {e}")

            # Create sample interactions
            user_ids = await conn.fetch("SELECT id FROM users ORDER BY created_at DESC LIMIT $1", created_users)
            track_ids = await conn.fetch("SELECT id FROM tracks ORDER BY created_at DESC LIMIT $1", created_tracks)

            created_interactions = 0
            interaction_types = ['play', 'like', 'skip']

            for user in user_ids:
                # Each user interacts with 10-50 tracks
                num_interactions = 10 + (hash(str(user['id'])) % 40)

                for j in range(num_interactions):
                    try:
                        track = track_ids[j % len(track_ids)]
                        interaction_type = interaction_types[j % len(interaction_types)]

                        # Create interaction at random time in past 30 days
                        random_time = datetime.now() - timedelta(
                            days=j % 30,
                            hours=j % 24,
                            minutes=j % 60
                        )

                        await conn.execute("""
                            INSERT INTO interactions (user_id, track_id, interaction_type, created_at)
                            VALUES ($1, $2, $3, $4)
                        """,
                            user['id'],
                            track['id'],
                            interaction_type,
                            random_time
                        )
                        created_interactions += 1

                    except Exception as e:
                        logger.debug(f"Failed to create interaction: {e}")

            await conn.close()

            result = {
                'status': 'success',
                'created': {
                    'users': created_users,
                    'tracks': created_tracks,
                    'interactions': created_interactions
                },
                'message': f'Sample data created: {created_users} users, {created_tracks} tracks, {created_interactions} interactions'
            }

            logger.info("✅ Sample data creation completed")
            return result

        except Exception as e:
            logger.error(f"❌ Sample data creation failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _check_model_directories(self) -> Dict:
        """Check model directory structure."""
        required_dirs = [
            Config.MODEL_SAVE_PATH,
            os.path.join(Config.MODEL_SAVE_PATH, "free"),
            os.path.join(Config.MODEL_SAVE_PATH, "starter"),
            os.path.join(Config.MODEL_SAVE_PATH, "pro"),
            os.path.join(Config.MODEL_SAVE_PATH, "enterprise"),
            os.path.join(Config.MODEL_SAVE_PATH, "logs"),
            Config.FAISS_INDEX_PATH,
        ]

        for directory in required_dirs:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"  ✅ {directory}")
            except Exception as e:
                logger.error(f"  ❌ {directory}: {e}")
                return {'status': 'error', 'error': f'Failed to create {directory}'}

        return {'status': 'success', 'message': 'All model directories ready'}

    def _check_dependencies(self) -> Dict:
        """Check Python dependencies."""
        critical_deps = [
            'torch', 'sklearn', 'faiss', 'numpy',
            'asyncpg', 'redis', 'pytorch_lightning'
        ]

        missing = []
        for dep in critical_deps:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)

        if missing:
            return {
                'status': 'error',
                'missing_dependencies': missing,
                'message': f'Missing dependencies: {", ".join(missing)}'
            }

        return {
            'status': 'success',
            'message': 'All dependencies available'
        }


async def main():
    """Main function to setup training environment."""
    parser = argparse.ArgumentParser(description='Setup TuneTrail ML training environment')
    parser.add_argument(
        '--check-data',
        action='store_true',
        help='Check data availability and quality'
    )
    parser.add_argument(
        '--create-sample',
        action='store_true',
        help='Create sample data for testing (development only)'
    )

    args = parser.parse_args()

    try:
        setup = TrainingSetup()

        if args.create_sample:
            # Create sample data
            result = await setup.create_sample_data()
            if result['status'] == 'error':
                logger.error(f"Sample data creation failed: {result['error']}")
                sys.exit(1)

        # Always check readiness
        readiness = await setup.check_training_readiness()

        # Display results
        summary = readiness.get('summary', {})
        logger.info(f"\n🎯 TRAINING READINESS: {summary.get('readiness', 'unknown').upper()}")
        logger.info(f"📝 {summary.get('message', '')}")

        if summary.get('issues'):
            logger.error("Issues to resolve:")
            for issue in summary['issues']:
                logger.error(f"  • {issue}")

        if summary.get('warnings'):
            logger.warning("Warnings:")
            for warning in summary['warnings']:
                logger.warning(f"  • {warning}")

        # Show data recommendations
        if 'data' in readiness and 'recommendations' in readiness['data']:
            logger.info("\n💡 Recommendations:")
            for rec in readiness['data']['recommendations']:
                logger.info(f"  • {rec}")

        # Exit code based on readiness
        if summary.get('readiness') == 'not_ready':
            sys.exit(1)
        elif summary.get('readiness') == 'ready_with_warnings':
            logger.info("✅ Training can proceed with warnings")
            sys.exit(0)
        else:
            logger.info("✅ System fully ready for ML training!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())