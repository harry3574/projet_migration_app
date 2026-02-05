import tempfile
import uuid
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.registry import registry
from app.executor import execute

#AAAAA

app = FastAPI()

ROOT_UI = Path("app/ui/root.html")


@app.get("/")
def root_ui():
    return HTMLResponse(
        content=ROOT_UI.read_text(encoding="utf-8"),
        media_type="text/html; charset=utf-8"
    )

@app.get("/api/modules")
def list_modules():
    return registry.list_modules()


@app.get("/ui/{module_id}")
def module_ui(module_id: str):
    try:
        html = registry.load_ui(module_id)
        return HTMLResponse(
            content=html,
            media_type="text/html; charset=utf-8"
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Module not found")


@app.post("/api/run/{module_id}")
def run_module(module_id: str, payload: dict):
    try:
        return execute(module_id, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

UPLOAD_DIR = Path(tempfile.gettempdir()) / "local_tool_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(upload: UploadFile) -> str:
    if upload.filename:
        return Path(upload.filename).name  # strips directories
    return f"upload_{uuid.uuid4().hex}"


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = safe_filename(file)
    target = UPLOAD_DIR / filename

    try:
        content = await file.read()
        target.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"path": str(target)}
