# Standalone Benchmark CLI

A minimal, zero-dependency LLM benchmarking tool using the Pollinations AI API. This script requires only Python's standard library and can run anywhere without installation.

Run `python standalone.py --list-models --show-all` to inspect canonical model identifiers; quote names containing spaces when passing `-m`.

## Features

-   **Zero Dependencies**: Uses only Python standard library (`urllib`, `json`, `argparse`)
-   **Pollinations AI Integration**: Leverages free Pollinations AI API for model access
-   **JSON Response Parsing**: Automatic structured output parsing with `json=true` parameter
-   **Inline Task Definition**: Define questions directly via command-line flags
-   **Flexible Evaluation**: Substring (default) or exact match validation
-   **Display Mode**: Compare model responses without ground truth validation
-   **Multiple Questions**: Single request with multiple questions, parsed as structured JSON
-   **Model Discovery**: Automatic fetching of available models from API
-   **Rate Limiting**: Configurable wait time between requests
-   **Detailed Results**: JSON output with execution times, scores, and metadata

## Quick Start

### Display Mode (No Validation)

Ask a question to multiple models and compare responses:

```powershell
python standalone.py -q "Explain quantum computing in simple terms" -m openai mistral deepseek
```

### Single Question with Validation

Ask a question with expected answer (substring match by default):

```powershell
python standalone.py -q "What is the capital of France?" -a "Paris" -m openai gemini
```

### Multiple Questions with Validation

Ask multiple questions in one request:

```powershell
python standalone.py -q "What is 2+2?" "What is 3*3?" "What is 10-5?" -a "4" "9" "5" --eval-type exact -m deepseek
```

### Load from File

```powershell
python standalone.py sample_tasks.json -m openai mistral
```

## Usage

### List Available Models

```powershell
python standalone.py --list-models
```

List only reasoning models:

```powershell
python standalone.py --list-models --reasoning-only
```

Show all details including aliases:

```powershell
python standalone.py --list-models --show-all
```

### Inline Questions (New Workflow)

#### Display Mode (No Ground Truth)

Compare how different models answer the same question:

```powershell
# Single question
python standalone.py -q "What is the meaning of life?" -m openai mistral gemini

# Multiple questions
python standalone.py -q "Describe AI" "Describe ML" -m deepseek openai-large
```

**Output**: Shows parsed JSON responses from all models without evaluation.

#### Validation Mode (With Ground Truth)

Test models against expected answers:

```powershell
# Substring match (default) - answer can appear anywhere in response
python standalone.py -q "What is the capital of Japan?" -a "Tokyo" -m openai

# Exact match - response must exactly match answer
python standalone.py -q "2+2" -a "4" --eval-type exact -m mistral

# Multiple questions with different answers
python standalone.py `
    -q "Capital of France?" "Capital of Germany?" "Capital of Italy?" `
    -a "Paris" "Berlin" "Rome" `
    -m openai gemini
```

#### Mixed Mode (Some Questions Without Answers)

```powershell
# Only first two questions validated, third is display-only
python standalone.py -q "2+2?" "3*3?" "What is quantum computing?" -a "4" "9" -m deepseek
```

### File-Based Tasks

Test from JSON file:

```powershell
python standalone.py sample_tasks.json -m openai mistral
```

### Configuration Options

```powershell
# Adjust temperature for creativity
python standalone.py -q "Write a poem" -m openai -t 1.5

# Reduce wait time (careful with rate limits)
python standalone.py sample_tasks.json -m openai -w 3

# Add system message
python standalone.py -q "Explain AI" -m gemini -s "Be technical and precise"

# Custom output file
python standalone.py -q "Test question" -a "answer" -m openai -o my_results.json

# Verbose logging
python standalone.py sample_tasks.json -m openai -v
```

### Complete Example

```powershell
python standalone.py `
    -q "What is 2+2?" "What is the capital of France?" "Explain AI briefly" `
    -a "4" "Paris" `
    --eval-type substr `
    -m openai mistral deepseek `
    -t 0.7 `
    -w 6 `
    -o comprehensive_results.json `
    -v
```

This will:

1. Ask 3 questions bundled into one task per model (3 total API calls)
2. Validate first two answers with substring matching
3. Display third answer without validation
4. Use structured JSON parsing for all responses
5. Save detailed results to file
6. Show verbose progress logs

## Command-Line Options

| Flag                | Description                                                               | Default                                                           |
| ------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `tasks_file`        | Path to tasks JSON file (standalone expects JSON array/object; not JSONL) | Optional                                                          |
| `-q, --question`    | Inline question(s) to ask                                                 | None                                                              |
| `-a, --answer`      | Expected answer(s) for validation                                         | None                                                              |
| `--eval-type`       | Evaluation type (substr, exact)                                           | `substr`                                                          |
| `-m, --models`      | Models to test                                                            | Curated defaults (`"OpenAI GPT-5 Nano"`, `"OpenAI GPT-4.1 Nano"`) |
| `-w, --wait`        | Wait time between requests (seconds)                                      | `6`                                                               |
| `-t, --temperature` | Sampling temperature (0.0-3.0)                                            | `1.0`                                                             |
| `--timeout`         | Request timeout (seconds)                                                 | `180`                                                             |
| `-s, --system`      | System message for model                                                  | None                                                              |
| `-o, --output`      | Output file for results                                                   | Auto (`standalone_results.json` when evaluating) or none          |
| `-v, --verbose`     | Enable verbose logging                                                    | `False`                                                           |
| `--list-models`     | List available models and exit                                            | -                                                                 |
| `--reasoning-only`  | List only reasoning models                                                | -                                                                 |
| `--show-all`        | Show all model details                                                    | -                                                                 |

## Workflow Modes

### 1. Display Mode (No Ground Truth)

**When**: No answers provided via `-a` flag or no `ground_truth` in file.

**Behavior**:

-   Models generate responses with JSON formatting
-   Responses are parsed and displayed
-   No validation performed
-   No results file saved by default (use `-o` to save)

**Example**:

```powershell
python standalone.py -q "Explain quantum entanglement" -m openai deepseek
```

**Output**:

```
MODEL RESPONSES
================================================================================
Model: openai
Response: {"answer": "Quantum entanglement is..."}
Extracted Answers:
  q1: Quantum entanglement is...
────────────────────────────────────────────────────────────────────────────────
Model: deepseek
Response: {"answer": "Entanglement occurs when..."}
Extracted Answers:
  q1: Entanglement occurs when...
```

### 2. Validation Mode (With Ground Truth)

**When**: Answers provided via `-a` flag or `ground_truth` in file.

**Behavior**:

-   Models generate responses with JSON formatting
-   Responses are parsed and validated
-   Scores calculated per question
-   Results saved to file automatically

**Example**:

```powershell
python standalone.py -q "What is 2+2?" -a "4" --eval-type exact -m openai
```

**Output**:

```
BENCHMARK SUMMARY
================================================================================
Model: openai
  Total Tasks:       1
  Passed:            1 (100.0%)
  Total Questions:   1
  Questions Passed:  1 (100.0%)
  Average Score:     1.000

Results saved to: standalone_results.json
```

### 3. Mixed Mode (Partial Ground Truth)

**When**: Some questions have answers, others don't.

**Behavior**:

-   Questions with answers are validated
-   Questions without answers are display-only
-   Overall scoring based only on validated questions

**Example**:

```powershell
python standalone.py -q "2+2?" "Explain AI" -a "4" -m openai
```

## JSON Response Parsing

The script automatically requests JSON-formatted responses and parses them intelligently.

### Single Question

**Request**: Question with `json=true` parameter

**Model returns**:

```json
{ "answer": "Paris" }
```

**Parsed**: Extracts "Paris" for validation

### Multiple Questions

**Request**: Multiple questions with JSON instruction

**Model returns**:

```json
{
    "1": "Paris",
    "2": "Berlin",
    "3": "Rome"
}
```

**Parsed**: Maps to question IDs (q1→"Paris", q2→"Berlin", q3→"Rome")

### Alternative Formats Supported

The parser handles various JSON structures:

```json
// Array format
["Paris", "Berlin", "Rome"]

// Answers object
{"answers": ["Paris", "Berlin", "Rome"]}

// Named questions
{"q1": "Paris", "q2": "Berlin"}

// Nested format
{"answers": {"q1": "Paris", "q2": "Berlin"}}
```

### Fallback

If JSON parsing fails, uses raw response text for validation.

## Task File Format

### New Format (Multiple Questions per Task)

```json
[
    {
        "id": "task_geography",
        "questions": [
            {
                "id": "q1",
                "text": "What is the capital of France?",
                "ground_truth": "Paris",
                "eval_type": "substr"
            },
            {
                "id": "q2",
                "text": "What is the capital of Japan?",
                "ground_truth": "Tokyo",
                "eval_type": "substr"
            }
        ],
        "metadata": {
            "category": "geography"
        }
    }
]
```

### Legacy Format (Backward Compatible)

```json
[
    {
        "id": "task_001",
        "prompt": "What is the capital of France?",
        "ground_truth": "Paris",
        "eval_type": "substr"
    }
]
```

**Note**: Legacy format automatically converted to new format internally.

### Display-Only Tasks

```json
[
    {
        "id": "creative_task",
        "questions": [
            {
                "id": "q1",
                "text": "Write a creative story opening"
            }
        ]
    }
]
```

Omit `ground_truth` for display-only questions.

## Evaluation Types

### Substring Match (`substr` - Default)

**Use case**: Answer can appear anywhere in response.

```powershell
python standalone.py -q "What is the capital of France?" -a "Paris" --eval-type substr
```

-   Response: "The capital of France is **Paris**, a beautiful city."
-   Result: ✅ **Pass** (contains "paris")

### Exact Match (`exact`)

**Use case**: Response must exactly match answer (case-insensitive).

```powershell
python standalone.py -q "2+2" -a "4" --eval-type exact
```

-   Response: "4"
-   Result: ✅ **Pass** (exact match)
-   Response: "The answer is 4"
-   Result: ❌ **Fail** (not exact match)

## Output Format

### Console Output

**Display Mode**:

```
MODEL RESPONSES
================================================================================
────────────────────────────────────────────────────────────────────────────────
Model: openai
Task:  inline_task
Time:  1.23s
────────────────────────────────────────────────────────────────────────────────

Parsed JSON Response:
{
  "1": "Paris",
  "2": "Tokyo"
}

Extracted Answers:
  q1: Paris
  q2: Tokyo
```

**Validation Mode**:

```
BENCHMARK SUMMARY
================================================================================

Model: openai
  Total Tasks:       1
  Passed:            1 (100.0%)
  Failed:            0
  Errors:            0
  Average Score:     1.000
  Total Questions:   2
  Questions Passed:  2 (100.0%)
  Total Time:        1.23s
  Average Time:      1.23s per task
```

### JSON Output File

Results are saved with detailed information:

```json
{
    "timestamp": "2025-10-28T12:34:56.789012",
    "total_executions": 2,
    "results": [
        {
            "model": "openai",
            "task_id": "inline_task",
            "success": true,
            "response": "{\n  \"1\": \"Paris\",\n  \"2\": \"Tokyo\"\n}",
            "parsed_json": {
                "1": "Paris",
                "2": "Tokyo"
            },
            "execution_time": 1.234,
            "error": null,
            "grade": {
                "overall_score": 1.0,
                "overall_passed": true,
                "reasoning": "2/2 questions passed",
                "question_grades": [
                    {
                        "question_id": "q1",
                        "score": 1.0,
                        "passed": true,
                        "reasoning": "Contains 'Paris'",
                        "expected": "Paris",
                        "actual": "Paris",
                        "metadata": { "eval_type": "substr" }
                    },
                    {
                        "question_id": "q2",
                        "score": 1.0,
                        "passed": true,
                        "reasoning": "Contains 'Tokyo'",
                        "expected": "Tokyo",
                        "actual": "Tokyo",
                        "metadata": { "eval_type": "substr" }
                    }
                ],
                "metadata": { "total_questions": 2 }
            },
            "timestamp": "2025-10-28T12:34:56.789012"
        }
    ]
}
```

## Available Models

The script automatically fetches models from `https://text.pollinations.ai/models`.

### Reasoning Models

-   `deepseek` - DeepSeek V3.1 (reasoning capable)
-   `openai-reasoning` - OpenAI o4 Mini (reasoning capable)

### Standard Models

-   `openai` - OpenAI GPT-5 Nano
-   `openai-fast` - OpenAI GPT-4.1 Nano
-   `openai-large` - OpenAI GPT-5 Chat
-   `gemini` - Gemini 2.5 Flash Lite
-   `gemini-search` - Gemini 2.5 Flash Lite with Google Search
-   `mistral` - Mistral Small 3.2 24B
-   `qwen-coder` - Qwen 2.5 Coder 32B

## Examples

### Quick Comparisons

Compare model responses side-by-side:

```powershell
# Philosophy question
python standalone.py -q "What is consciousness?" -m openai deepseek gemini

# Coding question
python standalone.py -q "Explain recursion in programming" -m qwen-coder openai mistral
```

### Comprehensive Benchmark

Test reasoning capabilities:

```powershell
python standalone.py `
    -q "If 5 machines make 5 widgets in 5 minutes, how long for 100 machines to make 100 widgets?" `
       "A bat and ball cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?" `
    -a "5" "0.05" `
    --eval-type substr `
    -m deepseek openai-reasoning mistral `
    -w 8 `
    -o reasoning_test.json
```

### Math Validation

```powershell
python standalone.py `
    -q "2+2" "10*5" "100/4" "7^2" `
    -a "4" "50" "25" "49" `
    --eval-type exact `
    -m openai mistral qwen-coder
```

### Creative Writing (Display Only)

```powershell
python standalone.py `
    -q "Write a haiku about artificial intelligence" `
       "Create a metaphor for quantum computing" `
    -m openai-large gemini deepseek `
    -t 1.2
```

### Mixed Evaluation

```powershell
# First two validated, third display-only
python standalone.py `
    -q "Capital of France?" "Capital of Japan?" "Describe Tokyo in one sentence" `
    -a "Paris" "Tokyo" `
    -m openai gemini
```

### File-Based Testing

```powershell
# Load from file
python standalone.py sample_tasks.json -m openai mistral gemini -v

# Multiple files (run separately)
python standalone.py sample_tasks.json -o results1.json
python standalone.py legacy_tasks.json -o results2.json
```

## Edge Cases Handled

### 1. Mismatched Question/Answer Counts

```powershell
# More questions than answers - extra questions are display-only
python standalone.py -q "Q1?" "Q2?" "Q3?" -a "A1" "A2" -m openai
```

### 2. JSON Parsing Failures

If model returns invalid JSON, falls back to raw text:

```
Response: "The answer is 42 (not valid JSON)"
Fallback: Uses full text for validation
```

### 3. Empty Responses

```
Response: ""
Result: Score 0.0, "No answer extracted from response"
```

### 4. Multiple Answers in Response

Parser tries multiple keys in order:

1. `"answer"` key
2. Question ID (`"q1"`)
3. Numbered key (`"1"`)
4. `"answers"` array by index
5. Raw response as fallback

### 5. Conflicting Flags

```powershell
# Error: Cannot use both
python standalone.py tasks.json -q "Question?" -m openai
# Error: Either tasks_file or --question is required
```

### 6. Model Errors

HTTP errors, timeouts, or API failures:

-   Captured as error in result
-   Score: 0.0
-   Reasoning: "Execution failed: {error}"
-   Continues with remaining models/tasks

## Rate Limiting

The Pollinations AI API is free but rate-limited. The default 6-second wait between requests is conservative. Adjust based on your needs:

-   **Development**: `-w 3` (faster iteration)
-   **Production**: `-w 6` (safe default)
-   **Bulk testing**: `-w 10` (very safe)

## Limitations

-   No authentication required (uses free tier)
-   Sequential execution (no parallel requests)
-   Basic error handling (no automatic retries)
-   No streaming support
-   Single-turn conversations only (no chat history)
-   JSON parsing best-effort (fallback to raw text)

## Integration with Main Benchmark

This standalone script complements the main benchmark system:

**When to use standalone**:

-   Quick prototyping and testing
-   Environments without pip/dependencies
-   CI/CD pipelines
-   Learning and experimentation
-   One-off comparisons

**When to use main benchmark**:

-   Complex multi-turn conversations
-   Custom tool integration
-   Advanced evaluation metrics
-   Large-scale batch processing
-   Detailed analytics and reporting

## Troubleshooting

### Connection Errors

```
Error: URL error: [Errno 11001] getaddrinfo failed
```

**Solution**: Check internet connection and firewall settings.

### Rate Limiting

```
HTTP 429: Too Many Requests
```

**Solution**: Increase wait time with `-w 10` or higher.

### JSON Parsing Issues

```
Warning: JSON parsing failed, using raw response
```

**Solution**: This is expected for some models. Validation still works with raw text.

### Empty File

```
Warning: Empty file sample_tasks.json
```

**Solution**: Verify file exists and contains valid JSON.

### Model Not Found

```
HTTP 400: Invalid model name
```

**Solution**: Run `python standalone.py --list-models` to see available models.

### Mixed Inline and File

```
Error: Cannot specify both tasks_file and --question
```

**Solution**: Use either `-q` for inline questions OR a file, not both.

## Performance Tips

1. **Model Selection**: Use `openai-fast` for quick iterations
2. **Batch Testing**: Test subset first with `-q`, then full file
3. **Temperature**: Lower (0.3-0.5) for factual, higher (1.0-1.5) for creative
4. **Wait Time**: Start with 6s, increase if rate-limited
5. **Verbose Mode**: Use `-v` to monitor progress on long runs

## Best Practices

1. **Start Simple**: Begin with single question display mode
2. **Validate Incrementally**: Add ground truth once you understand responses
3. **Use JSON Output**: Save results with `-o` for later analysis
4. **Test Models**: Try `--list-models` to find best model for your task
5. **Handle Failures**: Check error messages in verbose mode
6. **Version Control**: Keep task files in git for reproducibility

## License

Part of the benchmarks project. See parent LICENSE file.
