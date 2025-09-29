#!/usr/bin/env python3
"""
TuneTrail ML Engine - Model Evaluation Script

Evaluate all trained recommendation models and generate performance reports.

Usage:
    python scripts/evaluate_models.py [--models MODEL1,MODEL2] [--output report.json]

Examples:
    python scripts/evaluate_models.py
    python scripts/evaluate_models.py --models collaborative_filter,neural_cf
    python scripts/evaluate_models.py --output /models/evaluation_report.json
"""

import asyncio
import argparse
import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.evaluators import ModelEvaluator
from config import Config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("evaluate_models")


class EvaluationRunner:
    """Comprehensive model evaluation runner."""

    def __init__(self):
        self.evaluator = ModelEvaluator()
        self.start_time = datetime.now()

    async def run_evaluation(
        self,
        model_names: Optional[List[str]] = None,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Run model evaluation.

        Args:
            model_names: Specific models to evaluate, or None for all
            output_path: Path to save evaluation report

        Returns:
            Evaluation results dictionary
        """
        logger.info("🔍 Starting Model Evaluation")
        logger.info("=" * 50)

        try:
            if model_names:
                logger.info(f"Evaluating specific models: {', '.join(model_names)}")
                results = await self._evaluate_specific_models(model_names)
            else:
                logger.info("Evaluating all available models")
                results = await self.evaluator.evaluate_all_models()

            # Generate detailed report
            self._log_evaluation_results(results)

            # Save results if output path specified
            if output_path:
                self._save_results(results, output_path)

            return results

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise

    async def _evaluate_specific_models(self, model_names: List[str]) -> Dict:
        """Evaluate specific models by name."""
        from data.loaders import load_training_data

        # Load test data
        train_data, test_data = await load_training_data(train_ratio=0.8)

        if not test_data:
            raise ValueError("No test data available for evaluation")

        results = {}

        for model_name in model_names:
            logger.info(f"Evaluating {model_name}...")

            try:
                model = await self._load_model(model_name)
                if model:
                    evaluation = await self.evaluator.evaluate_model(
                        model, model_name, test_data
                    )
                    results[model_name] = evaluation
                    logger.info(f"✅ {model_name} evaluation completed")
                else:
                    logger.warning(f"⚠️ {model_name} model not found or failed to load")
                    results[model_name] = {'error': 'Model not found or failed to load'}

            except Exception as e:
                logger.error(f"❌ {model_name} evaluation failed: {e}")
                results[model_name] = {'error': str(e)}

        return results

    async def _load_model(self, model_name: str):
        """Load a specific model by name."""
        model_path_map = {
            'collaborative_filter': os.path.join(Config.MODEL_SAVE_PATH, "free", "collaborative_filter_als.pkl"),
            'popularity': os.path.join(Config.MODEL_SAVE_PATH, "free", "popularity.pkl"),
            'genre_based': os.path.join(Config.MODEL_SAVE_PATH, "free", "genre_based.pkl"),
            'content_based': os.path.join(Config.MODEL_SAVE_PATH, "starter", "content_based"),
            'neural_cf': os.path.join(Config.MODEL_SAVE_PATH, "pro", "neural_cf.pt"),
        }

        if model_name not in model_path_map:
            logger.error(f"Unknown model name: {model_name}")
            return None

        model_path = model_path_map[model_name]

        try:
            if model_name == 'collaborative_filter':
                from models.base.collaborative_filter import ALSCollaborativeFilter
                if os.path.exists(model_path):
                    return ALSCollaborativeFilter.load(model_path)

            elif model_name == 'popularity':
                from models.base.popularity import PopularityModel
                if os.path.exists(model_path):
                    return PopularityModel.load(model_path)

            elif model_name == 'genre_based':
                from models.base.genre_based import GenreBasedModel
                if os.path.exists(model_path):
                    return GenreBasedModel.load(model_path)

            elif model_name == 'content_based':
                from models.premium.content_based import ContentBasedModel
                if os.path.exists(f"{model_path}.pkl"):
                    return ContentBasedModel.load(model_path, use_gpu=Config.ENABLE_GPU)

            elif model_name == 'neural_cf':
                from models.enterprise.neural_cf import NeuralCF
                if os.path.exists(model_path):
                    device = 'cuda' if Config.ENABLE_GPU else 'cpu'
                    return NeuralCF.load(model_path, device=device)

        except Exception as e:
            logger.error(f"Failed to load {model_name}: {e}")
            return None

        logger.warning(f"Model file not found: {model_path}")
        return None

    def _log_evaluation_results(self, results: Dict):
        """Log evaluation results in a formatted way."""
        logger.info("\n📊 EVALUATION RESULTS")
        logger.info("=" * 50)

        # Individual model results
        for tier_or_model, tier_results in results.items():
            if tier_or_model == 'summary':
                continue

            if isinstance(tier_results, dict) and any(isinstance(v, dict) for v in tier_results.values()):
                # This is a tier with multiple models
                logger.info(f"\n🎯 {tier_or_model.upper().replace('_', ' ')}")
                logger.info("-" * 30)

                for model_name, model_results in tier_results.items():
                    if isinstance(model_results, dict):
                        if 'error' in model_results:
                            logger.error(f"❌ {model_name}: {model_results['error']}")
                        else:
                            self._log_model_metrics(model_name, model_results)
            else:
                # This is a single model result
                if isinstance(tier_results, dict):
                    if 'error' in tier_results:
                        logger.error(f"❌ {tier_or_model}: {tier_results['error']}")
                    else:
                        self._log_model_metrics(tier_or_model, tier_results)

        # Summary results
        if 'summary' in results:
            self._log_summary_results(results['summary'])

        # Overall duration
        duration = datetime.now() - self.start_time
        logger.info(f"\n⏱️ Total evaluation time: {duration}")

    def _log_model_metrics(self, model_name: str, results: Dict):
        """Log metrics for a single model."""
        logger.info(f"\n📈 {model_name}")

        # Key metrics to highlight
        key_metrics = ['recall@20', 'ndcg@20', 'mrr', 'map']

        for metric in key_metrics:
            if metric in results:
                logger.info(f"  {metric}: {results[metric]:.4f}")

        # Additional info
        if 'num_users_evaluated' in results:
            logger.info(f"  Users evaluated: {results['num_users_evaluated']}")

        if 'catalog_coverage' in results:
            logger.info(f"  Catalog coverage: {results['catalog_coverage']:.4f}")

    def _log_summary_results(self, summary: Dict):
        """Log summary comparison results."""
        logger.info("\n🏆 SUMMARY COMPARISON")
        logger.info("-" * 30)

        if 'best_models' in summary:
            logger.info("Best performing models:")
            for metric, info in summary['best_models'].items():
                logger.info(f"  {metric}: {info['model']} ({info['score']:.4f})")

        if 'tier_comparison' in summary:
            logger.info("\nTier performance comparison:")
            for tier, comparison in summary['tier_comparison'].items():
                scores = comparison.get('average_scores', {})
                if 'recall@20' in scores:
                    logger.info(f"  {tier}: Recall@20 = {scores['recall@20']:.4f}")

        if 'overall_winner' in summary and summary['overall_winner']:
            winner = summary['overall_winner']
            logger.info(f"\n🥇 Overall winner: {winner['tier']} (Recall@20: {winner['recall@20']:.4f})")

    def _save_results(self, results: Dict, output_path: str):
        """Save evaluation results to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Add metadata
            report = {
                'evaluation_date': self.start_time.isoformat(),
                'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
                'config': {
                    'gpu_enabled': Config.ENABLE_GPU,
                    'model_save_path': Config.MODEL_SAVE_PATH,
                },
                'results': results
            }

            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"📄 Evaluation report saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to save evaluation report: {e}")

    async def compare_models(self, model_names: List[str]) -> Dict:
        """Compare specific models side by side."""
        logger.info(f"🔄 Comparing models: {', '.join(model_names)}")

        results = await self._evaluate_specific_models(model_names)

        # Generate comparison
        comparison = {
            'models_compared': model_names,
            'metrics_comparison': {},
            'winner_by_metric': {}
        }

        metrics_to_compare = ['recall@20', 'ndcg@20', 'mrr', 'map', 'catalog_coverage']

        for metric in metrics_to_compare:
            metric_scores = {}
            for model_name in model_names:
                if model_name in results and metric in results[model_name]:
                    metric_scores[model_name] = results[model_name][metric]

            if metric_scores:
                comparison['metrics_comparison'][metric] = metric_scores

                # Find winner for this metric
                best_model = max(metric_scores, key=metric_scores.get)
                comparison['winner_by_metric'][metric] = {
                    'model': best_model,
                    'score': metric_scores[best_model]
                }

        logger.info("\n🔄 Model Comparison Results:")
        for metric, winner in comparison['winner_by_metric'].items():
            logger.info(f"  {metric}: {winner['model']} ({winner['score']:.4f})")

        return comparison


async def main():
    """Main function to run model evaluation."""
    parser = argparse.ArgumentParser(description='Evaluate TuneTrail ML Models')
    parser.add_argument(
        '--models',
        type=str,
        help='Comma-separated list of specific models to evaluate'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output path for evaluation report (default: print to console)'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare models side by side (requires --models)'
    )

    args = parser.parse_args()

    # Parse model names
    model_names = None
    if args.models:
        model_names = [name.strip() for name in args.models.split(',')]

    try:
        runner = EvaluationRunner()

        if args.compare:
            if not model_names or len(model_names) < 2:
                logger.error("Comparison requires at least 2 models specified with --models")
                sys.exit(1)

            results = await runner.compare_models(model_names)

            if args.output:
                runner._save_results({'comparison': results}, args.output)

        else:
            # Set default output path if not specified
            if args.output is None and not model_names:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                args.output = os.path.join(Config.MODEL_SAVE_PATH, f"evaluation_report_{timestamp}.json")

            results = await runner.run_evaluation(model_names, args.output)

        logger.info("✅ Model evaluation completed successfully!")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Evaluation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())