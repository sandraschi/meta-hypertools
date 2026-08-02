# 🧠 Token Analysis Suite

**LLM context optimization and cost control.**

A suite dedicated to helping developers understand and optimize the prompt payload they are sending to LLMs. Essential for managing costs and staying within context windows.

## Tools

### `estimate_context_limits`
Check if a token count fits within major model context windows.
- **Models**: GPT-4, Claude 3.5 Sonnet, Gemini 1.5 Pro, etc.
- **Returns**: Boolean compatibility and percentage usage for each model.
- **Args**: `token_count` (int)

### `analyze_file_tokens`
Count tokens in a specific file.
- **Features**: Language-aware tokenization (uses `tiktoken` or appropriate tokenizer).
- **Args**: `file_path` (str)

### `analyze_directory_tokens`
Aggregate token statistics for an entire directory tree.
- **Returns**: Total count, breakdown by file type, and largest files.
- **Args**: `dir_path` (str), `extensions` (list)

## Use Cases
- **Prompt Engineering**: "Will this context fit in Claude?"
- **Cost Estimation**: "How much will it cost to embed this entire repository?"
- **Optimization**: Identify massive files that are blowing up your context window unnecessarily.
