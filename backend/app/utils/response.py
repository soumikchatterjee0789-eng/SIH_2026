"""
Standard API response format (PRD Section 22).

Every endpoint returns:
    {"success": true, "data": {...}, "message": "..."}
or:
    {"success": false, "data": null, "message": "...", "error_code": "..."}

This is important because frontend and backend are developed independently.
"""
from typing import Any


def success_response(data: Any = None, message: str = "Request successful") -> dict:
    return {"success": True, "data": data, "message": message}


def error_response(message: str, error_code: str, data: Any = None) -> dict:
    return {"success": False, "data": data, "message": message, "error_code": error_code}
