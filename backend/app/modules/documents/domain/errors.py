class DocumentError(Exception):
    code = "document_error"


class InvalidDocumentTitleError(DocumentError):
    code = "invalid_document_title"


class InvalidDocumentFilenameError(DocumentError):
    code = "invalid_document_filename"


class InvalidPdfError(DocumentError):
    code = "invalid_pdf"


class DuplicateDocumentError(DocumentError):
    code = "duplicate_document"
