import asyncio
from typing import Dict, List, Tuple, Optional
from uuid import UUID
import numpy as np
from datetime import datetime
import logging

from utils.metrics import compute_recall_at_k, compute_ndcg, compute_mrr, compute_map, compute_precision_at_k, compute_f1_score
from utils.db import get_db_connection, fetch_interactions, fetch_tracks
from data.loaders import load_training_data


class ModelEvaluator:
    """Comprehensive model evaluation framework."""

    def __init__(self):
        self.logger = logging.getLogger("evaluator")

    async def evaluate_model(
        self,
        model,
        model_type: str,
        test_interactions: List[Dict],
        k_values: List[int] = [5, 10, 20],
        min_interactions: int = 5
    ) -> Dict:
        """
        Evaluate a recommendation model using standard metrics.

        Args:
            model: Trained recommendation model
            model_type: Type of model ('collaborative_filter', 'content_based', etc.)
            test_interactions: Test interaction data
            k_values: Values of k for Recall@K, NDCG@K evaluation
            min_interactions: Minimum interactions per user for evaluation

        Returns:
            Dictionary containing evaluation metrics
        """
        self.logger.info(f"Evaluating {model_type} model...")

        # Group interactions by user
        user_interactions = {}
        for interaction in test_interactions:
            user_id = interaction['user_id']
            if user_id not in user_interactions:
                user_interactions[user_id] = []
            user_interactions[user_id].append(interaction)

        # Filter users with sufficient interactions
        valid_users = {
            user_id: interactions
            for user_id, interactions in user_interactions.items()
            if len(interactions) >= min_interactions
        }

        if not valid_users:
            self.logger.warning("No users with sufficient interactions for evaluation")
            return {}

        self.logger.info(f"Evaluating on {len(valid_users)} users with {min_interactions}+ interactions")

        # Evaluate each user
        all_recommendations = []
        all_relevant_items = []

        for user_id, interactions in valid_users.items():
            # Get relevant items (tracks user actually interacted with positively)
            relevant_tracks = set()
            for interaction in interactions:
                if interaction['interaction_type'] in ['play', 'like']:
                    relevant_tracks.add(interaction['track_id'])

            if not relevant_tracks:
                continue

            # Get recommendations from model
            try:
                if hasattr(model, 'recommend'):
                    # For traditional models (ALS, etc.)
                    recommendations = model.recommend(user_id, k=max(k_values))
                    recommended_tracks = [track_id for track_id, _ in recommendations]
                elif hasattr(model, 'get_recommendations'):
                    # For inference engine
                    recs = await model.get_recommendations(user_id, limit=max(k_values))
                    recommended_tracks = [rec['track_id'] for rec in recs]
                else:
                    self.logger.warning(f"Model {model_type} has no recommendation method")
                    continue

                all_recommendations.append(recommended_tracks)
                all_relevant_items.append(relevant_tracks)

            except Exception as e:
                self.logger.error(f"Error getting recommendations for user {user_id}: {e}")
                continue

        if not all_recommendations:
            self.logger.error("No recommendations generated for evaluation")
            return {}

        # Calculate metrics
        metrics = {}

        for k in k_values:
            # Recall@K
            recall_scores = []
            ndcg_scores = []
            precision_scores = []

            for recommended, relevant in zip(all_recommendations, all_relevant_items):
                recall = compute_recall_at_k(recommended, relevant, k)
                ndcg = compute_ndcg(recommended, relevant, k)
                precision = compute_precision_at_k(recommended, relevant, k)

                recall_scores.append(recall)
                ndcg_scores.append(ndcg)
                precision_scores.append(precision)

            metrics[f'recall@{k}'] = np.mean(recall_scores)
            metrics[f'ndcg@{k}'] = np.mean(ndcg_scores)
            metrics[f'precision@{k}'] = np.mean(precision_scores)

            # F1 score
            if metrics[f'precision@{k}'] + metrics[f'recall@{k}'] > 0:
                f1 = compute_f1_score(metrics[f'precision@{k}'], metrics[f'recall@{k}'])
                metrics[f'f1@{k}'] = f1
            else:
                metrics[f'f1@{k}'] = 0.0

        # MRR (Mean Reciprocal Rank)
        mrr_scores = []
        for recommended, relevant in zip(all_recommendations, all_relevant_items):
            mrr = compute_mrr(recommended, relevant)
            mrr_scores.append(mrr)
        metrics['mrr'] = np.mean(mrr_scores)

        # MAP (Mean Average Precision)
        map_score = compute_map(all_recommendations, all_relevant_items)
        metrics['map'] = map_score

        # Coverage metrics
        all_recommended_items = set()
        for recommended in all_recommendations:
            all_recommended_items.update(recommended[:20])  # Top 20

        all_relevant_unique = set()
        for relevant in all_relevant_items:
            all_relevant_unique.update(relevant)

        # Catalog coverage
        total_items = len(all_relevant_unique)
        metrics['catalog_coverage'] = len(all_recommended_items) / total_items if total_items > 0 else 0

        # Add metadata
        metrics['model_type'] = model_type
        metrics['num_users_evaluated'] = len(all_recommendations)
        metrics['total_interactions'] = len(test_interactions)
        metrics['evaluation_date'] = datetime.utcnow().isoformat()

        self.logger.info(f"Evaluation complete. Key metrics:")
        for k in k_values:
            self.logger.info(f"  Recall@{k}: {metrics[f'recall@{k}']:.4f}")
            self.logger.info(f"  NDCG@{k}: {metrics[f'ndcg@{k}']:.4f}")
        self.logger.info(f"  MRR: {metrics['mrr']:.4f}")
        self.logger.info(f"  MAP: {metrics['map']:.4f}")

        return metrics

    async def evaluate_all_models(self) -> Dict:
        """Evaluate all trained models using test data."""
        self.logger.info("Starting comprehensive model evaluation...")

        # Load test data
        train_data, test_data = await load_training_data(train_ratio=0.8)

        if not test_data:
            self.logger.error("No test data available for evaluation")
            return {}

        results = {}

        # Evaluate Free Tier Models
        results['free_tier'] = await self._evaluate_free_tier_models(test_data)

        # Evaluate Starter Tier Models
        results['starter_tier'] = await self._evaluate_starter_tier_models(test_data)

        # Evaluate Pro Tier Models
        results['pro_tier'] = await self._evaluate_pro_tier_models(test_data)

        # Generate summary report
        results['summary'] = self._generate_summary_report(results)

        return results

    async def _evaluate_free_tier_models(self, test_data: List[Dict]) -> Dict:
        """Evaluate free tier models."""
        results = {}

        try:
            # Collaborative Filter (ALS)
            from models.base.collaborative_filter import ALSCollaborativeFilter
            import os
            from config import Config

            cf_path = os.path.join(Config.MODEL_SAVE_PATH, "free", "collaborative_filter_als.pkl")
            if os.path.exists(cf_path):
                cf_model = ALSCollaborativeFilter.load(cf_path)
                results['collaborative_filter'] = await self.evaluate_model(
                    cf_model, 'collaborative_filter', test_data
                )

            # Popularity Model
            from models.base.popularity import PopularityModel
            pop_path = os.path.join(Config.MODEL_SAVE_PATH, "free", "popularity.pkl")
            if os.path.exists(pop_path):
                pop_model = PopularityModel.load(pop_path)
                results['popularity'] = await self.evaluate_model(
                    pop_model, 'popularity', test_data
                )

        except Exception as e:
            self.logger.error(f"Error evaluating free tier models: {e}")

        return results

    async def _evaluate_starter_tier_models(self, test_data: List[Dict]) -> Dict:
        """Evaluate starter tier models."""
        results = {}

        try:
            # Content-Based Model
            from models.premium.content_based import ContentBasedModel
            import os
            from config import Config

            content_path = os.path.join(Config.MODEL_SAVE_PATH, "starter", "content_based")
            if os.path.exists(f"{content_path}.pkl"):
                content_model = ContentBasedModel.load(content_path, use_gpu=Config.ENABLE_GPU)
                results['content_based'] = await self.evaluate_model(
                    content_model, 'content_based', test_data
                )

        except Exception as e:
            self.logger.error(f"Error evaluating starter tier models: {e}")

        return results

    async def _evaluate_pro_tier_models(self, test_data: List[Dict]) -> Dict:
        """Evaluate pro tier models."""
        results = {}

        try:
            # Neural CF Model
            from models.enterprise.neural_cf import NeuralCF
            import os
            from config import Config

            ncf_path = os.path.join(Config.MODEL_SAVE_PATH, "pro", "neural_cf.pt")
            if os.path.exists(ncf_path):
                ncf_model = NeuralCF.load(ncf_path, device='cuda' if Config.ENABLE_GPU else 'cpu')
                results['neural_cf'] = await self.evaluate_model(
                    ncf_model, 'neural_cf', test_data
                )

        except Exception as e:
            self.logger.error(f"Error evaluating pro tier models: {e}")

        return results

    def _generate_summary_report(self, results: Dict) -> Dict:
        """Generate a summary report comparing all models."""
        summary = {
            'best_models': {},
            'tier_comparison': {},
            'overall_winner': None
        }

        # Find best model for each metric
        metrics_to_compare = ['recall@20', 'ndcg@20', 'mrr', 'map']

        for metric in metrics_to_compare:
            best_score = 0
            best_model = None

            for tier, tier_results in results.items():
                if tier == 'summary':
                    continue

                for model_name, model_results in tier_results.items():
                    if isinstance(model_results, dict) and metric in model_results:
                        score = model_results[metric]
                        if score > best_score:
                            best_score = score
                            best_model = f"{tier}_{model_name}"

            if best_model:
                summary['best_models'][metric] = {
                    'model': best_model,
                    'score': best_score
                }

        # Calculate tier averages
        for tier, tier_results in results.items():
            if tier == 'summary':
                continue

            tier_scores = {}
            model_count = 0

            for metric in metrics_to_compare:
                scores = []
                for model_name, model_results in tier_results.items():
                    if isinstance(model_results, dict) and metric in model_results:
                        scores.append(model_results[metric])

                if scores:
                    tier_scores[metric] = np.mean(scores)
                    model_count = len(scores)

            if tier_scores:
                summary['tier_comparison'][tier] = {
                    'average_scores': tier_scores,
                    'num_models': model_count
                }

        # Determine overall winner (highest average Recall@20)
        if summary['tier_comparison']:
            best_tier_score = 0
            best_tier = None

            for tier, comparison in summary['tier_comparison'].items():
                if 'recall@20' in comparison['average_scores']:
                    score = comparison['average_scores']['recall@20']
                    if score > best_tier_score:
                        best_tier_score = score
                        best_tier = tier

            summary['overall_winner'] = {
                'tier': best_tier,
                'recall@20': best_tier_score
            }

        return summary

    async def run_evaluation_pipeline(self) -> Dict:
        """Run the complete evaluation pipeline and save results."""
        self.logger.info("Starting model evaluation pipeline...")

        try:
            results = await self.evaluate_all_models()

            # Save results
            import json
            import os
            from config import Config

            results_path = os.path.join(Config.MODEL_SAVE_PATH, "evaluation_results.json")
            os.makedirs(os.path.dirname(results_path), exist_ok=True)

            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            self.logger.info(f"Evaluation results saved to {results_path}")

            return results

        except Exception as e:
            self.logger.error(f"Evaluation pipeline failed: {e}")
            return {}