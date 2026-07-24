"""
Setup script for downloading required spaCy NLP models for Presidio PII detection.

Usage:
    python scripts/setup_nlp_models.py
"""

import subprocess
import sys


MODELS: list[dict[str, str]] = [
    {
        "name": "en_core_web_lg",
        "description": "spaCy English model (NER, POS tagging)",
        "size": "~400MB",
    },
    {
        "name": "es_core_news_md",
        "description": "spaCy Spanish model (NER, POS tagging)",
        "size": "~40MB",
    },
]


def download_model(model_name: str) -> bool:
    """Downloads spaCy model package. Returns True on success."""
    print(f"\n📥 Downloading model: {model_name}...")
    result = subprocess.run(
        [sys.executable, "-m", "spacy", "download", model_name],
        capture_output=False,
        text=True,
    )
    return result.returncode == 0


def main() -> None:
    print("=" * 60)
    print("  DevTalenty AI Extractor — NLP Models Setup")
    print("=" * 60)
    print("\nRequired spaCy models for Presidio PII detection:\n")

    for model in MODELS:
        print(f"  • {model['name']} — {model['description']} ({model['size']})")

    print("\n" + "-" * 60)

    failed: list[str] = []
    for model in MODELS:
        success = download_model(model["name"])
        if success:
            print(f"  ✅ {model['name']} installed successfully.")
        else:
            print(f"  ❌ Failed to install {model['name']}.")
            failed.append(model["name"])

    print("\n" + "=" * 60)
    if failed:
        print(f"⚠️  Failed models: {', '.join(failed)}")
        print("    Try installing manually:")
        for name in failed:
            print(f"      python -m spacy download {name}")
        sys.exit(1)
    else:
        print("✅ All NLP models installed successfully.")
        print("   PII detection engine is ready.")


if __name__ == "__main__":
    main()
