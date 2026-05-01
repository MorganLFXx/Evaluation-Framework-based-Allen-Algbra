# allen-inference

An experimental repository for data generation, model responses, verification, and analysis. It provides a unified entry point via `main.py` to run the full workflow quickly.

## Structure

- datasets/: datasets and answer files
- generate/: data generation and prompt construction
- explain/: answer verification and error checking
- probing/: probing training and inference
- utils/: shared utilities

## Setup

1. Python 3.10+ is recommended.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add a .env file next to this README and fill in required keys (e.g., model API keys).

## main.py Basics

Unified entry:

```bash
python main.py -h
```

### 1. Data generation

```bash
python main.py data --name my_data --n 100 --depth 2 --type single
python main.py data --name my_conflict --n 100 --depth 2 --type conflict
python main.py data --name my_fill --n 100 --depth 2 --type fill
```

Arguments:

- `--name`: output file name (written to datasets/)
- `--n`: number of samples
- `--depth`: recursion depth
- `--type`: task type single (Goal-Oriented Deduction) / conflict (Contradiction Source Detection) / fill (Local Gap Completion)

### 2. Response generation

```bash
python main.py response --name my_data --chat_type single --model deepseek-v3.2 --workers 4
```

### 3. Answer verification / analysis

```bash
python main.py qa --mode answer_verify --name my_data_deepseek-v3.2
python main.py qa --mode final_analyze --name my_data_deepseek-v3.2 --model qwen3.5-plus
```

### 4. Error checking

```bash
python main.py error --path my_data --model qwen3.5-plus --workers 4
```

### 5. Full pipeline

```bash
python main.py pipeline --name my_data --n 100 --depth 2 --chat_type single --model deepseek-v3.2 --check-model qwen3.5-plus --workers 4
```

Optional: skip error checking

```bash
python main.py pipeline --name my_data --skip-error-check
```

## Notes

See scripts under generate/ and explain/ for detailed parameters and data formats.
