"""M2 constants. Values marked FIXED come from ARCHITECTURE.md 'Deterministic decisions'."""
import os

# --- swarm (FIXED) ---
MAX_ATTACKS_PER_BREAKER = 4
BUILDER_TEMP = 0.2
BREAKER_TEMPS = {"boundary": 0.8, "numeric_type": 0.9, "spec_gap": 1.0, "factual": 0.8}
BREAKER_SEEDS = {"boundary": 11, "numeric_type": 22, "spec_gap": 33, "factual": 44}

# --- token caps (Gateway enforces too) ---
BUILDER_MAX_TOKENS = 1600
BREAKER_MAX_TOKENS = 700
REPAIR_MAX_TOKENS = 700
LEDGER_PROMPT_CAP = 10          # survivors/landed lines shown per list

# --- sandbox (FIXED: 2s timeout, no network, memory-capped) ---
SANDBOX_TIMEOUT_S = float(os.getenv("SANDBOX_TIMEOUT_S", "2.0"))
SANDBOX_MEMORY_MB = int(os.getenv("SANDBOX_MEMORY_MB", "512"))

# --- NLI (FIXED: DeBERTa-v3 MNLI-family entailment classifier) ---
NLI_BACKEND = os.getenv("NLI_BACKEND", "hf")            # hf | local
NLI_MODEL = os.getenv("NLI_MODEL", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_NLI_URL = os.getenv("HF_NLI_URL", f"https://router.huggingface.co/hf-inference/models/{NLI_MODEL}")
NLI_THRESHOLD = 0.70
NLI_TOP_PASSAGES = 4
# Decision (change here only): does an UNSUPPORTED claim count as a landed break?
# False = only CONTRADICTED lands; unsupported shows amber. Safer against weak retrieval.
UNSUPPORTED_LANDS = os.getenv("UNSUPPORTED_LANDS", "0") == "1"

# --- v2: general code & reasoning ---
N_ORACLES = int(os.getenv("N_ORACLES", "2"))      # independent implementations / solvers per spec
ORACLE_TEMP = 0.5
ORACLE_SEEDS = (101, 202, 303)
SANDBOX_CONCURRENCY = int(os.getenv("SANDBOX_CONCURRENCY", "4"))
FUZZ_TIMEOUT_S = 4.0
FUZZ_SAMPLES = 150
