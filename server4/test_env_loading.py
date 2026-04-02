"""Quick test to verify .env loading works correctly."""

import os
import sys

sys.path.insert(0, r"D:\Desktop\New_Flask\FLASK\server4")

# Load .env
env_path = r"D:\Desktop\New_Flask\FLASK\server4\.env"
loaded = 0
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
            loaded += 1

print(f"Loaded {loaded} environment variables from .env")
print()

# Check LLM keys
checks = {
    "DEEPSEEK_ENDPOINT": "DEEPSEEK_ENDPOINT",
    "DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
    "Mistral_endpoint": "Mistral_endpoint",
    "Mistral_api_key": "Mistral_api_key",
    "GROQ_API_KEY": "GROQ_API_KEY",
    "CF_WORKER_QWEN_URL": "CF_WORKER_QWEN_URL",
    "CF_WORKER_QWEN_TOKEN": "CF_WORKER_QWEN_TOKEN",
    "CF_WORKER_GEMMA_URL": "CF_WORKER_GEMMA_URL",
    "CF_WORKER_GEMMA_TOKEN": "CF_WORKER_GEMMA_TOKEN",
}

all_ok = True
for key, name in checks.items():
    val = os.environ.get(key, "")
    status = "OK" if val else "MISSING"
    if not val:
        all_ok = False
    print(f"  {name}: {status}")

print()
if all_ok:
    print("All LLM keys are configured!")
else:
    print("WARNING: Some LLM keys are missing. Check the .env file.")
