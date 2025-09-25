# Standalone CLI Quick Reference

Use `python standalone.py --list-models --show-all` to discover exact model identifiers. Wrap multi-word names in quotes.

## Common Commands

### Discovery

```powershell
# List all models
python standalone.py --list-models

# List reasoning models only
python standalone.py --list-models --reasoning-only
```

### Display Mode (No Validation)

```powershell
# Single question
python standalone.py -q "Your question here" -m openai mistral

# Multiple questions
python standalone.py -q "Question 1?" "Question 2?" -m deepseek gemini
```

### Validation Mode (With Answers)

```powershell
# Substring match (default)
python standalone.py -q "Capital of France?" -a "Paris" -m openai

# Exact match
python standalone.py -q "2+2?" -a "4" --eval-type exact -m mistral

# Multiple Q&A
python standalone.py -q "Q1?" "Q2?" -a "A1" "A2" -m openai gemini
```

### File-Based

```powershell
# Load from file (JSON only)
python standalone.py tasks.json -m openai mistral
```

# With custom output

python standalone.py tasks.json -m deepseek -o results.json

````

## Flag Cheat Sheet

| Short | Long | Purpose | Example |
|-------|------|---------|---------|
| `-q` | `--question` | Inline question(s) | `-q "What is AI?"` |
| `-a` | `--answer` | Expected answer(s) | `-a "Artificial Intelligence"` |
| | `--eval-type` | Match type | `--eval-type exact` |
| `-m` | `--models` | Models to test | `-m openai mistral` |
| `-t` | `--temperature` | Creativity (0-3) | `-t 1.5` |
| `-w` | `--wait` | Wait seconds | `-w 10` |
| `-s` | `--system` | System message | `-s "Be concise"` |
| `-o` | `--output` | Output file | `-o results.json` |
| `-v` | `--verbose` | Verbose logging | `-v` |
| | `--timeout` | Request timeout | `--timeout 60` |

## Quick Recipes

### Compare Models on Same Question
```powershell
python standalone.py -q "Explain quantum computing" -m openai mistral deepseek gemini
````

### Math Quiz

```powershell
python standalone.py -q "2+2" "3*3" "10/2" -a "4" "9" "5" --eval-type exact -m openai
```

### Creative Writing Comparison

```powershell
python standalone.py -q "Write a haiku about technology" -m openai gemini -t 1.2
```

### Reasoning Test

```powershell
python standalone.py -q "If 5 machines take 5 mins to make 5 widgets, how long for 100 machines to make 100?" -a "5" -m deepseek openai-reasoning
```

### Batch File Test

```powershell
python standalone.py sample_tasks.json -m openai mistral qwen-coder -w 6 -o batch_results.json -v
```

## Task File Template

### Multiple Questions (New Format)

```json
{
    "id": "my_task",
    "questions": [
        {
            "id": "q1",
            "text": "Question 1?",
            "ground_truth": "Answer 1",
            "eval_type": "substr"
        },
        {
            "id": "q2",
            "text": "Question 2?",
            "ground_truth": "Answer 2",
            "eval_type": "exact"
        }
    ],
    "metadata": { "category": "test" }
}
```

### Single Question (Legacy Format)

```json
{
    "id": "task_001",
    "prompt": "Your question?",
    "ground_truth": "Expected answer",
    "eval_type": "substr"
}
```

### Display Only (No Validation)

```json
{
    "id": "creative_task",
    "questions": [{ "id": "q1", "text": "Write a story opening" }]
}
```

## Model Selection Guide

### Fast & Free

-   `openai` - GPT-5 Nano (balanced)
-   `openai-fast` - GPT-4.1 Nano (faster)
-   `mistral` - Mistral Small 3.2

### Reasoning

-   `deepseek` - DeepSeek V3.1 (best reasoning)
-   `openai-reasoning` - o4 Mini

### Specialized

-   `qwen-coder` - Coding tasks
-   `gemini` - Vision support
-   `gemini-search` - With Google Search

### Creative

-   `openai-large` - GPT-5 Chat (most capable)
-   `gemini` - Good for creative tasks

## Evaluation Types

| Type     | Match Rule         | Use Case                        |
| -------- | ------------------ | ------------------------------- |
| `substr` | Answer in response | Flexible matching, explanations |
| `exact`  | Response = answer  | Precise answers, math, facts    |

## Workflow Decision Tree

```
Start
 │
 ├─ Want to compare responses?
 │   └─ YES → Use display mode: -q "Question" -m model1 model2
 │
 ├─ Have expected answers?
 │   ├─ YES → Use validation mode: -q "Q" -a "A"
 │   └─ NO → Use display mode
 │
 ├─ Multiple questions?
 │   └─ YES → Use -q "Q1" "Q2" ... -a "A1" "A2" ...
 │
 ├─ Many tests?
 │   └─ YES → Create JSON file, use: standalone.py file.json
 │
 └─ Need exact matching?
     └─ YES → Add: --eval-type exact
```

## Common Patterns

### Pattern 1: Quick Prototype

```powershell
# Test single question on multiple models
python standalone.py -q "Your question?" -m openai mistral deepseek
```

### Pattern 2: Validation Run

```powershell
# Validate specific answer
python standalone.py -q "Question?" -a "Answer" --eval-type substr -m openai
```

### Pattern 3: Batch Testing

```powershell
# Run file-based tests
python standalone.py tests.json -m openai mistral -w 8 -o results.json -v
```

### Pattern 4: Reasoning Comparison

```powershell
# Compare reasoning models
python standalone.py -q "Complex problem?" -m deepseek openai-reasoning -w 10
```

## Troubleshooting

| Issue                    | Solution                   |
| ------------------------ | -------------------------- |
| Rate limited             | Increase `-w` value        |
| Timeout                  | Increase `--timeout` value |
| Wrong model              | Run `--list-models`        |
| JSON parse fail          | Normal, uses raw text      |
| No output file           | Add `-o filename.json`     |
| Can't use both file & -q | Choose one input method    |

## Tips

1. **Start simple**: `-q "Question?" -m openai`
2. **Add validation**: `-a "Answer"`
3. **Compare models**: `-m model1 model2 model3`
4. **Increase temperature** for creativity: `-t 1.5`
5. **Save results**: `-o results.json`
6. **Debug issues**: Add `-v` flag

## Environment

-   **Required**: Python 3.10+
-   **Dependencies**: None (stdlib only)
-   **Network**: Internet connection required
-   **API**: Pollinations AI (free, no key needed)
