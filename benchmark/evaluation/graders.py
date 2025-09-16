"""
Grading functions for benchmark evaluation.

Provides various grading strategies including exact match, substring matching,
numeric comparison, and LLM-based judging.
"""

import re
import logging
from typing import Optional, Callable, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def exact_match(
    response: str,
    ground_truth: str,
    case_sensitive: bool = False,
    strip_whitespace: bool = True
) -> bool:
    """
    Check if response exactly matches ground truth.
    
    Args:
        response: Model response
        ground_truth: Expected answer
        case_sensitive: Whether to perform case-sensitive comparison
        strip_whitespace: Whether to strip leading/trailing whitespace
    
    Returns:
        True if exact match, False otherwise
    """
    if response is None or ground_truth is None:
        return False
    
    resp = str(response)
    truth = str(ground_truth)
    
    if strip_whitespace:
        resp = resp.strip()
        truth = truth.strip()
    
    if not case_sensitive:
        resp = resp.lower()
        truth = truth.lower()
    
    return resp == truth


def substring_match(
    response: str,
    ground_truth: str,
    case_sensitive: bool = False,
    min_length: int = 3
) -> bool:
    """
    Check if ground truth appears as substring in response.
    
    Args:
        response: Model response
        ground_truth: Expected substring
        case_sensitive: Whether to perform case-sensitive comparison
        min_length: Minimum length for valid match
    
    Returns:
        True if substring found, False otherwise
    """
    if response is None or ground_truth is None:
        return False
    
    resp = str(response)
    truth = str(ground_truth)
    
    if len(truth) < min_length:
        logger.warning(f"Ground truth too short ({len(truth)} < {min_length})")
        return False
    
    if not case_sensitive:
        resp = resp.lower()
        truth = truth.lower()
    
    return truth in resp


def fuzzy_match(
    response: str,
    ground_truth: str,
    threshold: float = 0.8,
    case_sensitive: bool = False
) -> bool:
    """
    Check if response is similar to ground truth using fuzzy matching.
    
    Args:
        response: Model response
        ground_truth: Expected answer
        threshold: Similarity threshold (0.0 to 1.0)
        case_sensitive: Whether to perform case-sensitive comparison
    
    Returns:
        True if similarity above threshold, False otherwise
    """
    if response is None or ground_truth is None:
        return False
    
    resp = str(response)
    truth = str(ground_truth)
    
    if not case_sensitive:
        resp = resp.lower()
        truth = truth.lower()
    
    similarity = SequenceMatcher(None, resp, truth).ratio()
    return similarity >= threshold


def numeric_match(
    response: str,
    ground_truth: float,
    tolerance: float = 1e-6,
    extract_first: bool = True
) -> bool:
    """
    Check if response contains numeric value matching ground truth.
    
    Args:
        response: Model response
        ground_truth: Expected numeric value
        tolerance: Acceptable difference for floating point comparison
        extract_first: Extract first number from response if True
    
    Returns:
        True if numeric match within tolerance, False otherwise
    """
    if response is None or ground_truth is None:
        return False
    
    try:
        if extract_first:
            numbers = re.findall(r'-?\d+\.?\d*', str(response))
            if not numbers:
                return False
            response_value = float(numbers[0])
        else:
            response_value = float(response)
        
        truth_value = float(ground_truth)
        return abs(response_value - truth_value) <= tolerance
    
    except (ValueError, TypeError) as e:
        logger.debug(f"Numeric match failed: {e}")
        return False


def regex_match(
    response: str,
    pattern: str,
    flags: int = 0
) -> bool:
    """
    Check if response matches regular expression pattern.
    
    Args:
        response: Model response
        pattern: Regular expression pattern
        flags: Regex flags (e.g., re.IGNORECASE)
    
    Returns:
        True if pattern matches, False otherwise
    """
    if response is None or pattern is None:
        return False
    
    try:
        return bool(re.search(pattern, str(response), flags))
    except re.error as e:
        logger.error(f"Invalid regex pattern '{pattern}': {e}")
        return False


def json_match(
    response: str,
    expected_schema: dict[str, Any],
    strict: bool = True
) -> bool:
    """
    Check if response is valid JSON matching expected schema.
    
    Args:
        response: Model response
        expected_schema: Expected JSON structure
        strict: Whether to require exact match or subset match
    
    Returns:
        True if JSON valid and matches schema, False otherwise
    """
    import json
    
    if response is None or expected_schema is None:
        return False
    
    try:
        parsed = json.loads(str(response))
        
        if strict:
            return parsed == expected_schema
        else:
            return all(
                key in parsed and parsed[key] == value
                for key, value in expected_schema.items()
            )
    
    except (json.JSONDecodeError, TypeError) as e:
        logger.debug(f"JSON match failed: {e}")
        return False


async def llm_judge(
    response: str,
    ground_truth: str,
    task_description: str,
    llm_provider: Any,
    criteria: Optional[str] = None,
    max_tokens: int = 4000
) -> tuple[bool, float, str]:
    """
    Use LLM to judge response quality.
    
    Args:
        response: Model response to evaluate
        ground_truth: Expected answer or reference
        task_description: Description of the task
        llm_provider: LLM provider for judging
        criteria: Optional specific grading criteria
        max_tokens: Maximum tokens for judge response
    
    Returns:
        Tuple of (passed, score, reasoning)
    """
    if criteria is None:
        criteria = "Correctness, completeness, and accuracy"
    
    system_prompt = """You are an expert evaluator for benchmark tasks. 
Evaluate the response based on the provided criteria and ground truth.

Respond in JSON format:
{
    "score": <float between 0.0 and 1.0>,
    "passed": <boolean>,
    "reasoning": "<detailed explanation>"
}"""
    
    user_prompt = f"""Task: {task_description}

Ground Truth: {ground_truth}

Response to Evaluate:
{response}

Criteria: {criteria}

Evaluate the response and provide your judgment."""
    
    try:
        judge_response = await llm_provider.get_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=0.0
        )
        
        result = llm_provider.clean_and_parse_json(judge_response)
        
        score = float(result.get("score", 0.0))
        passed = bool(result.get("passed", False))
        reasoning = str(result.get("reasoning", "No reasoning provided"))
        
        score = max(0.0, min(1.0, score))
        
        return passed, score, reasoning
    
    except Exception as e:
        logger.error(f"LLM judge failed: {e}")
        return False, 0.0, f"Evaluation failed: {str(e)}"


def create_custom_grader(
    grading_function: Callable[[str, Any], bool],
    score_on_pass: float = 1.0,
    score_on_fail: float = 0.0
) -> Callable[[str, Any], tuple[bool, float]]:
    """
    Create custom grader from boolean function.
    
    Args:
        grading_function: Function that returns True/False for pass/fail
        score_on_pass: Score to assign on pass
        score_on_fail: Score to assign on fail
    
    Returns:
        Grader function that returns (passed, score)
    """
    def grader(response: str, ground_truth: Any) -> tuple[bool, float]:
        passed = grading_function(response, ground_truth)
        score = score_on_pass if passed else score_on_fail
        return passed, score
    
    return grader
