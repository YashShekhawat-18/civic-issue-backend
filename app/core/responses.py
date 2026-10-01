from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "Success", data=None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"success": True, "message": message, "data": data or {}}),
    )


def error_response(status_code: int, message: str, errors=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"success": False, "message": message, "errors": errors or []}),
    )