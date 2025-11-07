#!/usr/bin/env python3
"""
Download and test AI models for invenio-aisearch.

This script downloads the required HuggingFace models and tests that they work correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from invenio_aisearch.models import get_model_manager


def main():
    """Download and test models."""
    print("=" * 60)
    print("InvenioRDM AI Search - Model Setup")
    print("=" * 60)
    print()

    # Get model manager
    model_manager = get_model_manager()

    print("This will download approximately 3.3GB of AI models.")
    print("Models will be cached for future use.")
    print()

    try:
        # Preload all models
        model_manager.preload_models()

        print()
        print("=" * 60)
        print("Testing Models")
        print("=" * 60)
        print()

        # Test embedding model
        print("1. Testing embedding generation...")
        test_text = "Pride and Prejudice is a novel by Jane Austen"
        embedding = model_manager.generate_embedding(test_text)
        print(f"   ✓ Generated embedding vector (shape: {embedding.shape})")
        print(f"   ✓ Dimension: {len(embedding)} (expected: 384)")
        print()

        # Test classifier
        print("2. Testing query classification...")
        test_query = "find me books with female protagonists"
        labels = ["search_query", "question", "command"]
        result = model_manager.classify_intent(test_query, labels)
        print(f"   ✓ Classified as: {result['labels'][0]} (score: {result['scores'][0]:.2f})")
        print()

        # Test summarizer
        print("3. Testing summarization...")
        test_long_text = """
        Pride and Prejudice is a romantic novel of manners written by Jane Austen in 1813.
        The novel follows the character development of Elizabeth Bennet, the dynamic protagonist
        who learns about the repercussions of hasty judgments and comes to appreciate the
        difference between superficial goodness and actual goodness. Its humour lies in its
        honest depiction of manners, education, marriage, and money during the Regency era in England.
        """
        summary = model_manager.generate_summary(test_long_text.strip())
        print(f"   ✓ Generated summary:")
        print(f"   \"{summary}\"")
        print()

        print("=" * 60)
        print("✓ All models successfully loaded and tested!")
        print("=" * 60)
        print()
        print("Models are cached in:", model_manager.cache_dir)
        print()
        print("Next steps:")
        print("  1. Install the module: pip install -e .")
        print("  2. Generate embeddings for your books")
        print("  3. Test semantic search")
        print()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure you have enough disk space (~4GB)")
        print("  - Check your internet connection")
        print("  - Try running with: python3 -m pip install --upgrade transformers sentence-transformers")
        sys.exit(1)


if __name__ == "__main__":
    main()
