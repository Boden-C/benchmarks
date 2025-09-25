# Standalone Script - Usage Examples

Use `python standalone.py --list-models --show-all` to confirm model identifiers. Quote names containing spaces.

## Scenario-Based Examples

### 1. Quick Model Comparison

**Goal**: Compare how different models answer the same question.

```powershell
python standalone.py -q "Explain the difference between AI and ML" -m openai mistral gemini deepseek
```

**What happens**:

-   Single question sent to 4 models
-   Each model returns JSON response
-   Responses displayed side-by-side
-   No scoring (display mode)
-   No output file

**Use when**:

-   Exploring model capabilities
-   Choosing best model for a task
-   Understanding response differences

---

### 2. Factual Validation

**Goal**: Test if models know basic facts.

```powershell
python standalone.py `
    -q "What is the capital of France?" `
       "What is the capital of Japan?" `
       "What is the capital of Germany?" `
    -a "Paris" "Tokyo" "Berlin" `
    -m openai mistral `
    --eval-type substr
```

**What happens**:

-   3 questions in single request to 2 models (2 API calls total)
-   JSON response parsed: `{"1": "Paris", "2": "Tokyo", "3": "Berlin"}`
-   Each answer validated with substring match
-   Results saved automatically
-   Summary shows pass rates

**Use when**:

-   Testing factual knowledge
-   Benchmarking accuracy
-   Comparing model reliability

---

### 3. Math Quiz (Exact Answers)

**Goal**: Test arithmetic precision.

```powershell
python standalone.py `
    -q "2+2" "10*5" "100/4" "2^8" "sqrt(144)" `
    -a "4" "50" "25" "256" "12" `
    --eval-type exact `
    -m qwen-coder openai mistral `
    -o math_results.json
```

**What happens**:

-   5 math questions to 3 models
-   Exact matching (must be "4", not "The answer is 4")
-   Saved to custom file
-   Shows which models are most precise

**Use when**:

-   Testing calculation accuracy
-   Comparing reasoning models
-   Validating structured output

---

### 4. Reasoning Challenge

**Goal**: Test logical reasoning ability.

```powershell
python standalone.py `
    -q "If 5 machines take 5 minutes to make 5 widgets, how many minutes for 100 machines to make 100 widgets?" `
    -a "5" `
    -m deepseek openai-reasoning mistral `
    --eval-type substr `
    -w 10 `
    -v
```

**What happens**:

-   Complex reasoning question
-   Tests understanding vs pattern matching
-   Longer wait time (reasoning models may be slower)
-   Verbose output shows execution details
-   Compare reasoning-capable vs standard models

**Use when**:

-   Evaluating logical reasoning
-   Testing problem-solving ability
-   Comparing reasoning models

---

### 5. Creative Writing Comparison

**Goal**: Compare creative outputs without scoring.

```powershell
python standalone.py `
    -q "Write a haiku about artificial intelligence" `
       "Create a metaphor comparing code to music" `
    -m openai-large gemini mistral `
    -t 1.5 `
    -o creative_outputs.json
```

**What happens**:

-   Display mode (no ground truth)
-   Higher temperature for creativity
-   Each model's creative response shown
-   Saved for later review
-   No scoring, just comparison

**Use when**:

-   Testing creative capabilities
-   Comparing writing styles
-   Exploring model personalities

---

### 6. Batch File Testing

**Goal**: Run comprehensive test suite from file.

**File: `benchmark_suite.json`**

```json
[
    {
        "id": "math_test",
        "questions": [
            { "id": "q1", "text": "15 * 8", "ground_truth": "120", "eval_type": "exact" },
            { "id": "q2", "text": "144 / 12", "ground_truth": "12", "eval_type": "exact" }
        ]
    },
    {
        "id": "geography_test",
        "questions": [
            { "id": "q1", "text": "Capital of Italy?", "ground_truth": "Rome", "eval_type": "substr" },
            { "id": "q2", "text": "Capital of Spain?", "ground_truth": "Madrid", "eval_type": "substr" }
        ]
    }
]
```

**Command:**

```powershell
python standalone.py benchmark_suite.json -m openai mistral qwen-coder -w 6 -o suite_results.json -v
```

**What happens**:

-   2 tasks, each with 2 questions = 4 questions total
-   But only 2 API calls per model (questions bundled)
-   3 models tested
-   Total: 6 API calls (vs 12 if questions separate)
-   Detailed results saved
-   Progress tracked with verbose mode

**Use when**:

-   Running regular benchmarks
-   Testing multiple categories
-   Systematic model evaluation

---

### 7. Mixed Validation

**Goal**: Some questions validated, others just displayed.

```powershell
python standalone.py `
    -q "What is 2+2?" `
       "Explain how you arrived at that answer" `
       "What is 3*3?" `
    -a "4" "" "9" `
    -m deepseek openai-reasoning `
    --eval-type exact
```

**What happens**:

-   Question 1: Validated (answer "4" provided)
-   Question 2: Display only (empty answer)
-   Question 3: Validated (answer "9" provided)
-   Shows both scoring and explanations
-   Useful for understanding reasoning

**Use when**:

-   Need both validation and exploration
-   Want to see model's reasoning
-   Testing explanation quality

---

### 8. Model Discovery

**Goal**: Find best model for specific task.

```powershell
# Step 1: List available models
python standalone.py --list-models --reasoning-only

# Step 2: Test reasoning models
python standalone.py `
    -q "A farmer has 15 sheep. All but 8 die. How many are left?" `
    -a "8" `
    -m deepseek openai-reasoning `
    --eval-type exact

# Step 3: Test on creative task
python standalone.py `
    -q "Write a short poem about stars" `
    -m deepseek openai-reasoning openai-large `
    -t 1.2
```

**What happens**:

-   First: See all reasoning models available
-   Second: Test on logic puzzle
-   Third: Compare creative abilities
-   Helps choose right model for your needs

**Use when**:

-   Starting a new project
-   Unsure which model to use
-   Need to justify model selection

---

### 9. System Message Guidance

**Goal**: Guide model behavior with system message.

```powershell
python standalone.py `
    -q "Explain quantum computing" `
    -m gemini openai `
    -s "You are a teacher explaining to a 10-year-old. Use simple language and analogies." `
    -t 0.7
```

**What happens**:

-   System message sets context
-   Model adjusts tone and complexity
-   Compare how models follow instructions
-   Display mode shows differences

**Use when**:

-   Need specific tone/style
-   Testing instruction following
-   Persona-based responses

---

### 10. Rapid Prototyping

**Goal**: Quickly test prompt variations.

```powershell
# Test 1: Direct question
python standalone.py -q "Explain AI" -m openai

# Test 2: More specific
python standalone.py -q "Explain AI in exactly one sentence" -m openai

# Test 3: With context
python standalone.py -q "Explain AI to a beginner programmer" -m openai

# Test 4: With validation
python standalone.py `
    -q "Explain AI in one sentence" `
    -a "artificial intelligence" `
    --eval-type substr `
    -m openai
```

**What happens**:

-   Rapid iteration without file creation
-   See how prompt changes affect output
-   Add validation when satisfied
-   Fast feedback loop

**Use when**:

-   Developing prompts
-   Testing prompt engineering
-   Finding optimal phrasing

---

### 11. Multilingual Testing

**Goal**: Test model language capabilities.

```powershell
python standalone.py `
    -q "What is 'hello' in Spanish?" `
       "What is 'hello' in French?" `
       "What is 'hello' in German?" `
    -a "hola" "bonjour" "hallo" `
    --eval-type substr `
    -m openai gemini mistral
```

**What happens**:

-   Tests translation knowledge
-   Substring match allows for variations
-   Compare multilingual capabilities
-   Identifies best model for translations

**Use when**:

-   Building multilingual apps
-   Testing translation quality
-   Comparing language support

---

### 12. Error Tolerance Testing

**Goal**: Test how models handle ambiguous questions.

```powershell
python standalone.py `
    -q "What is the meaning of 'bank'?" `
       "What color is a mirror?" `
       "How long is a piece of string?" `
    -m openai mistral deepseek
```

**What happens**:

-   Ambiguous questions without validation
-   Display mode shows how each model handles ambiguity
-   Compare response quality
-   Identify most thoughtful model

**Use when**:

-   Testing edge cases
-   Evaluating reasoning quality
-   Understanding model limitations

---

### 13. Performance Benchmarking

**Goal**: Measure response time across models.

```powershell
python standalone.py `
    -q "What is 2+2?" `
    -a "4" `
    -m openai openai-fast mistral qwen-coder gemini `
    -w 3 `
    -o performance_test.json `
    -v
```

**What happens**:

-   Same simple question to all models
-   Verbose mode shows timing per request
-   Results include execution_time per model
-   Identify fastest model

**Use when**:

-   Optimizing for speed
-   Cost/performance tradeoffs
-   Latency-sensitive applications

---

### 14. Legacy Format Support

**Goal**: Use old task format (backward compatibility).

**File: `old_format.json`**

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

**Command:**

```powershell
python standalone.py old_format.json -m openai
```

**What happens**:

-   Legacy format automatically detected
-   Converted to new format internally
-   Works exactly as before
-   No migration needed

**Use when**:

-   Using existing task files
-   Gradual migration to new format
-   Backward compatibility needed

---

### 15. Comprehensive Evaluation

**Goal**: Full model evaluation across multiple dimensions.

```powershell
# Math accuracy
python standalone.py `
    -q "2+2" "10*5" "100/4" `
    -a "4" "50" "25" `
    --eval-type exact `
    -m openai mistral qwen-coder `
    -o eval_math.json

# Factual knowledge
python standalone.py `
    -q "Capital of France?" "Capital of Japan?" `
    -a "Paris" "Tokyo" `
    -m openai mistral qwen-coder `
    -o eval_facts.json

# Reasoning
python standalone.py `
    -q "If all roses are flowers and some flowers fade quickly, can we conclude all roses fade quickly?" `
    -a "No" `
    -m openai mistral deepseek `
    -o eval_reasoning.json

# Compare all results
cat eval_*.json | ConvertFrom-Json | Select-Object timestamp, results
```

**What happens**:

-   Multiple test categories
-   Separate result files
-   Can aggregate and compare
-   Comprehensive model profile

**Use when**:

-   Full model evaluation
-   Model selection for production
-   Creating model comparison reports

---

## Quick Reference by Goal

| Goal               | Command Pattern                         |
| ------------------ | --------------------------------------- |
| Compare models     | `-q "Question" -m model1 model2 model3` |
| Validate answer    | `-q "Question" -a "Answer" -m model`    |
| Exact match        | Add `--eval-type exact`                 |
| Multiple questions | `-q "Q1" "Q2" -a "A1" "A2"`             |
| Creative/high temp | Add `-t 1.5`                            |
| Save results       | Add `-o filename.json`                  |
| See progress       | Add `-v`                                |
| Slower rate        | Add `-w 10`                             |
| Guide behavior     | Add `-s "System message"`               |
| Use file           | `tasks.json -m model`                   |
| List models        | `--list-models`                         |

## Tips for Success

1. **Start with display mode** to understand responses
2. **Add validation incrementally** as you refine expectations
3. **Use verbose mode** for debugging and monitoring
4. **Increase wait time** if rate-limited
5. **Save results** for later analysis
6. **Group related questions** for efficiency
7. **Use exact match** for structured data
8. **Use substr match** for natural language
9. **Adjust temperature** based on task type
10. **Test with multiple models** to find the best fit
