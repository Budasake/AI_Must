import os
import re
from pathlib import Path
from pypdf import PdfReader

from config import (
    logger,
    LOCAL_MATERIALS_DIR,
    CATEGORIES,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    USE_GOOGLE_DRIVE,
)

from drive_loader import download_drive_pdfs_by_category


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_local_pdf_files(category: str) -> list[Path]:
    folder_path = Path(LOCAL_MATERIALS_DIR) / category

    if not folder_path.exists():
        logger.warning(f"Local category folder not found: {folder_path}")
        return []

    pdf_files = sorted(folder_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No local PDF files found in: {folder_path}")

    return pdf_files


def get_pdf_files_for_category(category: str) -> list[Path]:
    if category not in CATEGORIES:
        logger.warning(f"Unknown category: {category}")
        return []

    if USE_GOOGLE_DRIVE:
        logger.info(f"Using Google Drive PDFs for category: {category}")
        return download_drive_pdfs_by_category(category)

    logger.info(f"Using local PDFs for category: {category}")
    return get_local_pdf_files(category)


def load_pdf_pages(file_path: Path, category: str) -> list[dict]:
    pages = []

    try:
        reader = PdfReader(str(file_path))

        if reader.is_encrypted:
            logger.warning(f"Encrypted PDF skipped: {file_path.name}")
            return []

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
                page_text = clean_text(page_text)

                if page_text:
                    pages.append({
                        "text": page_text,
                        "source": file_path.name,
                        "page": page_num,
                        "category": category,
                    })

            except Exception as e:
                logger.warning(
                    f"Failed to extract page {page_num} from {file_path.name}: {e}"
                )

    except Exception as e:
        logger.error(f"Error reading PDF {file_path.name}: {e}", exc_info=True)

    return pages


def load_pdfs_by_category(category: str) -> list[dict]:
    pdf_files = get_pdf_files_for_category(category)

    pages = []

    for pdf_file in pdf_files:
        logger.info(f"Reading PDF: {category}/{pdf_file.name}")
        pages.extend(load_pdf_pages(pdf_file, category))

    logger.info(
        f"{category}: loaded {len(pages)} text pages from {len(pdf_files)} PDF files."
    )

    return pages



def split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += max(chunk_size - overlap, 1)

    return chunks


def split_page_into_chunks(page_data: dict) -> list[dict]:
    text = page_data["text"]
    source = page_data["source"]
    page = page_data["page"]
    category = page_data["category"]

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n{2,}", text)
        if paragraph.strip()
    ]

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(paragraph) > CHUNK_SIZE:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = ""

            chunks.extend(split_long_text(paragraph, CHUNK_SIZE, CHUNK_OVERLAP))
            continue

        if len(current_chunk) + len(paragraph) + 2 <= CHUNK_SIZE:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            overlap_text = (
                current_chunk[-CHUNK_OVERLAP:]
                if len(current_chunk) > CHUNK_OVERLAP
                else current_chunk
            )

            current_chunk = overlap_text + paragraph + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [
        {
            "text": chunk,
            "source": source,
            "page": page,
            "category": category,
        }
        for chunk in chunks
        if chunk.strip()
    ]


def build_chunks_for_category(category: str) -> list[dict]:
    pages = load_pdfs_by_category(category)

    all_chunks = []

    for page in pages:
        all_chunks.extend(split_page_into_chunks(page))

    logger.info(f"{category}: created {len(all_chunks)} chunks.")

    return all_chunks


def load_all_categories() -> dict[str, list[dict]]:
    data = {}

    for category in CATEGORIES:
        data[category] = build_chunks_for_category(category)

    return data