"""REST endpointy pro nahrávání, stahování a mazání fotografii lokácí."""

import mimetypes
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.repositories.photos_repository import PhotosRepository
from backend.routes.helpers import get_current_user_id

photos_bp = Blueprint("photos", __name__)

ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PHOTO_EXTENSION_ALIASES = {
    ".jpg": {".jpg", ".jpeg"},
    ".jpeg": {".jpg", ".jpeg"},
    ".png": {".png"},
    ".webp": {".webp"},
    ".gif": {".gif"},
}
PHOTO_HEADER_BYTES = 32


@photos_bp.get("/<int:location_id>/photos")
def list_location_photos(location_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    photos = _photos_repository().list_for_location(user_id, location_id)
    if photos is None:
        return jsonify({"error": "Lokace nebyla nalezena."}), 404

    return jsonify({"photos": photos})


@photos_bp.post("/<int:location_id>/photos")
def upload_location_photo(location_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    repository = _photos_repository()
    if not repository.location_belongs_to_user(user_id, location_id):
        return jsonify({"error": "Lokace nebyla nalezena."}), 404

    uploaded_file = request.files.get("photo")
    try:
        original_filename, extension = _validate_uploaded_photo(uploaded_file)
    except PhotoValidationError as exc:
        return jsonify({"error": exc.message}), 400

    relative_path = f"{user_id}/{location_id}/{uuid4().hex}{extension}"
    absolute_path = _safe_upload_path(relative_path)
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    uploaded_file.save(absolute_path)

    photo = repository.create_for_location(
        user_id=user_id,
        location_id=location_id,
        file_path=relative_path,
        original_filename=original_filename,
    )
    if photo is None:
        absolute_path.unlink(missing_ok=True)
        return jsonify({"error": "Lokace nebyla nalezena."}), 404

    return jsonify({"photo": photo}), 201


@photos_bp.get("/<int:location_id>/photos/<int:photo_id>/file")
def get_location_photo_file(location_id: int, photo_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    photo = _photos_repository().get_for_user(user_id, location_id, photo_id)
    if photo is None:
        return jsonify({"error": "Fotka nebyla nalezena."}), 404

    absolute_path = _safe_upload_path(photo["file_path"])
    if not absolute_path.is_file():
        return jsonify({"error": "Soubor fotky nebyl nalezen."}), 404

    mimetype = mimetypes.guess_type(photo["original_filename"])[0] or "application/octet-stream"
    return send_file(
        absolute_path,
        mimetype=mimetype,
        download_name=photo["original_filename"],
        conditional=True,
    )


@photos_bp.delete("/<int:location_id>/photos/<int:photo_id>")
def delete_location_photo(location_id: int, photo_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    photo = _photos_repository().delete_for_user(user_id, location_id, photo_id)
    if photo is None:
        return jsonify({"error": "Fotka nebyla nalezena."}), 404

    _safe_upload_path(photo["file_path"]).unlink(missing_ok=True)
    return "", 204


class PhotoValidationError(Exception):
    """Vyvolatá funkcí :func:`_validate_uploaded_photo` při selhání validace nahrávaného souboru."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message



def _photos_repository() -> PhotosRepository:
    return PhotosRepository(current_app.extensions["database"])


def _validate_uploaded_photo(uploaded_file: FileStorage | None) -> tuple[str, str]:
    """Zvaliduje multipart upload a vrátí ``(původní_název, přípona)``.

    Kontroluje MIME typ z požadavku a samostatně čte magic bytes ze začátku
    souboru, aby ověřila, že přípona odpovídá skutečnému formátu.

    Raises:
        PhotoValidationError: Při jakémkoli selhání validace.
    """
    if uploaded_file is None or not uploaded_file.filename:
        raise PhotoValidationError("Vyber fotku k nahrání.")

    original_filename = secure_filename(uploaded_file.filename)
    if not original_filename:
        raise PhotoValidationError("Název souboru není platný.")

    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        raise PhotoValidationError("Podporované formáty jsou JPG, PNG, WebP a GIF.")

    if uploaded_file.mimetype and not uploaded_file.mimetype.startswith("image/"):
        raise PhotoValidationError("Soubor musí být obrázek.")

    detected_extension = _detect_photo_extension(uploaded_file)
    if detected_extension is None:
        raise PhotoValidationError("Soubor musí být platný obrázek.")

    if extension not in PHOTO_EXTENSION_ALIASES[detected_extension]:
        raise PhotoValidationError("Přípona souboru neodpovídá obsahu obrázku.")

    return original_filename, extension


def _detect_photo_extension(uploaded_file: FileStorage) -> str | None:
    """Detekuje formát obrázku na základě magic bytes na začátku streamu.

    Pozice ve streamu je po načtení obnovena, aby bylo možné soubor následně uložit.
    Vrací normalizovanou příponu (např. ``".jpg"``), nebo ``None`` pro neznámé formáty.
    """
    stream = uploaded_file.stream
    original_position = stream.tell()
    header = stream.read(PHOTO_HEADER_BYTES)
    stream.seek(original_position)

    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    return None


def _safe_upload_path(relative_path: str) -> Path:
    """Rozliší *relative_path* vůči kořenému adresáři uploadů a ověří, že v něm zůstává.

    Raises:
        PhotoValidationError: Při pokusu o path-traversal útoky.
    """
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    absolute_path = (upload_root / relative_path).resolve()
    if upload_root not in absolute_path.parents:
        raise PhotoValidationError("Cesta k souboru není platná.")
    return absolute_path
