import os
import re
from pypdf import PdfReader
from config import logger, LECTURE_FOLDER


# =========================
# PDF LOADING
# =========================

def load_all_pdfs(folder_path: str = LECTURE_FOLDER) -> list[dict]:
    """
    PDF файлуудыг уншиж, metadata-тай хуудас list буцаана.
    Returns: [{"text": "...", "source": "file.pdf", "page": 3}, ...]
    """
    if not os.path.exists(folder_path):
        logger.warning(f"Лекцийн хавтас олдсонгүй: {folder_path}")
        return []

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

    if not pdf_files:
        logger.warning(f"{folder_path} хавтаст PDF файл байхгүй.")
        return []

    pages = []
    for filename in pdf_files:
        file_path = os.path.join(folder_path, filename)
        logger.info(f"PDF уншиж байна: {filename}")

        try:
            reader = PdfReader(file_path)
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    pages.append({
                        "text": page_text.strip(),
                        "source": filename,
                        "page": page_num
                    })
        except Exception as e:
            logger.error(f"{filename} уншихад алдаа: {e}")

    logger.info(f"Нийт {len(pages)} хуудас уншлаа ({len(pdf_files)} PDF файлаас).")
    return pages


# =========================
# SMART CHUNKING
# =========================

def split_page_into_chunks(page_data: dict, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    """Нэг хуудасны текстийг параграфаар ухаалаг хуваана."""
    text   = page_data["text"]
    source = page_data["source"]
    page   = page_data["page"]

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append({"text": current_chunk.strip(), "source": source, "page": page})
            overlap_text  = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + para + "\n\n"

    if current_chunk.strip():
        chunks.append({"text": current_chunk.strip(), "source": source, "page": page})

    return chunks


def build_chunks(pages: list[dict]) -> list[dict]:
    """Бүх хуудсыг chunk-үүдэд хуваана."""
    all_chunks = []
    for page in pages:
        all_chunks.extend(split_page_into_chunks(page))
    return all_chunks
