#!/usr/bin/env python3
"""
download_models.py — Download BERT clinical NER models from HuggingFace.

uMCP uses two Spanish clinical-domain RoBERTa models for entity recognition:
  1. bsc-bio-ehr-es-carmen-anon   (50 labels, F1: 0.954)
  2. bsc-bio-ehr-es-meddocan      (F1: 0.961)

Both models are developed by the Barcelona Supercomputing Center (BSC)
and released under an open license on HuggingFace.

Usage:
    python scripts/download_models.py                 # Downloads both models
    python scripts/download_models.py --model carmen   # Only CARMEN-ANON
    python scripts/download_models.py --model meddocan # Only MEDDOCAN
    python scripts/download_models.py --force          # Re-download even if exists

The models are saved to:  models/bsc-bio-ehr-es-{carmen-anon,meddocan}/
This directory is listed in .gitignore and NOT committed to the repository.
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure we can import transformers
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification
except ImportError:
    print("Installing transformers and torch...")
    import subprocess
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "transformers", "torch"]
    )
    from transformers import AutoTokenizer, AutoModelForTokenClassification


MODELS = {
    "carmen": {
        "repo": "PlanTL-GOB-ES/bsc-bio-ehr-es-carmen-anon",
        "dir": "bsc-bio-ehr-es-carmen-anon",
        "description": "CARMEN-I-anonymization (50 labels, F1: 0.954)",
    },
    "meddocan": {
        "repo": "PlanTL-GOB-ES/bsc-bio-ehr-es-meddocan",
        "dir": "bsc-bio-ehr-es-meddocan",
        "description": "MEDDOCAN (F1: 0.961)",
    },
}

MODELS_DIR = Path(__file__).parent.parent / "models"


def download_model(key: str, force: bool = False) -> None:
    """Download a model from HuggingFace and save it locally."""
    info = MODELS[key]
    target_dir = MODELS_DIR / info["dir"]

    if target_dir.exists() and not force:
        print(f"  ✓ {key}: already exists at {target_dir} (use --force to re-download)")
        return

    print(f"\n  Downloading {info['repo']} ...")
    print(f"  Description: {info['description']}")
    print(f"  Target: {target_dir}")
    print()

    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"  [1/2] Downloading tokenizer ...")
    tokenizer = AutoTokenizer.from_pretrained(info["repo"])
    tokenizer.save_pretrained(str(target_dir))
    print(f"         Saved to {target_dir / 'tokenizer.json'}")

    print(f"  [2/2] Downloading model weights ...")
    model = AutoModelForTokenClassification.from_pretrained(info["repo"])
    model.save_pretrained(str(target_dir))
    print(f"         Saved to {target_dir / 'pytorch_model.bin'}")

    # Write a README with model info
    readme = target_dir / "README.md"
    readme.write_text(
        f"# {info['dir']}\n\n"
        f"Source: {info['repo']}\n"
        f"Description: {info['description']}\n"
        f"Downloaded by: scripts/download_models.py\n"
        f"License: See original repository at https://huggingface.co/{info['repo']}\n"
    )

    print(f"  ✓ {key}: download complete ({target_dir})")
    print(f"    Total size (approx): {sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download BERT clinical NER models for uMCP"
    )
    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()) + ["all"],
        default="all",
        help="Model to download (default: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if model already exists",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  uMCP — Model Download Script")
    print("=" * 60)
    print()
    print(f"  Models directory: {MODELS_DIR}")
    print()

    if args.model == "all":
        keys = list(MODELS.keys())
    else:
        keys = [args.model]

    for key in keys:
        download_model(key, force=args.force)

    print()
    print("=" * 60)
    print("  All downloads complete.")
    print(f"  Models saved to: {MODELS_DIR}")
    print()
    print("  To verify:  python -c 'from umcp.gateway.server import app; app'")
    print("  The server will auto-detect the models at startup.")
    print("=" * 60)


if __name__ == "__main__":
    main()