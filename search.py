import functools
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from loader import load_all_pdfs, build_chunks
from config import logger, TOP_K_CHUNKS, MIN_SIMILARITY


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


@functools.lru_cache(maxsize=1)
def get_indexed_data():
    pages = load_all_pdfs()
    chunks = build_chunks(pages)
    if not chunks:
        logger.error("Chunk үүссэнгүй. PDF файлуудаа шалгана уу.")
        return [], None, None

    texts = [_normalize(c["text"]) for c in chunks]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_df=0.95)
    vectors = vectorizer.fit_transform(texts)
    logger.info(f"Индекс бэлэн: {len(chunks)} chunk, {vectors.shape[1]} feature.")
    return chunks, vectorizer, vectors


def search_relevant_chunks(question: str, top_k: int = TOP_K_CHUNKS) -> tuple[str, list[str]]:
    """Returns (context_with_source_headers, source_list)."""
    chunks, vectorizer, vectors = get_indexed_data()
    if not chunks or vectorizer is None:
        return "", []

    try:
        q_vector = vectorizer.transform([_normalize(question)])
        similarities = cosine_similarity(q_vector, vectors).flatten()
        top_indexes = similarities.argsort()[-top_k:][::-1]

        blocks: list[str] = []
        sources: list[str] = []
        seen = set()

        for i in top_indexes:
            if similarities[i] < MIN_SIMILARITY:
                continue
            c = chunks[i]
            header = f"--- Source: {c['source']}, Page {c['page']} ---"
            blocks.append(f"{header}\n{c['text']}")
            key = f"{c['source']} (хуудас {c['page']})"
            if key not in seen:
                sources.append(key)
                seen.add(key)

        return "\n\n".join(blocks), sources
    except Exception as e:
        logger.error(f"Хайлт хийхэд алдаа: {e}")
        return "", []
