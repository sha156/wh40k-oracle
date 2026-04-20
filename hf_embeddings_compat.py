from __future__ import annotations

from typing import Any


def get_huggingface_embeddings_cls():
    """Return a HuggingFaceEmbeddings class compatible with old and new LangChain layouts."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings
    except ModuleNotFoundError as exc:
        if exc.name != "langchain_huggingface":
            raise

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings
    except Exception as exc:
        raise ModuleNotFoundError(
            "Cannot import HuggingFaceEmbeddings. Install `langchain-huggingface` "
            "or run the app with the project virtualenv: "
            "`.\\.venv\\Scripts\\streamlit.exe run app.py`."
        ) from exc


def build_huggingface_embeddings(
    *,
    model_name: str,
    cache_folder: str | None = None,
    model_kwargs: dict[str, Any] | None = None,
    encode_kwargs: dict[str, Any] | None = None,
):
    """Create embeddings with a clearer error when the wrong Python environment is used."""
    embeddings_cls = get_huggingface_embeddings_cls()

    try:
        return embeddings_cls(
            model_name=model_name,
            cache_folder=cache_folder,
            model_kwargs=model_kwargs or {},
            encode_kwargs=encode_kwargs or {},
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to initialize HuggingFace embeddings. "
            "This usually means Streamlit was started from a global environment with "
            "an incompatible `torch` / `sentence-transformers` stack. "
            "Use the project virtualenv instead: "
            "`.\\.venv\\Scripts\\streamlit.exe run app.py`."
        ) from exc
