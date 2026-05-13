import io
import os
import json
import tempfile
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from config import logger, CATEGORIES


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():

    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account.json")

    if credentials_json:
        logger.info("Using Google service account from Railway variable.")

        service_account_info = json.loads(credentials_json)

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES,
        )

    else:
        logger.info(f"Using Google service account file: {credentials_path}")

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
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    files = result.get("files", [])

    if not files:
        logger.warning(f"Drive folder not found: {folder_name}")
        return None

    folder_id = files[0]["id"]
    logger.info(f"Drive folder found: {folder_name} -> {folder_id}")

    return folder_id


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
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    files = result.get("files", [])

    logger.info(f"Found {len(files)} PDF files in Drive folder.")

    return files

def safe_filename(filename: str) -> str:

    return filename.replace("/", "_").replace("\\", "_")


def download_pdf_to_temp(service, file_id: str, file_name: str) -> Path:

    request = service.files().get_media(fileId=file_id)

    temp_dir = Path(tempfile.gettempdir()) / "ai_sict_bot_drive"
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_path = temp_dir / safe_filename(file_name)

    with io.FileIO(file_path, "wb") as file_handle:
        downloader = MediaIoBaseDownload(file_handle, request)

        done = False

        while not done:
            status, done = downloader.next_chunk()

            if status:
                logger.info(
                    f"Downloading {file_name}: {int(status.progress() * 100)}%"
                )

    logger.info(f"Downloaded Drive PDF: {file_name}")

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
        logger.warning(f"No Drive category folder found for: {category}")
        return []

    pdf_files = list_pdfs_in_folder(service, category_folder_id)

    downloaded_paths = []

    for pdf in pdf_files:
        file_id = pdf["id"]
        file_name = pdf["name"]

        logger.info(f"Downloading Drive PDF: {category}/{file_name}")

        try:
            file_path = download_pdf_to_temp(
                service=service,
                file_id=file_id,
                file_name=file_name,
            )

            downloaded_paths.append(file_path)

        except Exception as e:
            logger.error(f"Failed to download {file_name}: {e}", exc_info=True)

    logger.info(
        f"{category}: downloaded {len(downloaded_paths)} PDFs from Google Drive."
    )

    return downloaded_paths