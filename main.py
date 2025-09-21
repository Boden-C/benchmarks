"""
CLI entry point for benchmark execution.

Provides command-line interface for running benchmarks with various options.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from benchmark.config.loader import load_config, apply_overrides


def setup_logging(verbose: bool = False) -> None:
    """
    Setup logging configuration.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def list_available_models() -> None:
    """List available models from global config."""
    try:
        config = load_config("global_config.yaml")
        
        print("\n=== Available Models ===\n")
        
        if not config.models:
            print("No models configured in global_config.yaml")
            return
        
        for model in config.models:
            print(f"- {model.name} ({model.provider})")
        
        print()
        
    except Exception as e:
        print(f"Error loading models: {e}")
        sys.exit(1)


def load_benchmark_class(benchmark_name: str):
    """
    Dynamically load benchmark class.
    
    Args:
        benchmark_name: Name of benchmark to load
    
    Returns:
        Benchmark class
    """
    import importlib
    
    try:
        # Try to import from tests/<benchmark_name>/<benchmark_name>.py
        module_path = f"tests.{benchmark_name}.{benchmark_name}"
        module = importlib.import_module(module_path)
        
        # Look for Benchmark subclass
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and attr_name.lower().endswith("benchmark")
                and attr_name != "Benchmark"
            ):
                return attr
        
        raise ImportError(f"No Benchmark class found in {module_path}")
        
    except ImportError as e:
        print(f"Error loading benchmark '{benchmark_name}': {e}")
        print(f"\nMake sure tests/{benchmark_name}/{benchmark_name}.py exists")
        sys.exit(1)


async def run_benchmark(
    benchmark_name: str,
    config_path: Optional[str] = None,
    questions_path: Optional[str] = None,
    models: Optional[str] = None,
    output: Optional[str] = None,
    verbose: bool = False,
    **kwargs
) -> None:
    """
    Run a benchmark.
    
    Args:
        benchmark_name: Name of benchmark to run
        config_path: Optional path to custom config
        questions_path: Optional path to custom questions file
        models: Comma-separated list of model names or "all"
        output: Optional custom output path
        verbose: Enable verbose logging
        **kwargs: Additional options
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting benchmark: {benchmark_name}")
    
    # Load benchmark class
    BenchmarkClass = load_benchmark_class(benchmark_name)
    
    # Prepare configuration
    if config_path:
        config = load_config("global_config.yaml", config_path)
    else:
        config = None  # Let benchmark load its own config
    
    # Filter models if specified
    if models and config:
        if models.lower() == "all":
            logger.info("Running on all configured models")
        else:
            model_names = [m.strip() for m in models.split(",")]
            config.models = [m for m in config.models if m.name in model_names]
            logger.info(f"Filtered to models: {model_names}")
    
    # Apply output path override
    if output and config:
        config = apply_overrides(config, {"results.output_dir": str(Path(output).parent)})
    
    # Create benchmark instance
    benchmark_kwargs = {}
    if config:
        benchmark_kwargs["config"] = config
    if questions_path:
        benchmark_kwargs["questions"] = questions_path
    
    benchmark = BenchmarkClass(**benchmark_kwargs)
    
    # Run benchmark
    logger.info("Executing benchmark...")
    result = await benchmark.run()
    
    # Display summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"\nBenchmark: {benchmark_name}")
    print(f"Models: {', '.join([m.name for m in benchmark.config.models])}")
    print(f"\nTasks completed: {result.summary['total_tasks']}")
    print(f"Mean score: {result.summary['mean_score']:.3f}")
    print(f"Pass rate: {result.summary['pass_rate']:.1%}")
    print(f"Total execution time: {result.execution_time:.2f}s")
    print(f"Total tokens used: {result.summary.get('total_tokens', 0):,}")
    print("\n" + "=" * 60 + "\n")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run LLM benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run benchmark
  python main.py --benchmark example_benchmark
  
  # With specific models
  python main.py --benchmark example_benchmark --models gpt-4o,claude-sonnet-4
  
  # With custom config
  python main.py --benchmark example_benchmark --config custom.yaml
  
  # List available models
  python main.py --list-models
        """,
    )
    
    parser.add_argument(
        "--benchmark",
        type=str,
        help="Name of benchmark to run (e.g., example_benchmark)",
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom config file",
    )
    
    parser.add_argument(
        "--questions",
        type=str,
        help="Path to custom questions file",
    )
    
    parser.add_argument(
        "--models",
        type=str,
        help="Comma-separated list of model names or 'all'",
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save results",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit",
    )
    
    args = parser.parse_args()
    
    # Handle list-models
    if args.list_models:
        list_available_models()
        return
    
    # Validate required args
    if not args.benchmark:
        parser.error("--benchmark is required (or use --list-models)")
    
    # Run benchmark
    try:
        asyncio.run(
            run_benchmark(
                benchmark_name=args.benchmark,
                config_path=args.config,
                questions_path=args.questions,
                models=args.models,
                output=args.output,
                verbose=args.verbose,
            )
        )
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBenchmark failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
