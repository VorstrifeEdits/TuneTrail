#!/usr/bin/env python3
"""
TuneTrail ML Engine - FAISS Index Builder

Build and optimize FAISS indexes for fast similarity search on audio embeddings.

Usage:
    python scripts/build_faiss_index.py [--force] [--gpu] [--index-type flat|ivf]

Examples:
    python scripts/build_faiss_index.py --gpu --index-type ivf
    python scripts/build_faiss_index.py --force
"""

import asyncio
import argparse
import sys
import os
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import faiss
from config import Config
from data.loaders import load_audio_features
from utils.similarity import build_faiss_index


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("build_faiss_index")


class FAISSIndexBuilder:
    """FAISS index builder for audio embeddings."""

    def __init__(self, force_rebuild: bool = False, use_gpu: bool = False):
        self.force_rebuild = force_rebuild
        self.use_gpu = use_gpu and Config.ENABLE_GPU
        self.start_time = datetime.now()

    async def build_all_indexes(self, index_type: str = "auto") -> Dict:
        """
        Build all FAISS indexes for similarity search.

        Args:
            index_type: Type of index to build ("flat", "ivf", or "auto")

        Returns:
            Dictionary with build results and metrics
        """
        logger.info("🔍 Building FAISS Indexes")
        logger.info("=" * 40)
        logger.info(f"Index type: {index_type}")
        logger.info(f"GPU enabled: {self.use_gpu}")
        logger.info(f"Force rebuild: {self.force_rebuild}")

        try:
            # Load audio features
            audio_features = await self._load_and_validate_features()

            if not audio_features:
                raise ValueError("No audio features available for index building")

            # Build main embedding index
            main_index_result = await self._build_embedding_index(audio_features, index_type)

            # Build additional specialized indexes
            results = {
                'main_embedding_index': main_index_result,
                'build_summary': self._generate_build_summary(main_index_result)
            }

            logger.info("✅ All FAISS indexes built successfully!")
            return results

        except Exception as e:
            logger.error(f"FAISS index building failed: {e}")
            raise

    async def _load_and_validate_features(self) -> List[Dict]:
        """Load and validate audio features."""
        logger.info("📊 Loading audio features...")

        audio_features = await load_audio_features()
        logger.info(f"Loaded {len(audio_features)} audio feature records")

        if not audio_features:
            return []

        # Validate embeddings
        valid_features = []
        for feature in audio_features:
            if feature.get('embedding') and len(feature['embedding']) == 512:
                valid_features.append(feature)

        logger.info(f"Found {len(valid_features)} valid 512-dimensional embeddings")

        if len(valid_features) < 10:
            logger.warning("Very few valid embeddings found. Index quality may be poor.")

        return valid_features

    async def _build_embedding_index(self, audio_features: List[Dict], index_type: str) -> Dict:
        """Build the main embedding similarity index."""
        logger.info("🏗️ Building main embedding similarity index...")

        # Extract embeddings
        embeddings = np.array([f['embedding'] for f in audio_features], dtype=np.float32)
        track_ids = [f['track_id'] for f in audio_features]

        logger.info(f"Building index with {len(embeddings)} vectors of dimension {embeddings.shape[1]}")

        # Determine index type automatically if needed
        if index_type == "auto":
            if len(embeddings) < 1000:
                index_type = "flat"
                logger.info("Auto-selected IndexFlatIP (< 1000 vectors)")
            else:
                index_type = "ivf"
                logger.info("Auto-selected IndexIVFFlat (>= 1000 vectors)")

        # Build index
        start_time = datetime.now()

        try:
            if index_type == "flat":
                index = self._build_flat_index(embeddings)
            elif index_type == "ivf":
                index = self._build_ivf_index(embeddings)
            else:
                raise ValueError(f"Unknown index type: {index_type}")

            build_duration = (datetime.now() - start_time).total_seconds()

            # Test index performance
            test_results = self._test_index_performance(index, embeddings)

            # Save index and metadata
            self._save_index_and_metadata(index, track_ids, index_type, test_results)

            result = {
                'index_type': index_type,
                'num_vectors': len(embeddings),
                'dimension': embeddings.shape[1],
                'build_time_seconds': build_duration,
                'use_gpu': self.use_gpu,
                'performance_metrics': test_results,
                'index_size_mb': self._estimate_index_size(index),
                'status': 'success'
            }

            logger.info(f"✅ {index_type.upper()} index built successfully in {build_duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Failed to build {index_type} index: {e}")
            return {
                'index_type': index_type,
                'status': 'error',
                'error': str(e)
            }

    def _build_flat_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build IndexFlatIP for exact similarity search."""
        logger.info("Building IndexFlatIP (exact search)...")

        dimension = embeddings.shape[1]

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        if self.use_gpu and faiss.get_num_gpus() > 0:
            logger.info("Using GPU acceleration")
            res = faiss.StandardGpuResources()
            index = faiss.GpuIndexFlatIP(res, dimension)
        else:
            index = faiss.IndexFlatIP(dimension)

        index.add(embeddings)
        return index

    def _build_ivf_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build IndexIVFFlat for approximate similarity search."""
        logger.info("Building IndexIVFFlat (approximate search)...")

        dimension = embeddings.shape[1]
        nlist = min(Config.FAISS_NLIST, len(embeddings) // 10)  # Reasonable nlist

        logger.info(f"Using nlist={nlist} for {len(embeddings)} vectors")

        # Normalize embeddings
        faiss.normalize_L2(embeddings)

        # Create quantizer and index
        quantizer = faiss.IndexFlatIP(dimension)
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_INNER_PRODUCT)

        # Train index
        logger.info("Training IVF index...")
        index.train(embeddings)

        # Move to GPU if available
        if self.use_gpu and faiss.get_num_gpus() > 0:
            logger.info("Moving index to GPU")
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, 0, index)

        # Add vectors
        index.add(embeddings)

        # Set search parameters
        if hasattr(index, 'nprobe'):
            index.nprobe = Config.FAISS_NPROBE

        return index

    def _test_index_performance(self, index: faiss.Index, embeddings: np.ndarray) -> Dict:
        """Test index search performance."""
        logger.info("🧪 Testing index performance...")

        # Select random test queries
        num_queries = min(100, len(embeddings))
        query_indices = np.random.choice(len(embeddings), num_queries, replace=False)
        test_queries = embeddings[query_indices]

        # Test different k values
        k_values = [5, 10, 20]
        performance = {}

        for k in k_values:
            start_time = datetime.now()

            # Perform search
            distances, indices = index.search(test_queries, k)

            search_time = (datetime.now() - start_time).total_seconds()
            avg_time_per_query = search_time / num_queries * 1000  # ms

            performance[f'search_time_k{k}_ms'] = avg_time_per_query

            logger.info(f"K={k}: {avg_time_per_query:.2f}ms per query")

        # Test recall (for IVF indexes)
        if hasattr(index, 'nprobe'):
            recall = self._test_recall(index, embeddings, test_queries)
            performance['recall@10'] = recall

        return performance

    def _test_recall(self, index: faiss.Index, embeddings: np.ndarray, test_queries: np.ndarray) -> float:
        """Test recall for approximate index."""
        logger.info("Testing recall against exact search...")

        # Build exact index for ground truth
        exact_index = faiss.IndexFlatIP(embeddings.shape[1])
        exact_index.add(embeddings)

        k = 10
        num_test = min(20, len(test_queries))  # Test on subset

        recalls = []

        for i in range(num_test):
            query = test_queries[i:i+1]

            # Get approximate results
            _, approx_indices = index.search(query, k)

            # Get exact results
            _, exact_indices = exact_index.search(query, k)

            # Calculate recall
            approx_set = set(approx_indices[0])
            exact_set = set(exact_indices[0])

            recall = len(approx_set & exact_set) / k
            recalls.append(recall)

        avg_recall = np.mean(recalls)
        logger.info(f"Average Recall@{k}: {avg_recall:.3f}")

        return avg_recall

    def _estimate_index_size(self, index: faiss.Index) -> float:
        """Estimate index size in MB."""
        # Rough estimation based on index type and parameters
        if hasattr(index, 'ntotal'):
            num_vectors = index.ntotal
        else:
            num_vectors = 0

        dimension = index.d if hasattr(index, 'd') else 512

        # Estimate: 4 bytes per float + overhead
        estimated_bytes = num_vectors * dimension * 4 * 1.2  # 20% overhead
        return estimated_bytes / (1024 * 1024)  # Convert to MB

    def _save_index_and_metadata(
        self,
        index: faiss.Index,
        track_ids: List[str],
        index_type: str,
        performance_metrics: Dict
    ):
        """Save index and associated metadata."""
        logger.info("💾 Saving index and metadata...")

        # Ensure output directory exists
        os.makedirs(Config.FAISS_INDEX_PATH, exist_ok=True)

        # Save index
        index_path = os.path.join(Config.FAISS_INDEX_PATH, "audio_embeddings.index")

        # Move to CPU before saving if on GPU
        if hasattr(index, 'index'):  # GPU index wrapper
            cpu_index = faiss.index_gpu_to_cpu(index)
            faiss.write_index(cpu_index, index_path)
        else:
            faiss.write_index(index, index_path)

        logger.info(f"Index saved to: {index_path}")

        # Save track ID mapping
        import pickle
        mapping_path = os.path.join(Config.FAISS_INDEX_PATH, "track_id_mapping.pkl")
        with open(mapping_path, 'wb') as f:
            pickle.dump({
                'track_ids': track_ids,
                'index_type': index_type,
                'build_date': datetime.now().isoformat(),
                'performance_metrics': performance_metrics
            }, f)

        logger.info(f"Track mapping saved to: {mapping_path}")

        # Save index metadata
        metadata_path = os.path.join(Config.FAISS_INDEX_PATH, "index_metadata.json")
        metadata = {
            'index_type': index_type,
            'num_vectors': len(track_ids),
            'dimension': index.d if hasattr(index, 'd') else 512,
            'build_date': datetime.now().isoformat(),
            'gpu_enabled': self.use_gpu,
            'performance_metrics': performance_metrics,
            'index_file': 'audio_embeddings.index',
            'mapping_file': 'track_id_mapping.pkl'
        }

        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Metadata saved to: {metadata_path}")

    def _generate_build_summary(self, main_result: Dict) -> Dict:
        """Generate build summary."""
        duration = datetime.now() - self.start_time

        summary = {
            'total_build_time_seconds': duration.total_seconds(),
            'indexes_built': 1 if main_result.get('status') == 'success' else 0,
            'total_vectors': main_result.get('num_vectors', 0),
            'gpu_acceleration': self.use_gpu,
            'build_date': self.start_time.isoformat()
        }

        return summary


async def main():
    """Main function to build FAISS indexes."""
    parser = argparse.ArgumentParser(description='Build FAISS indexes for TuneTrail')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force rebuild even if indexes exist'
    )
    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Use GPU acceleration (if available)'
    )
    parser.add_argument(
        '--index-type',
        choices=['flat', 'ivf', 'auto'],
        default='auto',
        help='Type of index to build (default: auto)'
    )

    args = parser.parse_args()

    try:
        builder = FAISSIndexBuilder(
            force_rebuild=args.force,
            use_gpu=args.gpu
        )

        results = await builder.build_all_indexes(args.index_type)

        # Log summary
        summary = results.get('build_summary', {})
        logger.info(f"\n📈 BUILD SUMMARY")
        logger.info(f"Total time: {summary.get('total_build_time_seconds', 0):.2f}s")
        logger.info(f"Indexes built: {summary.get('indexes_built', 0)}")
        logger.info(f"Total vectors: {summary.get('total_vectors', 0)}")

        logger.info("✅ FAISS index building completed successfully!")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Index building interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Index building failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())