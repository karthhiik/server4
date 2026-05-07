"""
V4 HF Embeddings — local bge-small-en-v1.5 wrapper.

Model: BAAI/bge-small-en-v1.5
  - License: MIT (commercial-safe for SaaS)
  - Size: 33M params, ~133MB FP32 / ~67MB FP16
  - Dimension: 384
  - Source: https://huggingface.co/BAAI/bge-small-en-v1.5

Usage:
    embedder = await get_embedder()
    vec = await embedder.embed_one("text")          # 384-dim list[float]
    vecs = await embedder.embed_many(["a", "b"])    # list[list[float]]

Behaviour:
  - Lazy singleton: model loads on first call (downloads from HF on first run).
  - Inference runs in a thread pool (sentence-transformers is sync CPU-bound).
  - HUGGINGFACE_API_TOKEN is forwarded to huggingface_hub for gated model access.
  - Cache directory: settings.EMBEDDINGS_PATH (defaults to D:/Desktop/newpitchdecks/data/embeddings).
  - Graceful degradation: if sentence_transformers is unavailable, raises a clear
    error at first use (NOT at import time) so the rest of the app keeps working.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

MODEL_ID = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


class HFEmbedder:
    def __init__(self) -> None:
        self._model = None
        self._lock = asyncio.Lock()

    async def _ensure_loaded(self):
        await self._do_load()

    def is_loaded(self) -> bool:
        return self._model is not None

    async def _do_load(self):
        if self._model is not None:
            return
        async with self._lock:
            if self._model is not None:
                return
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "sentence-transformers not installed; "
                    "add `sentence-transformers>=2.7.0` to requirements.txt"
                ) from e

            cache_dir = self._cache_dir()
            hf_token = os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN")
            device = os.environ.get("MODEL_DEVICE", "cpu")
            logger.info("hf_embedder.loading", model=MODEL_ID, device=device, cache_dir=str(cache_dir))

            def _load():
                kwargs: dict = {"device": device, "cache_folder": str(cache_dir)}
                if hf_token:
                    try:
                        return SentenceTransformer(MODEL_ID, token=hf_token, **kwargs)
                    except TypeError:
                        return SentenceTransformer(MODEL_ID, use_auth_token=hf_token, **kwargs)
                return SentenceTransformer(MODEL_ID, **kwargs)

            self._model = await asyncio.to_thread(_load)
            logger.info("hf_embedder.loaded", model=MODEL_ID)

    @staticmethod
    def _cache_dir() -> Path:
        try:
            from app.config import settings
            d = Path(getattr(settings, "EMBEDDINGS_PATH", "") or "./.cache/embeddings")
        except Exception:
            d = Path("./.cache/embeddings")
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def embed_one(self, text: str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * EMBED_DIM
        out = await self.embed_many([text])
        return out[0]

    async def embed_many(self, texts: list[str], *, batch_size: int = 32, normalize: bool = True) -> list[list[float]]:
        if not texts:
            return []
        await self._ensure_loaded()
        clean = [t if (t and t.strip()) else " " for t in texts]

        def _encode():
            return self._model.encode(  # type: ignore[union-attr]
                clean,
                batch_size=batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

        arr = await asyncio.to_thread(_encode)
        return arr.tolist()


# Singleton
_embedder: Optional[HFEmbedder] = None
_init_lock = asyncio.Lock()


async def get_embedder() -> HFEmbedder:
    global _embedder
    if _embedder is not None:
        return _embedder
    async with _init_lock:
        if _embedder is None:
            _embedder = HFEmbedder()
        return _embedder
