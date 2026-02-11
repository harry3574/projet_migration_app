import importlib

def execute(module_id: str, payload: dict, mode: str = "sync", format: str | None = None):
    module = importlib.import_module(f"modules.{module_id}.module")

    if mode == "stream":
        if not hasattr(module, "stream"):
            raise ValueError("Streaming not supported")
        return module.stream(payload)

    if mode == "download":
        if not hasattr(module, "download"):
            raise ValueError("Download not supported")
        return module.download(payload, format=format)

    return module.run(payload)
