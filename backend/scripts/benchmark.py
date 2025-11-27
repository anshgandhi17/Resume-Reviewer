"""
Benchmarking Script for RAG Pipeline
Compares baseline vs enhanced RAG with various configurations.
"""

import sys
import time
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.vector_store import VectorStore
from app.services.enhanced_analysis_service import EnhancedAnalysisService
from app.core.config import settings
from app.evaluation.llm_judge import llm_judge
from app.evaluation.ragas_eval import ragas_evaluator

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGBenchmark:
    """
    Benchmark different RAG configurations.

    Tests:
    1. Baseline (no HyDE, no re-ranking)
    2. HyDE only
    3. Re-ranking only
    4. Both HyDE + Re-ranking (full pipeline)
    """

    def __init__(self):
        self.enhanced_service = EnhancedAnalysisService()
        self.results = []

    def run_benchmark(
        self,
        test_cases: List[Dict],
        output_file: str = None
    ) -> Dict:
        """
        Run benchmark on test cases.

        Args:
            test_cases: List of test cases with 'resume_path' and 'job_description'
            output_file: Optional file to save results

        Returns:
            Benchmark results
        """
        logger.info(f"Starting benchmark with {len(test_cases)} test cases")

        configurations = [
            {"name": "baseline", "use_hyde": False, "use_reranking": False},
            {"name": "hyde_only", "use_hyde": True, "use_reranking": False},
            {"name": "reranking_only", "use_hyde": False, "use_reranking": True},
            {"name": "full_pipeline", "use_hyde": True, "use_reranking": True},
        ]

        results = {
            "configurations": {},
            "test_cases": [],
            "summary": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        for config in configurations:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing configuration: {config['name']}")
            logger.info(f"{'='*60}")

            # Temporarily update settings
            original_hyde = settings.use_hyde
            original_reranking = settings.use_reranking

            settings.use_hyde = config['use_hyde']
            settings.use_reranking = config['use_reranking']

            config_results = self._run_configuration(
                config['name'],
                test_cases
            )

            results["configurations"][config['name']] = config_results

            # Restore original settings
            settings.use_hyde = original_hyde
            settings.use_reranking = original_reranking

        # Calculate summary statistics
        results["summary"] = self._calculate_summary(results["configurations"])

        # Save results
        if output_file:
            self._save_results(results, output_file)

        logger.info("\n" + "="*60)
        logger.info("BENCHMARK COMPLETE")
        logger.info("="*60)
        self._print_summary(results["summary"])

        return results

    def _run_configuration(
        self,
        config_name: str,
        test_cases: List[Dict]
    ) -> Dict:
        """Run tests for a specific configuration."""
        config_results = {
            "metrics": {
                "avg_latency": 0,
                "avg_retrieval_score": 0,
                "avg_eval_score": 0
            },
            "test_results": []
        }

        total_latency = 0
        total_retrieval_score = 0
        total_eval_score = 0
        successful_tests = 0

        for i, test_case in enumerate(test_cases):
            logger.info(f"\nTest case {i+1}/{len(test_cases)}")

            try:
                start_time = time.time()

                # Run analysis
                result = self.enhanced_service.analyze_resume_enhanced(
                    resume_path=test_case['resume_path'],
                    job_description=test_case['job_description'],
                    enable_evaluation=True
                )

                latency = time.time() - start_time

                # Extract metrics
                retrieval_score = result['match_analysis']['overall_score']

                eval_score = 0
                if result.get('evaluation'):
                    eval_score = result['evaluation'].get('overall_score', 0)

                # Store result
                test_result = {
                    "test_case_id": i,
                    "latency": latency,
                    "retrieval_score": retrieval_score,
                    "eval_score": eval_score,
                    "chunks_retrieved": result['rag_metadata']['chunks_retrieved'],
                    "success": True
                }

                config_results["test_results"].append(test_result)

                # Accumulate for averages
                total_latency += latency
                total_retrieval_score += retrieval_score
                total_eval_score += eval_score
                successful_tests += 1

                logger.info(
                    f"  Latency: {latency:.2f}s | "
                    f"Retrieval: {retrieval_score:.1f} | "
                    f"Eval: {eval_score:.2f}"
                )

            except Exception as e:
                logger.error(f"  Error in test case {i}: {str(e)}")
                config_results["test_results"].append({
                    "test_case_id": i,
                    "success": False,
                    "error": str(e)
                })

        # Calculate averages
        if successful_tests > 0:
            config_results["metrics"]["avg_latency"] = total_latency / successful_tests
            config_results["metrics"]["avg_retrieval_score"] = total_retrieval_score / successful_tests
            config_results["metrics"]["avg_eval_score"] = total_eval_score / successful_tests
            config_results["metrics"]["success_rate"] = successful_tests / len(test_cases)

        return config_results

    def _calculate_summary(self, configurations: Dict) -> Dict:
        """Calculate summary statistics across configurations."""
        summary = {
            "best_latency": None,
            "best_retrieval": None,
            "best_eval": None,
            "comparison": {}
        }

        # Find best configurations
        best_latency = float('inf')
        best_retrieval = 0
        best_eval = 0

        for config_name, config_results in configurations.items():
            metrics = config_results["metrics"]

            if metrics["avg_latency"] < best_latency:
                best_latency = metrics["avg_latency"]
                summary["best_latency"] = config_name

            if metrics["avg_retrieval_score"] > best_retrieval:
                best_retrieval = metrics["avg_retrieval_score"]
                summary["best_retrieval"] = config_name

            if metrics["avg_eval_score"] > best_eval:
                best_eval = metrics["avg_eval_score"]
                summary["best_eval"] = config_name

        # Calculate improvement over baseline
        if "baseline" in configurations and "full_pipeline" in configurations:
            baseline = configurations["baseline"]["metrics"]
            full_pipeline = configurations["full_pipeline"]["metrics"]

            summary["comparison"]["latency_change"] = (
                (full_pipeline["avg_latency"] - baseline["avg_latency"]) / baseline["avg_latency"] * 100
            )

            summary["comparison"]["retrieval_improvement"] = (
                full_pipeline["avg_retrieval_score"] - baseline["avg_retrieval_score"]
            )

            summary["comparison"]["eval_improvement"] = (
                full_pipeline["avg_eval_score"] - baseline["avg_eval_score"]
            )

        return summary

    def _print_summary(self, summary: Dict):
        """Print benchmark summary."""
        print("\nBENCHMARK SUMMARY")
        print("-" * 60)
        print(f"Best Latency: {summary.get('best_latency', 'N/A')}")
        print(f"Best Retrieval Score: {summary.get('best_retrieval', 'N/A')}")
        print(f"Best Evaluation Score: {summary.get('best_eval', 'N/A')}")

        if "comparison" in summary:
            comp = summary["comparison"]
            print("\nFull Pipeline vs Baseline:")
            print(f"  Latency Change: {comp.get('latency_change', 0):.1f}%")
            print(f"  Retrieval Improvement: {comp.get('retrieval_improvement', 0):.2f}")
            print(f"  Eval Improvement: {comp.get('eval_improvement', 0):.2f}")

    def _save_results(self, results: Dict, output_file: str):
        """Save results to JSON file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"\nResults saved to: {output_path}")


def create_sample_test_cases() -> List[Dict]:
    """
    Create sample test cases for demonstration.
    Replace with your actual test data.
    """
    return [
        {
            "resume_path": "./test_data/sample_resume_1.pdf",
            "job_description": """
                Senior Software Engineer
                Requirements:
                - 5+ years of Python experience
                - Strong background in machine learning
                - Experience with cloud platforms (AWS/GCP)
                - Excellent communication skills
            """
        },
        {
            "resume_path": "./test_data/sample_resume_2.pdf",
            "job_description": """
                Data Scientist
                Requirements:
                - PhD or Master's in Computer Science, Statistics, or related field
                - Experience with deep learning frameworks (PyTorch, TensorFlow)
                - Strong SQL and data analysis skills
                - Published research is a plus
            """
        }
    ]


def main():
    """Main entry point for benchmarking."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark RAG Pipeline")
    parser.add_argument(
        "--test-cases",
        type=str,
        help="Path to JSON file with test cases"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./benchmark_results/results.json",
        help="Output file for results"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test with sample data"
    )

    args = parser.parse_args()

    # Load test cases
    if args.test_cases:
        with open(args.test_cases, 'r') as f:
            test_cases = json.load(f)
    elif args.quick:
        logger.info("Running quick test with sample data")
        test_cases = create_sample_test_cases()
    else:
        logger.error("Please provide --test-cases or use --quick for sample data")
        return

    # Run benchmark
    benchmark = RAGBenchmark()
    results = benchmark.run_benchmark(test_cases, output_file=args.output)

    logger.info("\nBenchmark complete!")


if __name__ == "__main__":
    main()
