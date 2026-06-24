from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from config import PIPELINE_API_KEY
import pipeline as _pipeline

app = FastAPI(title="Lead Gen Pipeline")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(key: str = Security(_api_key_header)):
    if key != PIPELINE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return key


@app.post("/run")
def trigger_run(background_tasks: BackgroundTasks, _: str = Depends(_require_api_key)):
    """Trigger a pipeline run in the background."""
    if _pipeline.last_run.get("status") == "running":
        return {"status": "already_running"}
    _pipeline.last_run["status"] = "running"
    background_tasks.add_task(_pipeline.run_pipeline)
    return {"status": "started"}


@app.get("/status")
def get_status():
    """Return the last run's result."""
    return _pipeline.last_run or {"status": "no_runs_yet"}
