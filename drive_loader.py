import io
import os
import tempfile
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from config import logger, CATEGORIES


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS тохируулагдаагүй байна.")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES,
    )

    return build("drive", "v3", credentials=credentials)


def find_folder_id(service, parent_folder_id: str, folder_name: str) -> str | None:
    query = (
        f"'{parent_folder_id}' in parents and "
        f"name = '{folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )

    result = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=10,
    ).execute()

    files = result.get("files", [])

    if not files:
        logger.warning(f"Drive folder not found: {folder_name}")
        return None

    return files[0]["id"]


def list_pdfs_in_folder(service, folder_id: str) -> list[dict]:
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType = 'application/pdf' and "
        f"trashed = false"
    )

    result = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=100,
    ).execute()

    return result.get("files", [])


def download_pdf_to_temp(service, file_id: str, file_name: str) -> Path:
    request = service.files().get_media(fileId=file_id)

    temp_dir = Path(tempfile.gettempdir()) / "ai_sict_bot_drive"
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_path = temp_dir / file_name

    with io.FileIO(file_path, "wb") as file_handle:
        downloader = MediaIoBaseDownload(file_handle, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

    return file_path


def download_drive_pdfs_by_category(category: str) -> list[Path]:
    if category not in CATEGORIES:
        logger.warning(f"Unknown category: {category}")
        return []

    root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")

    if not root_folder_id:
        raise ValueError("GOOGLE_DRIVE_ROOT_FOLDER_ID тохируулагдаагүй байна.")

    service = get_drive_service()

    category_folder_id = find_folder_id(
        service=service,
        parent_folder_id=root_folder_id,
        folder_name=category,
    )

    if not category_folder_id:
        return []

    pdf_files = list_pdfs_in_folder(service, category_folder_id)

    downloaded_paths = []

    for pdf in pdf_files:
        logger.info(f"Downloading Drive PDF: {category}/{pdf['name']}")

        file_path = download_pdf_to_temp(
            service=service,
            file_id=pdf["id"],
            file_name=pdf["name"],
        )

        downloaded_paths.append(file_path)

    logger.info(f"{category}: downloaded {len(downloaded_paths)} PDFs from Drive.")

    return downloaded_paths