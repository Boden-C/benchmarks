"""
Execution state management for agentic execution.

Tracks compression attempts, token reduction, format fixes, and round limits.
"""

from dataclasses import dataclass


@dataclass
class ExecutionContext:
    """Execution state management for multi-round agentic execution."""
    
    compression_used: bool = False
    max_compression_attempts: int = 3
    compression_attempts: int = 0
    
    token_reduction_used: bool = False
    max_token_reductions: int = 3
    token_reduction_attempts: int = 0
    
    format_fix_used: bool = False
    max_format_fixes: int = 3
    format_fix_attempts: int = 0
    
    current_round: int = 0
    max_rounds: int = 10
    
    task_retries: int = 0
    max_task_retries: int = 3
    
    def can_compress(self) -> bool:
        """Returns True if compression available."""
        return self.compression_attempts < self.max_compression_attempts
    
    def mark_compressed(self) -> None:
        """Increments compression counter and sets flag."""
        self.compression_attempts += 1
        self.compression_used = True
    
    def can_reduce_tokens(self) -> bool:
        """Returns True if token reduction available."""
        return self.token_reduction_attempts < self.max_token_reductions
    
    def apply_token_reduction(self) -> None:
        """Increments reduction counter and sets flag."""
        self.token_reduction_attempts += 1
        self.token_reduction_used = True
    
    def can_fix_format(self) -> bool:
        """Returns True if format fixes available."""
        return self.format_fix_attempts < self.max_format_fixes
    
    def increment_format_fixes(self) -> None:
        """Increments format fix counter."""
        self.format_fix_attempts += 1
        self.format_fix_used = True
    
    def can_retry_round(self) -> bool:
        """Returns True if more rounds allowed."""
        return self.current_round < self.max_rounds
    
    def start_new_round(self) -> None:
        """Increments round counter."""
        self.current_round += 1
    
    def can_retry_task(self) -> bool:
        """Returns True if task retries available."""
        return self.task_retries < self.max_task_retries
    
    def start_new_task_retry(self) -> None:
        """Increments task retry counter."""
        self.task_retries += 1
    
    def get_status_summary(self) -> str:
        """Returns human-readable status string."""
        return (
            f"Round {self.current_round}/{self.max_rounds}, "
            f"Compressions: {self.compression_attempts}/{self.max_compression_attempts}, "
            f"Token reductions: {self.token_reduction_attempts}/{self.max_token_reductions}, "
            f"Format fixes: {self.format_fix_attempts}/{self.max_format_fixes}"
        )
