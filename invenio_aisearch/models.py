# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""AI model management for semantic search and NLP."""

import os
from pathlib import Path
from typing import Optional

from sentence_transformers import SentenceTransformer
from transformers import pipeline


class ModelManager:
    """Manage AI models for search and NLP tasks."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize model manager.

        Args:
            cache_dir: Directory to cache downloaded models
        """
        self.cache_dir = cache_dir or os.path.join(
            str(Path.home()), ".cache", "invenio_aisearch"
        )
        os.makedirs(self.cache_dir, exist_ok=True)

        self._embedding_model = None
        self._classifier = None
        self._summarizer = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        """Get or load the embedding model."""
        if self._embedding_model is None:
            print("Loading embedding model (sentence-transformers/all-MiniLM-L6-v2)...")
            self._embedding_model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                cache_folder=self.cache_dir
            )
            print("✓ Embedding model loaded")
        return self._embedding_model

    @property
    def classifier(self):
        """Get or load the zero-shot classification model."""
        if self._classifier is None:
            print("Loading classifier model (facebook/bart-large-mnli)...")
            self._classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1,  # CPU
                model_kwargs={"cache_dir": self.cache_dir}
            )
            print("✓ Classifier model loaded")
        return self._classifier

    @property
    def summarizer(self):
        """Get or load the summarization model."""
        if self._summarizer is None:
            print("Loading summarizer model (facebook/bart-large-cnn)...")
            self._summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1,  # CPU
                model_kwargs={"cache_dir": self.cache_dir}
            )
            print("✓ Summarizer model loaded")
        return self._summarizer

    def generate_embedding(self, text: str):
        """Generate embedding for text.

        Args:
            text: Input text

        Returns:
            numpy array of embedding vector
        """
        return self.embedding_model.encode(text, convert_to_numpy=True)

    def classify_intent(self, query: str, candidate_labels: list):
        """Classify query intent using zero-shot classification.

        Args:
            query: User query
            candidate_labels: Possible intent labels

        Returns:
            Classification result with scores
        """
        return self.classifier(query, candidate_labels)

    def generate_summary(self, text: str, max_length: int = 130, min_length: int = 30):
        """Generate summary of text.

        Args:
            text: Input text to summarize
            max_length: Maximum summary length
            min_length: Minimum summary length

        Returns:
            Summary text
        """
        # Truncate if too long (model has max input length)
        max_input_length = 1024
        if len(text) > max_input_length:
            text = text[:max_input_length]

        result = self.summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )
        return result[0]['summary_text']

    def preload_models(self):
        """Preload all models to avoid lazy loading delays."""
        print("Preloading AI models...")
        _ = self.embedding_model
        _ = self.classifier
        _ = self.summarizer
        print("✓ All models preloaded and ready")


# Global model manager instance
_model_manager = None


def get_model_manager(cache_dir: Optional[str] = None) -> ModelManager:
    """Get the global model manager instance.

    Args:
        cache_dir: Optional cache directory

    Returns:
        ModelManager instance
    """
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(cache_dir=cache_dir)
    return _model_manager
