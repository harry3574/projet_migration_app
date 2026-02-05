from typing import Any, Dict
import pandas as pd

def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main execution entrypoint for the module.
    Payload comes from UI.
    """
    file_path = payload["file_path"]

    df = pd.read_excel(file_path)

    return {
        "rows": len(df),
        "columns": list(df.columns),
        "preview": df.head(5).to_dict(orient="records")
    }
