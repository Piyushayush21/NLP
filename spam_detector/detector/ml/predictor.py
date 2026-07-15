"""
ML Predictor module — loads spam_model.pkl and vectorizer.pkl once
and exposes a predict() function used by Django views.
"""

import os
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ML_DIR = Path(__file__).resolve().parent
MODEL_PATH = ML_DIR / 'spam_model.pkl'
VECTORIZER_PATH = ML_DIR / 'vectorizer.pkl'

# ── Singleton loading ─────────────────────────────────────────────────────────
_model = None
_vectorizer = None


def _load_artifacts():
    """Load model and vectorizer from disk (called once on first use)."""
    global _model, _vectorizer

    if _model is not None and _vectorizer is not None:
        return  # already loaded

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found at: {MODEL_PATH}\n"
            "Please ensure spam_model.pkl is placed in detector/ml/"
        )
    if not VECTORIZER_PATH.exists():
        raise FileNotFoundError(
            f"Vectorizer file not found at: {VECTORIZER_PATH}\n"
            "Please ensure vectorizer.pkl is placed in detector/ml/"
        )

    logger.info("Loading spam model from %s …", MODEL_PATH)
    with open(MODEL_PATH, 'rb') as f:
        _model = pickle.load(f)

    logger.info("Loading vectorizer from %s …", VECTORIZER_PATH)
    with open(VECTORIZER_PATH, 'rb') as f:
        _vectorizer = pickle.load(f)

    logger.info("Model and vectorizer loaded successfully.")


def predict(text: str) -> dict:
    """
    Predict whether a message is spam or ham.

    Args:
        text: Raw email/message string.

    Returns:
        dict with keys:
            label       – 'spam' or 'ham'
            confidence  – confidence % for the predicted class (0-100)
            spam_prob   – probability of spam (0-100)
            ham_prob    – probability of ham (0-100)
    """
    _load_artifacts()

    # Transform text using the TF-IDF vectorizer
    X = _vectorizer.transform([text])

    # Predict class (0 = ham, 1 = spam)
    prediction = _model.predict(X)[0]

    # Get class probabilities
    proba = _model.predict_proba(X)[0]  # [ham_prob, spam_prob]
    ham_prob = float(proba[0]) * 100
    spam_prob = float(proba[1]) * 100

    label = 'spam' if prediction == 1 else 'ham'
    confidence = spam_prob if label == 'spam' else ham_prob

    return {
        'label': label,
        'confidence': round(confidence, 2),
        'spam_prob': round(spam_prob, 2),
        'ham_prob': round(ham_prob, 2),
    }


def predict_batch(texts: list) -> list:
    """
    Predict for a list of messages.

    Args:
        texts: List of raw strings.

    Returns:
        List of result dicts (same schema as predict()).
    """
    _load_artifacts()

    results = []
    for text in texts:
        if text.strip():
            results.append({'text': text.strip(), **predict(text.strip())})
    return results
