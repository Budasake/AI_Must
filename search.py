import functools
import re
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import CATEGORIES, MIN_SIMILARITY, TOP_K_CHUNKS, logger
from loader import build_chunks_for_category



def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@functools.lru_cache(maxsize=10)
def get_indexed_data(category: str):

    if category not in CATEGORIES:
        logger.warning(f"Unknown category for indexing: {category}")
        return [], None, None

    chunks = build_chunks_for_category(category)

    if not chunks:
        logger.warning(f"No chunks created for category: {category}")
        return [], None, None

    texts = [normalize_text(chunk["text"]) for chunk in chunks]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )

    vectors = vectorizer.fit_transform(texts)

    logger.info(
        f"Index ready for '{category}': "
        f"{len(chunks)} chunks, {vectors.shape[1]} features."
    )

    return chunks, vectorizer, vectors


def search_relevant_chunks(
    question: str,
    category: str,
    top_k: Optional[int] = None,
) -> tuple[str, list[str]]:

    if top_k is None:
        top_k = TOP_K_CHUNKS

    question = normalize_text(question)

    if not question:
        return "", []

    chunks, vectorizer, vectors = get_indexed_data(category)

    if not chunks or vectorizer is None or vectors is None:
        return "", []

    try:
        query_vector = vectorizer.transform([question])
        similarities = cosine_similarity(query_vector, vectors).flatten()

        ranked_indexes = similarities.argsort()[::-1]

        context_blocks: list[str] = []
        sources: list[str] = []
        seen_sources = set()

        for index in ranked_indexes:
            if len(context_blocks) >= top_k:
                break

            score = float(similarities[index])

            if score < MIN_SIMILARITY:
                continue

            chunk = chunks[index]

            source_name = chunk.get("source", "unknown.pdf")
            page_number = chunk.get("page", "?")
            chunk_category = chunk.get("category", category)
            chunk_text = chunk.get("text", "")

            header = (
                f"--- Source: {source_name}, "
                f"Page {page_number}, "
                f"Category {chunk_category}, "
                f"Score {score:.3f} ---"
            )

            context_blocks.append(f"{header}\n{chunk_text}")

            source_key = f"{source_name} (хуудас {page_number})"

            if source_key not in seen_sources:
                sources.append(source_key)
                seen_sources.add(source_key)

        if not context_blocks:
            logger.info(
                f"No relevant chunks found. "
                f"category={category}, question='{question[:80]}'"
            )

        return "\n\n".join(context_blocks), sources

    except Exception as e:
        logger.error(
            f"Search error. category={category}, question='{question[:80]}': {e}",
            exc_info=True
        )
        return "", []


def clear_indexes():

    get_indexed_data.cache_clear()
    logger.info("All category indexes cleared.")


def get_category_chunk_count(category: str) -> int:
    chunks, _, _ = get_indexed_data(category)
    return len(chunks)


def get_all_category_counts() -> dict[str, int]:
    return {
        category: get_category_chunk_count(category)
        for category in CATEGORIES
    }


def get_category_sources(category: str) -> list[str]:
    chunks, _, _ = get_indexed_data(category)

    if not chunks:
        return []

    sources = sorted({
        chunk.get("source", "unknown.pdf")
        for chunk in chunks
    })

    return sources