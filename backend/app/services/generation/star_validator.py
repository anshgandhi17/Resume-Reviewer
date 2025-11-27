"""
STAR Validator Service
Validates STAR-formatted bullets to detect hallucination and added content.

Validates:
1. No added metrics/numbers
2. No added technologies/tools
3. No fabricated results
4. No added action verbs not in original
"""

import logging
import re
from typing import Dict, List, Set
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class STARValidator:
    """
    Validates STAR-formatted bullets to detect hallucination.

    Strictness levels:
    - low: Only flag obvious fabrications (new numbers > 2x original)
    - medium: Flag added numbers and major technology changes
    - high: Flag ANY additions (numbers, technologies, results)
    """

    # Common metrics patterns
    NUMBER_PATTERN = r'\d+(?:[.,]\d+)?(?:\s*[%kKmMbB])?'
    PERCENTAGE_PATTERN = r'\d+(?:[.,]\d+)?\s*%'

    # Technology keywords (expandable)
    TECH_KEYWORDS = {
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust',
        'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring', 'express',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'terraform',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'git', 'github', 'gitlab', 'jira', 'confluence',
        'machine learning', 'ai', 'deep learning', 'nlp', 'computer vision'
    }

    # Result indicator words
    RESULT_INDICATORS = {
        'increased', 'decreased', 'reduced', 'improved', 'enhanced', 'optimized',
        'achieved', 'delivered', 'generated', 'saved', 'accelerated',
        'resulting in', 'led to', 'contributed to'
    }

    def __init__(self, strictness: str = "high"):
        """
        Initialize STAR Validator.

        Args:
            strictness: Validation strictness level (low, medium, high)
        """
        self.strictness = strictness
        logger.info(f"STAR Validator initialized with strictness: {strictness}")

    def validate_bullet(self, original: str, star_formatted: str) -> Dict:
        """
        Validate a STAR-formatted bullet against the original.

        Args:
            original: Original bullet point text
            star_formatted: STAR-formatted version

        Returns:
            Validation result with flags and warnings
        """
        validation_result = {
            'is_valid': True,
            'flags': [],
            'warnings': [],
            'severity': 'none',  # none, low, medium, high
            'added_content': {
                'numbers': [],
                'technologies': [],
                'results': [],
                'other': []
            }
        }

        # Extract and compare numbers
        numbers_check = self._check_numbers(original, star_formatted)
        if numbers_check['added']:
            validation_result['flags'].append("Added metrics/numbers not in original")
            validation_result['added_content']['numbers'] = numbers_check['added']
            validation_result['is_valid'] = False
            validation_result['severity'] = 'high'

        # Extract and compare technologies
        tech_check = self._check_technologies(original, star_formatted)
        if tech_check['added']:
            validation_result['flags'].append("Added technologies/tools not in original")
            validation_result['added_content']['technologies'] = tech_check['added']
            validation_result['is_valid'] = False
            if validation_result['severity'] != 'high':
                validation_result['severity'] = 'medium'

        # Check for fabricated results
        result_check = self._check_results(original, star_formatted)
        if result_check['fabricated']:
            validation_result['flags'].append("Added result statements not in original")
            validation_result['added_content']['results'] = result_check['fabricated']
            validation_result['is_valid'] = False
            validation_result['severity'] = 'high'

        # Check for action verb changes
        action_check = self._check_action_verbs(original, star_formatted)
        if action_check['added']:
            validation_result['warnings'].append("Added action verbs not in original")
            if self.strictness == 'high':
                validation_result['is_valid'] = False
                if not validation_result['severity'] or validation_result['severity'] == 'none':
                    validation_result['severity'] = 'low'

        # Overall similarity check
        similarity = self._calculate_similarity(original, star_formatted)
        if similarity < 0.5:  # Less than 50% similarity
            validation_result['warnings'].append(
                f"Low similarity to original ({similarity:.1%}). Possible over-rewriting."
            )

        logger.debug(
            f"Validation result: valid={validation_result['is_valid']}, "
            f"severity={validation_result['severity']}, "
            f"flags={len(validation_result['flags'])}"
        )

        return validation_result

    def _check_numbers(self, original: str, formatted: str) -> Dict:
        """
        Check for added numbers/metrics.

        Returns:
            Dictionary with 'original', 'formatted', and 'added' numbers
        """
        original_numbers = set(re.findall(self.NUMBER_PATTERN, original.lower()))
        formatted_numbers = set(re.findall(self.NUMBER_PATTERN, formatted.lower()))

        added = formatted_numbers - original_numbers

        # Filter based on strictness
        if self.strictness == 'low':
            # Only flag if new numbers are significantly larger (2x or more)
            original_values = [self._extract_numeric_value(n) for n in original_numbers]
            added = [
                n for n in added
                if self._extract_numeric_value(n) > max(original_values, default=0) * 2
            ]

        return {
            'original': list(original_numbers),
            'formatted': list(formatted_numbers),
            'added': list(added)
        }

    def _check_technologies(self, original: str, formatted: str) -> Dict:
        """
        Check for added technologies/tools.

        Returns:
            Dictionary with 'original', 'formatted', and 'added' technologies
        """
        original_lower = original.lower()
        formatted_lower = formatted.lower()

        original_techs = {tech for tech in self.TECH_KEYWORDS if tech in original_lower}
        formatted_techs = {tech for tech in self.TECH_KEYWORDS if tech in formatted_lower}

        added = formatted_techs - original_techs

        # Also check for capitalized tech terms (e.g., "React", "AWS")
        original_words = set(re.findall(r'\b[A-Z][a-zA-Z0-9+#\.]*\b', original))
        formatted_words = set(re.findall(r'\b[A-Z][a-zA-Z0-9+#\.]*\b', formatted))

        added_words = formatted_words - original_words
        # Filter to likely tech terms (2+ chars, contains specific patterns)
        added_words = {
            w for w in added_words
            if len(w) >= 2 and (w.isupper() or '+' in w or '#' in w or '.' in w)
        }

        return {
            'original': list(original_techs | original_words),
            'formatted': list(formatted_techs | formatted_words),
            'added': list(added | added_words)
        }

    def _check_results(self, original: str, formatted: str) -> Dict:
        """
        Check for fabricated result statements.

        Returns:
            Dictionary with original and fabricated result indicators
        """
        original_lower = original.lower()
        formatted_lower = formatted.lower()

        original_results = {
            indicator for indicator in self.RESULT_INDICATORS
            if indicator in original_lower
        }
        formatted_results = {
            indicator for indicator in self.RESULT_INDICATORS
            if indicator in formatted_lower
        }

        fabricated = formatted_results - original_results

        # Special check: If original has no numbers but formatted Result has numbers
        original_numbers = re.findall(self.NUMBER_PATTERN, original)
        result_section = self._extract_result_section(formatted)
        if result_section and result_section != "NOT PROVIDED":
            result_numbers = re.findall(self.NUMBER_PATTERN, result_section)
            if result_numbers and not original_numbers:
                fabricated.add("quantified_result_without_original_data")

        return {
            'original': list(original_results),
            'fabricated': list(fabricated)
        }

    def _check_action_verbs(self, original: str, formatted: str) -> Dict:
        """
        Check for added action verbs.

        Returns:
            Dictionary with original and added action verbs
        """
        # Common action verbs in resumes
        action_verbs = {
            'led', 'managed', 'developed', 'created', 'designed', 'implemented',
            'built', 'launched', 'delivered', 'optimized', 'improved', 'enhanced',
            'analyzed', 'researched', 'coordinated', 'collaborated', 'presented',
            'architected', 'engineered', 'programmed', 'deployed', 'maintained'
        }

        original_lower = original.lower()
        formatted_lower = formatted.lower()

        original_verbs = {verb for verb in action_verbs if verb in original_lower}
        formatted_verbs = {verb for verb in action_verbs if verb in formatted_lower}

        added = formatted_verbs - original_verbs

        return {
            'original': list(original_verbs),
            'formatted': list(formatted_verbs),
            'added': list(added)
        }

    def _extract_result_section(self, star_text: str) -> str:
        """
        Extract the Result section from STAR-formatted text.

        Args:
            star_text: Full STAR-formatted text

        Returns:
            Result section text
        """
        pattern = r'\*\*Result\*\*:\s*(.+?)(?=\*\*|$)'
        match = re.search(pattern, star_text, re.IGNORECASE | re.DOTALL)

        if match:
            return match.group(1).strip()
        else:
            return ""

    def _extract_numeric_value(self, number_str: str) -> float:
        """
        Extract numeric value from a number string (e.g., "50%", "10k", "2.5M").

        Args:
            number_str: Number string

        Returns:
            Numeric value as float
        """
        # Remove common suffixes and convert
        number_str = number_str.lower().replace('%', '').replace(',', '')

        multiplier = 1
        if 'k' in number_str:
            multiplier = 1000
            number_str = number_str.replace('k', '')
        elif 'm' in number_str:
            multiplier = 1000000
            number_str = number_str.replace('m', '')
        elif 'b' in number_str:
            multiplier = 1000000000
            number_str = number_str.replace('b', '')

        try:
            return float(number_str) * multiplier
        except ValueError:
            return 0

    def _calculate_similarity(self, original: str, formatted: str) -> float:
        """
        Calculate similarity between original and formatted text.

        Args:
            original: Original text
            formatted: Formatted text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        return SequenceMatcher(None, original.lower(), formatted.lower()).ratio()

    def validate_batch(
        self,
        formatted_bullets: List[Dict]
    ) -> Dict:
        """
        Validate a batch of formatted bullets.

        Args:
            formatted_bullets: List of formatted bullet dictionaries

        Returns:
            Batch validation result with summary statistics
        """
        results = []
        invalid_count = 0
        severity_counts = {'none': 0, 'low': 0, 'medium': 0, 'high': 0}

        for bullet in formatted_bullets:
            if 'original' not in bullet or 'star_formatted' not in bullet:
                continue

            validation = self.validate_bullet(
                original=bullet['original'],
                star_formatted=bullet['star_formatted']
            )

            # Add to bullet
            bullet['validation'] = validation

            results.append(bullet)

            if not validation['is_valid']:
                invalid_count += 1

            severity_counts[validation['severity']] += 1

        return {
            'total': len(results),
            'valid': len(results) - invalid_count,
            'invalid': invalid_count,
            'severity_counts': severity_counts,
            'results': results
        }
