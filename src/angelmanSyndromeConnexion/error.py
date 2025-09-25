class AppError(Exception):
    """Base des erreurs applicatives (validation, règles métier, etc.)."""
    code = "app_error"      # identifiant court dans la réponse JSON
    http_status = 400       # statut HTTP par défaut

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}

# --- Spécifiques ---
class MissingFieldError(AppError):
    code = "missing_field"
    http_status = 400

class BadDateFormatError(AppError):
    code = "bad_date_format"
    http_status = 422

class FutureDateError(AppError):
    code = "future_date"
    http_status = 400

class PhotoTooLargeError(AppError):
    code = "photo_too_large"
    http_status = 413  # Payload Too Large

class InvalidMimeTypeError(AppError):
    code = "invalid_mime"
    http_status = 415  # Unsupported Media Type

class DuplicateEmailError(AppError):
    code = "duplicate_email"
    http_status = 409  # Conflict