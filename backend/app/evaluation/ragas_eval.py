"""
Ragas Evaluation Module
Evaluates RAG pipeline quality using Ragas framework metrics.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import Ragas, but make it optional
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_recall,
        context_precision,
        context_relevancy
    )
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logger.warning("Ragas not installed. Evaluation will be disabled.")


class RagasEvaluator:
    """
    Evaluates RAG pipeline using Ragas metrics:
    - Context Relevance: Are retrieved chunks relevant to query?
    - Faithfulness: Does generated output match source chunks?
    - Answer Relevancy: Does output address the query?
    - Context Precision: Are the most relevant contexts ranked higher?
    - Context Recall: Are all relevant contexts retrieved?
    """

    def __init__(self):
        self.enabled = settings.enable_ragas and RAGAS_AVAILABLE
        self.results_dir = Path("./evaluation_results")
        self.results_dir.mkdir(exist_ok=True)

        if not self.enabled:
            logger.info("Ragas evaluation is disabled")

    def evaluate_retrieval(
        self,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Evaluate retrieval quality.

        Args:
            test_cases: List of test cases with format:
                {
                    'query': str,
                    'retrieved_contexts': List[str],
                    'ground_truth_contexts': List[str] (optional)
                }

        Returns:
            Evaluation results with metrics
        """
        if not self.enabled:
            return {"error": "Ragas not available"}

        try:
            # Prepare dataset for Ragas
            data = {
                'question': [],
                'contexts': [],
                'ground_truths': []
            }

            for case in test_cases:
                data['question'].append(case['query'])
                data['contexts'].append(case['retrieved_contexts'])

                # Ground truth is optional
                if 'ground_truth_contexts' in case:
                    data['ground_truths'].append(case['ground_truth_contexts'])
                else:
                    # Use retrieved contexts as proxy if no ground truth
                    data['ground_truths'].append(case['retrieved_contexts'])

            dataset = Dataset.from_dict(data)

            # Evaluate with relevancy metrics
            metrics = [context_relevancy, context_precision]

            logger.info(f"Evaluating {len(test_cases)} test cases with Ragas")
            result = evaluate(dataset, metrics=metrics)

            logger.info(f"Ragas evaluation complete: {result}")

            # Save results
            self._save_results({
                'type': 'retrieval',
                'metrics': result,
                'num_test_cases': len(test_cases),
                'timestamp': datetime.utcnow().isoformat()
            })

            return {
                'success': True,
                'metrics': result,
                'num_test_cases': len(test_cases)
            }

        except Exception as e:
            logger.error(f"Error in Ragas evaluation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def evaluate_generation(
        self,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Evaluate generation quality (faithfulness and relevancy).

        Args:
            test_cases: List of test cases with format:
                {
                    'query': str,
                    'retrieved_contexts': List[str],
                    'generated_answer': str,
                    'ground_truth_answer': str (optional)
                }

        Returns:
            Evaluation results with metrics
        """
        if not self.enabled:
            return {"error": "Ragas not available"}

        try:
            # Prepare dataset
            data = {
                'question': [],
                'contexts': [],
                'answer': [],
                'ground_truths': []
            }

            for case in test_cases:
                data['question'].append(case['query'])
                data['contexts'].append(case['retrieved_contexts'])
                data['answer'].append(case['generated_answer'])

                # Ground truth answer
                if 'ground_truth_answer' in case:
                    data['ground_truths'].append([case['ground_truth_answer']])
                else:
                    # If no ground truth, use the generated answer
                    data['ground_truths'].append([case['generated_answer']])

            dataset = Dataset.from_dict(data)

            # Evaluate with generation metrics
            metrics = [faithfulness, answer_relevancy]

            logger.info(f"Evaluating {len(test_cases)} generation test cases")
            result = evaluate(dataset, metrics=metrics)

            logger.info(f"Generation evaluation complete: {result}")

            # Save results
            self._save_results({
                'type': 'generation',
                'metrics': result,
                'num_test_cases': len(test_cases),
                'timestamp': datetime.utcnow().isoformat()
            })

            return {
                'success': True,
                'metrics': result,
                'num_test_cases': len(test_cases)
            }

        except Exception as e:
            logger.error(f"Error in generation evaluation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def evaluate_full_pipeline(
        self,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Evaluate complete RAG pipeline (retrieval + generation).

        Args:
            test_cases: List of test cases with complete pipeline data

        Returns:
            Comprehensive evaluation results
        """
        if not self.enabled:
            return {"error": "Ragas not available"}

        try:
            # Prepare dataset with all fields
            data = {
                'question': [],
                'contexts': [],
                'answer': [],
                'ground_truths': []
            }

            for case in test_cases:
                data['question'].append(case['query'])
                data['contexts'].append(case['retrieved_contexts'])
                data['answer'].append(case['generated_answer'])

                # Ground truth
                if 'ground_truth' in case:
                    data['ground_truths'].append([case['ground_truth']])
                else:
                    data['ground_truths'].append([case['generated_answer']])

            dataset = Dataset.from_dict(data)

            # Evaluate with all metrics
            metrics = [
                context_relevancy,
                context_precision,
                faithfulness,
                answer_relevancy
            ]

            logger.info(f"Evaluating full pipeline with {len(test_cases)} test cases")
            result = evaluate(dataset, metrics=metrics)

            logger.info(f"Full pipeline evaluation complete")

            # Save results
            self._save_results({
                'type': 'full_pipeline',
                'metrics': result,
                'num_test_cases': len(test_cases),
                'timestamp': datetime.utcnow().isoformat()
            })

            return {
                'success': True,
                'metrics': result,
                'num_test_cases': len(test_cases)
            }

        except Exception as e:
            logger.error(f"Error in full pipeline evaluation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_test_dataset(
        self,
        job_descriptions: List[str],
        resumes: List[str],
        num_samples: int = None
    ) -> List[Dict]:
        """
        Create a test dataset from job descriptions and resumes.

        Args:
            job_descriptions: List of job descriptions
            resumes: List of resume texts
            num_samples: Number of samples to create (None = all combinations)

        Returns:
            List of test cases
        """
        test_cases = []

        # Create combinations of job descriptions and resumes
        import itertools
        combinations = list(itertools.product(job_descriptions, resumes))

        if num_samples:
            import random
            combinations = random.sample(combinations, min(num_samples, len(combinations)))

        for jd, resume in combinations:
            test_cases.append({
                'query': jd,
                'document': resume,
                'timestamp': datetime.utcnow().isoformat()
            })

        return test_cases

    def _save_results(self, results: Dict):
        """Save evaluation results to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"ragas_eval_{results['type']}_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Results saved to {filename}")

    def load_results(self, evaluation_type: Optional[str] = None) -> List[Dict]:
        """
        Load previous evaluation results.

        Args:
            evaluation_type: Filter by type ('retrieval', 'generation', 'full_pipeline')

        Returns:
            List of evaluation results
        """
        results = []

        for file_path in self.results_dir.glob("ragas_eval_*.json"):
            if evaluation_type and evaluation_type not in file_path.name:
                continue

            with open(file_path, 'r') as f:
                results.append(json.load(f))

        return sorted(results, key=lambda x: x['timestamp'], reverse=True)

    def compare_results(
        self,
        result1: Dict,
        result2: Dict
    ) -> Dict:
        """
        Compare two evaluation results.

        Args:
            result1: First evaluation result
            result2: Second evaluation result

        Returns:
            Comparison statistics
        """
        comparison = {
            'improvement': {},
            'regression': {},
            'unchanged': {}
        }

        metrics1 = result1.get('metrics', {})
        metrics2 = result2.get('metrics', {})

        for metric_name in metrics1:
            if metric_name in metrics2:
                val1 = metrics1[metric_name]
                val2 = metrics2[metric_name]

                diff = val2 - val1
                pct_change = (diff / val1 * 100) if val1 != 0 else 0

                comparison_data = {
                    'before': val1,
                    'after': val2,
                    'absolute_change': diff,
                    'percent_change': pct_change
                }

                if diff > 0.01:  # Improvement threshold
                    comparison['improvement'][metric_name] = comparison_data
                elif diff < -0.01:  # Regression threshold
                    comparison['regression'][metric_name] = comparison_data
                else:
                    comparison['unchanged'][metric_name] = comparison_data

        return comparison


# Global evaluator instance
ragas_evaluator = RagasEvaluator()
