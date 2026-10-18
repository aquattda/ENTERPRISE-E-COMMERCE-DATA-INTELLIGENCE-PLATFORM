"""Small, stateless source connection workspace for Vercel."""

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from apps.vercel.sources import SourceError, SourceRequest, read_source

ASSETS = Path(__file__).resolve().parent / "static"
app = FastAPI(title="CDIP · Kết nối dữ liệu", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")


@app.get("/")
def home():
    return FileResponse(ASSETS / "index.html")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "source-connections", "storage": "none"}


@app.post("/api/sources/read")
def read(body: SourceRequest):
    try:
        return read_source(body)
    except SourceError as error:
        return JSONResponse({"error": str(error)}, status_code=400)


@app.get("/api/sources/example")
def example():
    rows = [
        {"id": "01", "name": "Bản ghi thử A", "status": "active"},
        {"id": "02", "name": "Bản ghi thử B", "status": "active"},
        {"id": "03", "name": "Bản ghi thử C", "status": "inactive"},
    ]
    return {"example": True, "items": rows}


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # Never echo submitted input: it can contain access tokens or app secrets.
    return JSONResponse(
        {"error": "Thông tin kết nối chưa hợp lệ. Kiểm tra các trường đã nhập."}, status_code=422
    )


@app.middleware("http")
async def guard(request: Request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if request.headers.get("x-cdip-request") != "1" or (
            origin and urlsplit(origin).netloc != request.headers.get("host")
        ):
            return JSONResponse(
                {"error": "Yêu cầu không hợp lệ. Mở lại trang kết nối rồi thử lại."},
                status_code=403,
            )
        payload = await request.body()
        if len(payload) > 32000:
            return JSONResponse(
                {"error": "Thông tin yêu cầu quá dài (tối đa 32 KB)."}, status_code=413
            )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors "
        "'none'; base-uri 'self'; form-action 'self'"
    )
    return response
