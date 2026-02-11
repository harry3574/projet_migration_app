import csv
import json
import math
from pathlib import Path
import re
import tempfile
import unicodedata
import uuid
import numpy as np
import pandas as pd
import requests
from typing import Any, Dict, List, TypedDict, Optional
from uuid import uuid4
from threading import Lock

_PROGRESS = {}
_PROGRESS_LOCK = Lock()

BAN_URL = "https://api-adresse.data.gouv.fr/search/"
PREVIEW_ROWS = 50

POSTCODE_RE = re.compile(r"^\d{5}$")
NUMBER_RE = re.compile(r"^\d+[a-zA-Z]?$")

POSTAL_ONLY_KEYWORDS = ["bp", "boite postale", "cedex", "cs"]

STREET_KEYWORDS = [
    "rue", "avenue", "av", "boulevard", "bd",
    "chemin", "route", "impasse", "allee",
    "place", "quai", "cours"
]

FIELD_LABELS = {
    "valid": "Adresse valide",
    "reason": "Raison",
    "postal_code": "Code postal",
    "city": "Ville",
    "country": "Pays",
    "confidence": "Confiance",
}

class AddressParts(TypedDict):
    number: Optional[str]
    street: Optional[str]
    postcode: Optional[str]
    city: Optional[str]
    mixed: List[str]

def is_postal_only(text: str) -> bool:
    t = normalize(text)
    return any(k in t for k in POSTAL_ONLY_KEYWORDS)

def normalize(text: str) -> str:
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def classify_column(series) -> str:
    sample = series.dropna().astype(str).head(20)

    scores = {
        "postcode": 0,
        "number": 0,
        "street": 0,
        "city": 0,
        "mixed": 0,
    }

    for v in sample:
        v = v.strip()
        nv = normalize(v)

        if POSTCODE_RE.match(v):
            scores["postcode"] += 1
        elif NUMBER_RE.match(v):
            scores["number"] += 1
        elif any(k in nv for k in STREET_KEYWORDS):
            scores["street"] += 1
        elif any(c.isdigit() for c in v):
            scores["mixed"] += 1
        else:
            scores["city"] += 1

    return max(scores.items(), key=lambda item: item[1])[0]


def build_address_candidates(parts: AddressParts) -> List[str]:
    candidates = []

    n = parts.get("number")
    s = parts.get("street")
    p = parts.get("postcode")
    c = parts.get("city")

    # Ideal French postal format
    if all([n, s, p, c]):
        candidates.append(f"{n} {s} {p} {c}")

    # Street + city + postcode
    if s and c and p:
        candidates.append(f"{s} {p} {c}")

    # Number + street
    if n and s:
        candidates.append(f"{n} {s}")

    # Known merged fields
    for m in parts.get("mixed", []):
        candidates.append(m)

    # Last resort: everything concatenated
    flat = " ".join(
        v for v in [n, s, p, c]
        if isinstance(v, str)
    )
    if flat:
        candidates.append(flat)

    # Deduplicate
    return list(dict.fromkeys(a.strip() for a in candidates if a.strip()))

def validate_with_ban(address: str) -> dict | None:
    params = {
        "q": address,
        "limit": 1
    }

    try:
        r = requests.get(BAN_URL, params=params, timeout=3)
        r.raise_for_status()
        data = r.json()

        if not data.get("features"):
            return None

        props = data["features"][0]["properties"]
        score = float(props.get("score", 0))
        has_number = bool(props.get("housenumber"))
        is_named_place = props.get("type") in ("poi", "place")


        is_valid = (
            props.get("score", 0) >= 0.8 and
            props.get("housenumber") and
            props.get("street") and
            props.get("postcode") and
            props.get("city")
        )

        return {
            "valid": bool(is_valid),
            "score": score,
            "label": props.get("label")  # normalized address
        }

    except requests.RequestException:
        return None


def explain_result(result: dict) -> str:
    if result["score"] is None:
        return "No match found"

    if result["score"] < 0.6:
        return "Address not recognized"

    if result["score"] < 0.8:
        return "Low confidence match"

    return "Missing delivery details"


def validate_row(row, column_types: Dict[str, str]) -> dict:
    parts: AddressParts = {
        "number": None,
        "street": None,
        "postcode": None,
        "city": None,
        "mixed": []
    }

    for col, col_type in column_types.items():
        value = str(row[col]).strip()
        if not value:
            continue

        if col_type in ("number", "street", "postcode", "city"):
            if parts[col_type] is None:
                parts[col_type] = value
            else:
                parts["mixed"].append(value)
        else:
            parts["mixed"].append(value)

    best_score = 0.0
    best_label = None

    for addr in build_address_candidates(parts):
        result = validate_with_ban(addr)
        if not result:
            continue

        if result["score"] > best_score:
            best_score = result["score"]
            best_label = result["label"]

        if result["valid"]:
            return {
                "valid": True,
                "score": result["score"],
                "address": result["label"],
                "reason": "Valid postal address"
            }

    return {
    "valid": False,
    "score": best_score if best_score > 0 else None,
    "address": best_label,
    "reason": explain_result({
        "score": best_score
    })
   }



def load_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    file_path = Path(payload["file_path"])

    df = pd.read_excel(file_path)

    preview = df.head(PREVIEW_ROWS).to_dict(orient="records")

    result = {
        "columns": list(df.columns),
        "preview": preview,
        "total_rows": int(len(df))
    }

    return sanitize_for_json(result)


def verify_addresses(payload: Dict[str, Any]) -> Dict[str, Any]:
    file_path = Path(payload["file_path"])
    selected_columns: List[str] = payload["columns"]

    df = pd.read_excel(file_path)

    column_types = {
        col: classify_column(df[col])
        for col in selected_columns
    }

    results = df.apply(
        lambda row: validate_row(row, column_types),
        axis=1
    )

    df_result = df[selected_columns].copy()
    df_result["valid"] = results.apply(lambda r: r["valid"])
    df_result["score"] = results.apply(lambda r: r["score"])
    df_result["normalized_address"] = results.apply(lambda r: r["address"])

    invalid = df_result[~df_result["valid"]]
    valid = df_result[df_result["valid"]]

    return {
        "checked": int(len(df_result)),
        "valid": int(valid.shape[0]),
        "invalid": int(invalid.shape[0]),
        "invalid_samples": invalid.head(20).to_dict(orient="records"),
        "valid_samples": valid.head(20).to_dict(orient="records")
    }

def stream(payload: Dict[str, Any]):
    file_path = Path(payload["file_path"])
    selected_columns = payload["columns"]

    df = pd.read_excel(file_path)
    total = len(df)

    job_id = uuid.uuid4().hex

    yield { "type": "started", "job_id": job_id }

    RESULTS_DIR = Path(tempfile.gettempdir()) / "module_results"
    RESULTS_DIR.mkdir(exist_ok=True)

    result_path = RESULTS_DIR / f"{job_id}.jsonl"

    column_types = {
        col: classify_column(df[col])
        for col in selected_columns
    }

    valid_count = 0
    invalid_count = 0
    valid_samples = []
    invalid_samples = []

    with result_path.open("a", encoding="utf-8-sig") as f:
        for idx, row in df.iterrows():
            result = validate_row(row, column_types)
            output = { **row.to_dict(), **result }

            f.write(json.dumps(output) + "\n")

            if result["valid"]:
                valid_count += 1
                if len(valid_samples) < 20:
                    valid_samples.append(output)
            else:
                invalid_count += 1
                if len(invalid_samples) < 20:
                    invalid_samples.append(output)

            yield {
                "type": "progress",
                "current": idx + 1, # type: ignore
                "total": total,
                "message": f"Validated {idx + 1} / {total}" # type: ignore
            }

    yield {
        "type": "done",
        "job_id": job_id,
        "checked": total,
        "valid": valid_count,
        "invalid": invalid_count,
        "valid_samples": valid_samples,
        "invalid_samples": invalid_samples
    }



def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")

    if action == "preview":
        return load_preview(payload)

    if action == "verify":
        return verify_addresses(payload)

    raise ValueError(f"Unknown action: {action}")

def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively convert Pandas / NumPy values into JSON-safe Python types.
    """
    if obj is None:
        return None

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if math.isnan(val) or math.isinf(val) else val

    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]

    return obj

def init_progress(total: int) -> str:
    job_id = str(uuid4())
    with _PROGRESS_LOCK:
        _PROGRESS[job_id] = {
            "total": total,
            "current": 0,
            "message": "Starting…",
            "done": False
        }
    return job_id


def update_progress(job_id: str, current: int, message: str = ""):
    with _PROGRESS_LOCK:
        if job_id in _PROGRESS:
            _PROGRESS[job_id]["current"] = current
            if message:
                _PROGRESS[job_id]["message"] = message


def finish_progress(job_id: str):
    with _PROGRESS_LOCK:
        if job_id in _PROGRESS:
            _PROGRESS[job_id]["done"] = True

def download(payload: Dict[str, Any], format: str | None = None):
    if format != "csv":
        raise ValueError("Unsupported format")

    job_id = payload.get("job_id")
    if not job_id:
        raise ValueError("Missing job_id")

    RESULTS_DIR = Path(tempfile.gettempdir()) / "module_results"
    source = RESULTS_DIR / f"{job_id}.jsonl"

    if not source.exists():
        raise ValueError("Results not found")

    fd, csv_path = tempfile.mkstemp(suffix=".csv")

    with source.open("r", encoding="utf-8-sig") as src, \
         open(fd, "w", newline="", encoding="utf-8-sig") as out:

        writer = None
        fieldnames = None

        for line in src:
            row = json.loads(line)

            # First row → define schema
            if fieldnames is None:
                fieldnames = list(row.keys())

                headers = [
                    FIELD_LABELS.get(name, name)
                    for name in fieldnames
                ]

                writer = csv.writer(out)
                writer.writerow(headers)

            # Write row values in the same order
            writer.writerow([ # type: ignore
                row.get(name, "")
                for name in fieldnames
            ])

    return {
        "path": csv_path,
        "filename": f"verified_addresses_{job_id}.csv",
        "media_type": "text/csv"
    }
