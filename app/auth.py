import os
import secrets
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

security = HTTPBasic()
_KEY = os.getenv("SECURITY_KEY", "")


def verify_docs_access(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    valid = secrets.compare_digest(credentials.password.encode(), _KEY.encode())
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
