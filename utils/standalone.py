#!/usr/bin/env python3
"""
Standalone benchmarking CLI using only Python standard library.

A minimal benchmarking tool that queries LLMs via Pollinations AI API
and evaluates responses against ground truth. No external dependencies.
Supports inline task definition with JSON-structured responses.
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
import socket
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


API_BASE_URL = "https://text.pollinations.ai"
MODELS_ENDPOINT = API_BASE_URL + "/models"

DEFAULT_HEADERS = {
    "User-Agent": "benchmarks-standalone/1.0",
    "Accept": "application/json",
}

DEFAULT_WAIT_TIME = 6
DEFAULT_TIMEOUT = 180
DEFAULT_TEMPERATURE = 1
DEFAULT_OUTPUT_FILE = "standalone_results.json"
DEFAULT_EVALUATION = "substr"

# Default embedded tasks JSON (standalone uses JSON files/strings, not JSONL)
DEFAULT_TASKS_JSON = r'''
[
    {
        "id": "default_task",
        "questions": [
            {
                "id": "q1",
                "text": "Example 1 input: [[0,0,0],[0,1,0],[0,0,0]] Example 1 output: [[0,1,0],[0,1,0],[0,1,0]] Example 2 input: [[2,0,0],[0,0,0],[0,0,0]] Example 2 output: [[2,0,0],[2,0,0],[2,0,0]] Input: [[0,0,3],[0,0,0],[0,0,0]] What is the expected output as a single string in one line no spaces?",
                "ground_truth": "[0,0,3],[0,0,3],[0,0,3]",
                "eval_type": "substr",
                "strip_spaces": true,
                "strip_newlines": true
            },
            {
                "id": "q2",
                "text": "Example 1 input: [[0,0,1],[0,1,0],[0,0,0]] Example 1 output: [[2,0,0],[2,0,0],[2,2,2]] Example 2 input: [[2,0,0],[0,2,0],[0,0,0]] Example 2 output: [[0,0,3],[0,0,3],[3,3,3]] Input: [[0,0,3],[0,0,0],[0,0,0]] What is the expected output as a single string in one line no spaces?",
                "ground_truth": "[6,6,6],[6,0,0],[6,0,0]",
                "eval_type": "substr",
                "strip_spaces": true,
                "strip_newlines": true
            }
        ],
        "metadata": {
            "category": "computer_science"
        }
    }
]
'''

DEFAULT_MODEL_NAMES = [
    "OpenAI GPT-5 Nano",
    "OpenAI GPT-4.1 Nano",
]


# ANSI Color Codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with ANSI colors."""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_BLACK,
        logging.INFO: Colors.BRIGHT_CYAN,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if record.levelno in self.LEVEL_COLORS:
            levelname_color = f"{self.LEVEL_COLORS[record.levelno]}{levelname}{Colors.RESET}"
            record.levelname = levelname_color
        
        # Add timestamp color
        timestamp = self.formatTime(record, self.datefmt)
        colored_timestamp = f"{Colors.DIM}{timestamp}{Colors.RESET}"
        
        # Format the message
        result = super().format(record)
        
        # Reset levelname for future use
        record.levelname = levelname
        
        return result


def setup_logger(name: str = "standalone", verbose: bool = False) -> logging.Logger:
    """Set up colored logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Colored formatter
    formatter = ColoredFormatter(
        fmt=f"{Colors.DIM}[%(asctime)s]{Colors.RESET} %(levelname)s {Colors.DIM}%(name)s:{Colors.RESET} %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


# Global logger instance
logger = setup_logger()


@dataclass
class ModelInfo:
    """Available model information."""
    pollinations_model_id: str
    model_name: str
    description: str
    reasoning: bool = False
    tier: str = "anonymous"
    tools: bool = False
    vision: bool = False
    audio: bool = False
    aliases: list[str] = field(default_factory=list)


@dataclass
class Question:
    """Single question within a task."""
    id: str
    text: str
    ground_truth: Optional[Any] = None
    eval_type: str = "substr"
    strip_spaces: bool = False
    strip_newlines: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Benchmark task definition with multiple questions."""
    id: str
    questions: list[Question]
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def combined_prompt(self) -> str:
        """Generate combined prompt for all questions."""
        if len(self.questions) == 1:
            return self.questions[0].text
        
        prompt_parts = ["Please answer the following questions:"]
        for i, q in enumerate(self.questions, 1):
            prompt_parts.append(f"\n{i}. {q.text}")
        
        return "\n".join(prompt_parts)


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    model_name: str
    response: str
    raw_response: str
    parsed_json: Optional[dict[str, Any]]
    execution_time: float
    success: bool = True
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestionGrade:
    """Grade for a single question."""
    question_id: str
    score: float
    passed: bool
    reasoning: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Grade:
    """Evaluation grade for all questions in a task."""
    overall_score: float
    overall_passed: bool
    question_grades: list[QuestionGrade]
    reasoning: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""
    model_name: str
    task_id: str
    result: TaskResult
    grade: Grade
    timestamp: str


class PollinationsClient:
    """Client for Pollinations AI API using only standard library."""
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = API_BASE_URL
    
    def _open(self, request: urllib.request.Request):
        try:
            return urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", None)
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise TimeoutError(f"Pollinations request exceeded timeout ({self.timeout}s)") from error
            raise
        except socket.timeout as error:
            raise TimeoutError(f"Pollinations request exceeded timeout ({self.timeout}s)") from error

    def fetch_models(self) -> list[ModelInfo]:
        """Fetch available models from API."""
        try:
            req = urllib.request.Request(MODELS_ENDPOINT, headers=DEFAULT_HEADERS)
            with self._open(req) as response:
                data = json.loads(response.read().decode())
                model_items = []
                if isinstance(data, list):
                    model_items = data
                elif isinstance(data, dict) and "models" in data and isinstance(data["models"], list):
                    model_items = data["models"]
                else:
                    logger.warning("Models endpoint returned unexpected payload (not a list nor {'models': [...]})")
                    return []
                sanitized_models: list[ModelInfo] = []
                for idx, item in enumerate(model_items):
                    if not isinstance(item, dict):
                        logger.debug(f"Skipping non-dict model entry at index {idx}")
                        continue

                    pollinations_id = item.get("name")
                    if not pollinations_id:
                        logger.debug(f"Skipping model entry without name at index {idx}")
                        continue

                    description = item.get("description") or ""
                    friendly_name = description or pollinations_id
                    aliases_value = item.get("aliases")
                    if not isinstance(aliases_value, list):
                        aliases_value = []

                    sanitized = {
                        "pollinations_model_id": pollinations_id,
                        "model_name": friendly_name,
                        "description": description,
                        "reasoning": bool(item.get("reasoning", False)),
                        "tier": item.get("tier", "anonymous") or "anonymous",
                        "tools": bool(item.get("tools", False)),
                        "vision": bool(item.get("vision", False)),
                        "audio": bool(item.get("audio", False)),
                        "aliases": aliases_value,
                    }

                    try:
                        sanitized_models.append(ModelInfo(**sanitized))
                    except Exception as ex:
                        logger.warning(f"Failed to create ModelInfo for entry index {idx}: {ex}")

                return sanitized_models
        except urllib.error.HTTPError as e:
            # Provide clearer info on 403s and other HTTP errors
            try:
                body = e.read().decode() if e.fp else "No error details"
            except Exception:
                body = "No error details"
            logger.error(f"Error fetching models: HTTP {e.code}: {body}")
            return []
        except TimeoutError as e:
            logger.error(str(e))
            return []
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []

    def generate_text(
        self,
        prompt: str,
        model: str = "openai",
        temperature: float = DEFAULT_TEMPERATURE,
        system: Optional[str] = None,
        json_mode: bool = True
    ) -> tuple[str, Optional[dict[str, Any]]]:
        """
        Generate text response from model.
        
        Args:
            prompt: Input prompt
            model: Model name
            temperature: Sampling temperature
            system: System message
            json_mode: Request JSON formatted output
        
        Returns:
            Tuple of (raw_response, parsed_json_dict)
        """
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"{self.base_url}/{encoded_prompt}"
        params = {
            "model": model,
            "temperature": str(temperature)
        }
        if json_mode:
            params["json"] = "true"
        if system:
            params["system"] = system
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        try:
            req = urllib.request.Request(full_url, headers=DEFAULT_HEADERS)
            with self._open(req) as response:
                raw_response = response.read().decode().strip()
                if json_mode:
                    try:
                        parsed = json.loads(raw_response)
                        return raw_response, parsed
                    except json.JSONDecodeError:
                        return raw_response, None
                return raw_response, None
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode() if e.fp else "No error details"
            except Exception:
                error_body = "No error details"
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"URL error: {e.reason}")
        except TimeoutError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Request failed: {e}")


class Evaluator:
    """Evaluates task results against ground truth."""
    
    @staticmethod
    def normalize_answer(value: str, question: Question) -> str:
        cleaned = value.strip()
        if question.strip_spaces:
            cleaned = cleaned.replace(" ", "")
        if question.strip_newlines:
            cleaned = cleaned.replace("\n", "")
        return cleaned.lower()

    @staticmethod
    def extract_answer(result: TaskResult, question: Question, question_index: int) -> Optional[str]:
        """
        Extract answer for a specific question from result.
        
        Tries JSON parsing first, then falls back to raw response.
        """
        label = str(question_index + 1)
        parsed = result.parsed_json
        if parsed:
            if isinstance(parsed, dict):
                direct_candidates = [
                    label,
                    question.id,
                    f"q{label}",
                    f"question_{label}",
                    f"question_{question.id}",
                    "answer",
                    "response",
                    "result"
                ]
                for candidate in direct_candidates:
                    if candidate in parsed:
                        value = parsed[candidate]
                        if isinstance(value, (str, int, float, bool)):
                            return str(value).strip()
                        if isinstance(value, dict) and "answer" in value and isinstance(value["answer"], (str, int, float, bool)):
                            return str(value["answer"]).strip()
                if "answers" in parsed:
                    answers = parsed["answers"]
                    if isinstance(answers, list) and 0 <= question_index < len(answers):
                        return str(answers[question_index]).strip()
                    if isinstance(answers, dict):
                        if label in answers and isinstance(answers[label], (str, int, float, bool)):
                            return str(answers[label]).strip()
                        if question.id in answers and isinstance(answers[question.id], (str, int, float, bool)):
                            return str(answers[question.id]).strip()
            elif isinstance(parsed, list) and 0 <= question_index < len(parsed):
                return str(parsed[question_index]).strip()
        return result.response.strip() if result.response else None

    @staticmethod
    def evaluate_question(
        result: TaskResult,
        question: Question,
        question_index: int
    ) -> QuestionGrade:
        """Evaluate a single question within a task."""
        actual = Evaluator.extract_answer(result, question, question_index)
        if question.ground_truth is None:
            return QuestionGrade(
                question_id=question.id,
                score=1.0,
                passed=True,
                reasoning="No ground truth provided (display only)",
                expected=None,
                actual=actual,
                metadata={"eval_type": "none"}
            )
        if actual is None:
            return QuestionGrade(
                question_id=question.id,
                score=0.0,
                passed=False,
                reasoning="No answer extracted from response",
                expected=str(question.ground_truth),
                actual=None,
                metadata={"eval_type": question.eval_type}
            )
        normalized_actual = Evaluator.normalize_answer(actual, question)
        normalized_expected = Evaluator.normalize_answer(str(question.ground_truth), question)
        if question.eval_type == "exact":
            passed = normalized_actual == normalized_expected
            score = 1.0 if passed else 0.0
            reasoning = "Exact match" if passed else "Mismatch"
        else:
            passed = normalized_expected in normalized_actual
            score = 1.0 if passed else 0.0
            reasoning = f"Contains '{question.ground_truth}'" if passed else f"Does not contain '{question.ground_truth}'"
        return QuestionGrade(
            question_id=question.id,
            score=score,
            passed=passed,
            reasoning=reasoning,
            expected=str(question.ground_truth),
            actual=actual,
            metadata={"eval_type": question.eval_type}
        )

    @staticmethod
    def evaluate_task(result: TaskResult, task: Task) -> Grade:
        """Evaluate all questions in a task."""
        question_grades = []
        for index, question in enumerate(task.questions):
            grade = Evaluator.evaluate_question(result, question, index)
            question_grades.append(grade)
        if not question_grades:
            return Grade(
                overall_score=0.0,
                overall_passed=False,
                question_grades=[],
                reasoning="No questions to evaluate",
                metadata={}
            )
        total_score = sum(g.score for g in question_grades)
        overall_score = total_score / len(question_grades)
        overall_passed = all(g.passed for g in question_grades)
        passed_count = sum(1 for g in question_grades if g.passed)
        reasoning = f"{passed_count}/{len(question_grades)} questions passed"
        return Grade(
            overall_score=overall_score,
            overall_passed=overall_passed,
            question_grades=question_grades,
            reasoning=reasoning,
            metadata={"total_questions": len(question_grades)}
        )


class StandaloneBenchmark:
    """Standalone benchmark runner."""
    
    def __init__(
        self,
        client: PollinationsClient,
        wait_time: float = DEFAULT_WAIT_TIME,
        temperature: float = DEFAULT_TEMPERATURE,
        system_message: Optional[str] = None,
        verbose: bool = False
    ):
        self.client = client
        self.wait_time = wait_time
        self.temperature = temperature
        self.system_message = system_message
        self.verbose = verbose
    
    def execute_task(self, task: Task, model_id: str, model_name: str) -> TaskResult:
        """Execute single task on model."""
        logger.debug(f"Executing task {task.id} on {model_name}")
        start_time = time.time()
        json_mode = True
        try:
            prompt = task.combined_prompt
            instruction = '\n\nRespond with a JSON object where each key is the stringified question number ("1", "2", ...) and each value is your answer.'
            prompt += instruction
            raw_response, parsed_json = self.client.generate_text(
                prompt=prompt,
                model=model_id,
                temperature=self.temperature,
                system=self.system_message,
                json_mode=json_mode
            )
            execution_time = time.time() - start_time
            display_response = raw_response
            if parsed_json:
                try:
                    display_response = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                except Exception:
                    display_response = raw_response
            return TaskResult(
                task_id=task.id,
                model_name=model_name,
                response=display_response,
                raw_response=raw_response,
                parsed_json=parsed_json,
                execution_time=execution_time,
                success=True,
                metadata={
                    "temperature": self.temperature,
                    "json_mode": json_mode,
                    "model_id": model_id
                }
            )
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Task {task.id} failed: {error_msg}")
            return TaskResult(
                task_id=task.id,
                model_name=model_name,
                response="",
                raw_response="",
                parsed_json=None,
                execution_time=execution_time,
                success=False,
                error=error_msg,
                metadata={
                    "temperature": self.temperature,
                    "json_mode": json_mode,
                    "model_id": model_id
                }
            )
    
    def run_benchmark(
        self,
        tasks: list[Task],
        models: list[tuple[str, str]]
    ) -> list[BenchmarkResult]:
        """Run benchmark across all tasks and models."""
        results = []
        total = len(tasks) * len(models)
        current = 0
        logger.info(f"Starting benchmark: {len(tasks)} tasks × {len(models)} models = {total} total executions")
        for model_index, (model_name, model_id) in enumerate(models):
            logger.info(f"Testing model: {model_name}")
            for task_index, task in enumerate(tasks):
                current += 1
                logger.info(f"Progress: {current}/{total} - Model: {model_name}, Task: {task.id}")
                try:
                    result = self.execute_task(task, model_id, model_name)
                    if result.success:
                        grade = Evaluator.evaluate_task(result, task)
                    else:
                        grade = Grade(
                            overall_score=0.0,
                            overall_passed=False,
                            question_grades=[],
                            reasoning=f"Execution failed: {result.error}",
                            metadata={"error": True}
                        )
                except Exception as e:
                    logger.exception(f"Unexpected error running task {task.id} on {model_name}: {e}")
                    execution_time = 0.0
                    result = TaskResult(
                        task_id=task.id,
                        model_name=model_name,
                        response="",
                        raw_response="",
                        parsed_json=None,
                        execution_time=execution_time,
                        success=False,
                        error=str(e),
                        metadata={
                            "temperature": self.temperature,
                            "json_mode": True,
                            "model_id": model_id
                        }
                    )
                    grade = Grade(
                        overall_score=0.0,
                        overall_passed=False,
                        question_grades=[],
                        reasoning=f"Unexpected error: {e}",
                        metadata={"error": True}
                    )
                benchmark_result = BenchmarkResult(
                    model_name=model_name,
                    task_id=task.id,
                    result=result,
                    grade=grade,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                results.append(benchmark_result)
                if task_index < len(tasks) - 1 or model_index < len(models) - 1:
                    logger.debug(f"Waiting {self.wait_time}s before next request")
                    time.sleep(self.wait_time)
            logger.info(f"Completed model: {model_name}")
        return results


def create_inline_task(
    questions: list[str],
    answers: Optional[list[str]] = None,
    eval_type: str = "substr"
) -> Task:
    """
    Create a task from inline questions and optional answers.
    
    Args:
        questions: List of question strings
        answers: Optional list of ground truth answers
        eval_type: Evaluation type ('substr' or 'exact')
    
    Returns:
        Task with Question objects
    """
    question_objs = []
    
    for i, q_text in enumerate(questions):
        q_id = f"q{i+1}"
        ground_truth = None
        
        if answers and i < len(answers) and answers[i]:
            ground_truth = answers[i]
        
        question_objs.append(Question(
            id=q_id,
            text=q_text,
            ground_truth=ground_truth,
            eval_type=eval_type
        ))
    
    return Task(
        id="inline_task",
        questions=question_objs,
        metadata={"source": "inline"}
    )


def load_tasks_from_json(file_path: str) -> list[Task]:
    """Load tasks from a JSON file (standalone accepts JSON, not JSONL).

    The file must contain a JSON array of task objects or a single task object.
    Legacy single-line JSONL files will still be handled as a fallback but are
    not the recommended format for this standalone utility.
    """
    tasks = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            if not content:
                logger.warning(f"Empty file {file_path}")
                return []
            
            try:
                data = json.loads(content)
                
                if isinstance(data, list):
                    for item in data:
                        task = parse_task_dict(item)
                        if task:
                            tasks.append(task)
                elif isinstance(data, dict):
                    task = parse_task_dict(data)
                    if task:
                        tasks.append(task)
            
            except json.JSONDecodeError:
                for line_num, line in enumerate(content.split('\n'), 1):
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            task = parse_task_dict(item)
                            if task:
                                tasks.append(task)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
    
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading tasks: {e}")
        sys.exit(1)
    
    return tasks


def parse_task_dict(data: dict) -> Optional[Task]:
    """Parse task dictionary into Task object."""
    try:
        if "questions" in data:
            questions = []
            for q_data in data["questions"]:
                if isinstance(q_data, dict):
                    questions.append(Question(**q_data))
                elif isinstance(q_data, str):
                    questions.append(Question(
                        id=f"q{len(questions)+1}",
                        text=q_data,
                        ground_truth=None
                    ))
            
            return Task(
                id=data.get("id", f"task_{len(questions)}q"),
                questions=questions,
                metadata=data.get("metadata", {})
            )
        
        elif "prompt" in data:
            question = Question(
                id="q1",
                text=data["prompt"],
                ground_truth=data.get("ground_truth"),
                eval_type=data.get("eval_type", "substr")
            )
            
            return Task(
                id=data.get("id", "legacy_task"),
                questions=[question],
                metadata=data.get("metadata", {})
            )
        
        else:
            logger.warning(f"Unrecognized task format: {data}")
            return None
    
    except Exception as e:
        logger.warning(f"Failed to parse task: {e}")
        return None


def save_results(results: list[BenchmarkResult], output_file: str) -> None:
    """Save benchmark results to JSON file."""
    try:
        output_data = {
             "timestamp": datetime.now(timezone.utc).isoformat(),
              "total_executions": len(results),
             "results": [
                 {
                     "model": r.model_name,
                     "task_id": r.task_id,
                     "success": r.result.success,
                     "response": r.result.response,
                     "parsed_json": r.result.parsed_json,
                     "execution_time": r.result.execution_time,
                     "error": r.result.error,
                     "grade": {
                         "overall_score": r.grade.overall_score,
                         "overall_passed": r.grade.overall_passed,
                         "reasoning": r.grade.reasoning,
                         "question_grades": [
                             {
                                 "question_id": qg.question_id,
                                 "score": qg.score,
                                 "passed": qg.passed,
                                 "reasoning": qg.reasoning,
                                 "expected": qg.expected,
                                 "actual": qg.actual,
                                 "metadata": qg.metadata
                             }
                             for qg in r.grade.question_grades
                         ],
                         "metadata": r.grade.metadata
                     },
                     "timestamp": r.timestamp
                 }
                 for r in results
             ]
         }
    except Exception as e:
        logger.exception(f"Failed to prepare results payload: {e}")
        return

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.exception(f"Failed to write results to {output_file}: {e}")
        return

    logger.info(f"Results saved to: {output_file}")


def generate_summary(results: list[BenchmarkResult]) -> dict[str, Any]:
    """Generate summary statistics from results."""
    if not results:
        return {}
    
    by_model = {}
    
    for result in results:
        if result.model_name not in by_model:
            by_model[result.model_name] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "total_score": 0.0,
                "total_time": 0.0,
                "total_questions": 0,
                "questions_passed": 0
            }
        
        stats = by_model[result.model_name]
        stats["total"] += 1
        stats["total_score"] += result.grade.overall_score
        stats["total_time"] += result.result.execution_time
        
        if not result.result.success:
            stats["errors"] += 1
        elif result.grade.overall_passed:
            stats["passed"] += 1
        else:
            stats["failed"] += 1
        
        stats["total_questions"] += len(result.grade.question_grades)
        stats["questions_passed"] += sum(1 for qg in result.grade.question_grades if qg.passed)
    
    summary = {}
    for model, stats in by_model.items():
        summary[model] = {
            "total_tasks": stats["total"],
            "passed": stats["passed"],
            "failed": stats["failed"],
            "errors": stats["errors"],
            "pass_rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0,
            "average_score": stats["total_score"] / stats["total"] if stats["total"] > 0 else 0.0,
            "total_time": stats["total_time"],
            "average_time": stats["total_time"] / stats["total"] if stats["total"] > 0 else 0.0,
            "total_questions": stats["total_questions"],
            "questions_passed": stats["questions_passed"],
            "question_pass_rate": stats["questions_passed"] / stats["total_questions"] if stats["total_questions"] > 0 else 0.0
        }
    
    return summary


def print_summary(summary: dict[str, Any], results: list[BenchmarkResult], display_mode: bool = False) -> None:
    """Print formatted summary to console."""
    if display_mode:
        print("\n" + "=" * 80)
        print("MODEL RESPONSES")
        print("=" * 80)
        
        for result in results:
            print(f"\n{'─' * 80}")
            print(f"Model: {result.model_name}")
            print(f"Task:  {result.task_id}")
            print(f"Time:  {result.result.execution_time:.2f}s")
            print(f"{'─' * 80}")
            
            if result.result.success:
                if result.result.parsed_json:
                    print("\nParsed JSON Response:")
                    print(json.dumps(result.result.parsed_json, indent=2, ensure_ascii=False))
                else:
                    print("\nResponse:")
                    print(result.result.response)
                
                if result.grade.question_grades:
                    print("\nExtracted Answers:")
                    for qg in result.grade.question_grades:
                        print(f"  {qg.question_id}: {qg.actual if qg.actual else '(no answer extracted)'}")
            else:
                print(f"\nError: {result.result.error}")
        
        print("\n" + "=" * 80)
        return
    
    if not summary:
        print("\nNo results to summarize.")
        return
    
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    
    for model, stats in summary.items():
        print(f"\nModel: {model}")
        print(f"  Total Tasks:       {stats['total_tasks']}")
        print(f"  Passed:            {stats['passed']} ({stats['pass_rate']*100:.1f}%)")
        print(f"  Failed:            {stats['failed']}")
        print(f"  Errors:            {stats['errors']}")
        print(f"  Average Score:     {stats['average_score']:.3f}")
        print(f"  Total Questions:   {stats['total_questions']}")
        print(f"  Questions Passed:  {stats['questions_passed']} ({stats['question_pass_rate']*100:.1f}%)")
        print(f"  Total Time:        {stats['total_time']:.2f}s")
        print(f"  Average Time:      {stats['average_time']:.2f}s per task")
    
    print("\n" + "=" * 80)


def resolve_model_targets(requested: list[str], catalog: list[ModelInfo]) -> list[tuple[str, str]]:
    """Resolve requested display labels into Pollinations model identifiers."""
    trimmed = [entry.strip() for entry in requested if entry and entry.strip()]
    if not trimmed or not catalog:
        return []

    by_id = {model.pollinations_model_id.casefold(): model for model in catalog}
    by_name = {model.model_name.casefold(): model for model in catalog}
    alias_lookup: dict[str, ModelInfo] = {}
    for model in catalog:
        for alias in model.aliases:
            alias_lookup[alias.casefold()] = model

    resolved: list[tuple[str, str]] = []
    seen: set[str] = set()

    for entry in trimmed:
        key = entry.casefold()
        model_info = by_name.get(key) or by_id.get(key) or alias_lookup.get(key)
        if not model_info:
            logger.warning(f"Unrecognized model: {entry}")
            continue

        identifier = model_info.pollinations_model_id
        if identifier in seen:
            continue

        resolved.append((model_info.model_name, identifier))
        seen.add(identifier)

    return resolved


def list_models(client: PollinationsClient, reasoning_only: bool, show_all: bool) -> None:
    """List available models."""
    logger.info("Fetching available models...")
    models = client.fetch_models()
    
    if not models:
        logger.warning("No models available.")
        return
    
    reasoning_models = [m for m in models if m.reasoning]
    non_reasoning_models = [m for m in models if not m.reasoning]

    def render_model(model: ModelInfo) -> None:
        details = [f"id={model.pollinations_model_id}"]
        if model.description and model.description != model.model_name:
            details.append(model.description)
        suffix = f" - {' | '.join(details)}" if details else ""
        print(f"  • {model.model_name}{suffix}")
        if show_all and model.aliases:
            print(f"    Aliases: {', '.join(model.aliases)}")
    
    if reasoning_only:
        models_to_show = reasoning_models
        print(f"\n=== Reasoning Models ({len(reasoning_models)}) ===\n")
    else:
        models_to_show = reasoning_models + non_reasoning_models
        print(f"\n=== Available Models ({len(models)}) ===\n")
    
    if reasoning_models and not reasoning_only:
        print("Reasoning Models:")
        for model in reasoning_models:
            render_model(model)
        print()
    
    if non_reasoning_models and not reasoning_only:
        print("Standard Models:")
        for model in non_reasoning_models:
            render_model(model)
    
    if reasoning_only:
        for model in reasoning_models:
            render_model(model)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Standalone LLM benchmark tool using Pollinations AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available models
  python standalone.py --list-models
  
  # Single question, display only (no evaluation)
  python standalone.py -q "What is 2+2?" -m openai mistral
  
  # Single question with answer validation (substr match by default)
  python standalone.py -q "What is the capital of France?" -a "Paris" -m openai
  
  # Multiple questions with answers (exact match)
  python standalone.py -q "2+2?" "3*3?" -a "4" "9" --eval-type exact -m deepseek
  
  # Load from file
  python standalone.py tasks.json -m openai mistral
        """
    )
    
    parser.add_argument(
        "tasks_file",
        nargs="?",
        help="Path to tasks JSON file (standalone expects JSON array/object; not JSONL)"
    )
    
    parser.add_argument(
        "-q", "--question",
        nargs="+",
        help="Inline question(s) to ask models"
    )
    
    parser.add_argument(
        "-a", "--answer",
        nargs="+",
        help="Expected answer(s) for validation (optional, same order as questions)"
    )
    
    parser.add_argument(
        "--eval-type",
        choices=["substr", "exact"],
        default=DEFAULT_EVALUATION,
        help=f"Evaluation type for inline questions (default: {DEFAULT_EVALUATION})"
    )
    
    parser.add_argument(
        "-m", "--models",
        nargs="+",
        default=None,
        help="Models to test (defaults to curated set)"
    )
    
    parser.add_argument(
        "-w", "--wait",
        type=float,
        default=DEFAULT_WAIT_TIME,
        help=f"Wait time between requests in seconds (default: {DEFAULT_WAIT_TIME})"
    )
    
    parser.add_argument(
        "-t", "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE})"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )
    
    parser.add_argument(
        "-s", "--system",
        help="System message for model"
    )
    
    parser.add_argument(
        "-o", "--output",
        help=f"Output file for results (default: {DEFAULT_OUTPUT_FILE} or none for display mode)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit"
    )
    
    parser.add_argument(
        "--reasoning-only",
        action="store_true",
        help="List only reasoning models"
    )
    
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all model details including aliases"
    )
    
    args = parser.parse_args()
    
    # Reconfigure logger with verbose setting
    global logger
    logger = setup_logger(verbose=args.verbose)
    
    client = PollinationsClient(timeout=args.timeout)
    
    if args.list_models:
        list_models(client, args.reasoning_only, args.show_all)
        return
    
    # If neither tasks_file nor inline questions are provided, use embedded default JSON
    if args.tasks_file and args.question:
        parser.error("Cannot specify both tasks_file and --question")

    tasks = []

    if args.question:
        tasks = [create_inline_task(args.question, args.answer, args.eval_type)]
        logger.info(f"Created inline task with {len(args.question)} question(s)")
    else:
        if not args.tasks_file:
            # Use embedded default tasks
            logger.info("No tasks file or inline questions provided — using embedded default tasks JSON")
            try:
                data = json.loads(DEFAULT_TASKS_JSON)
                if isinstance(data, list):
                    for item in data:
                        task_obj = parse_task_dict(item)
                        if task_obj:
                            tasks.append(task_obj)
                elif isinstance(data, dict):
                    task_obj = parse_task_dict(data)
                    if task_obj:
                        tasks.append(task_obj)
            except Exception as e:
                logger.error(f"Error parsing embedded tasks JSON: {e}")
                sys.exit(1)
            logger.info(f"Loaded {len(tasks)} embedded task(s)")
        else:
            tasks = load_tasks_from_json(args.tasks_file)
            if not tasks:
                logger.error("No valid tasks loaded.")
                sys.exit(1)
            logger.info(f"Loaded {len(tasks)} task(s) from {args.tasks_file}")
    
    has_ground_truth = any(
        any(q.ground_truth is not None for q in task.questions)
        for task in tasks
    )
    
    display_mode = not has_ground_truth
    
    benchmark = StandaloneBenchmark(
        client=client,
        wait_time=args.wait,
        temperature=args.temperature,
        system_message=args.system,
        verbose=args.verbose
    )

    requested_models = args.models if args.models is not None else DEFAULT_MODEL_NAMES
    catalog = client.fetch_models()
    resolved_models = resolve_model_targets(requested_models, catalog)
    if not resolved_models:
        logger.error("No valid models resolved.")
        sys.exit(1)

    human_targets = ", ".join(f"{label} [{model_id}]" for label, model_id in resolved_models)

    logger.info(f"Testing models: {human_targets}")
    if not display_mode:
        logger.info(f"Evaluation type: {args.eval_type if args.question else 'per-question'}")
    else:
        logger.info("Mode: Display only (no ground truth provided)")
    logger.info(f"Temperature: {args.temperature}")
    logger.info(f"Wait time: {args.wait}s")
    
    try:
        results = benchmark.run_benchmark(tasks, resolved_models)
        summary = generate_summary(results)
        print_summary(summary, results, display_mode)

        output_file = args.output
        if output_file is None and has_ground_truth:
            output_file = DEFAULT_OUTPUT_FILE

        if output_file:
            save_results(results, output_file)
    except Exception as e:
        logger.exception(f"Benchmark execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
