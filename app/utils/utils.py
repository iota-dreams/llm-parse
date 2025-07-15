import re
from pathlib import Path

from fastapi import HTTPException


def validate_file_path(file_path: str, allowed_root: str = ".") -> str:
    """
    Validates and sanitizes a user-provided file path to prevent traversal, injection,
    or access outside allowed_root.

    Parameters
    ----------
    file_path : str
        User-provided file path.
    allowed_root : str
        Base directory where access is permitted.

    Returns
    -------
    str
        Absolute and validated safe path.

    Raises
    ------
    HTTPException
        If the path is unsafe or not allowed.
    """
    # Block obvious command injection characters
    if re.search(r"[;&|<>`]", file_path):
        raise HTTPException(status_code=400, detail="Unsafe characters in file path.")

    # Normalize path and check for traversal
    path_obj = Path(file_path).expanduser().resolve()

    allowed_root_path = Path(allowed_root).resolve()
    if not str(path_obj).startswith(str(allowed_root_path)):
        raise HTTPException(
            status_code=403,
            detail="Access to the specified path is not permitted.",
        )

    # Check extension and existence
    if not path_obj.is_file():
        raise HTTPException(status_code=400, detail="Provided file path is not valid.")

    if not path_obj.suffix.lower() == ".pdf":
        raise HTTPException(status_code=400, detail="Only .pdf files are supported.")

    return str(path_obj)
