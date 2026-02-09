import importlib

def execute(module_id: str, payload: dict, mode: str = "sync"):
    module_path = f"modules.{module_id}.module"
    module = importlib.import_module(module_path)

    if mode == "stream":
        if not hasattr(module, "stream"):
            raise ValueError(f"Module '{module_id}' does not support streaming")
        return module.stream(payload)

    if not hasattr(module, "run"):
        raise ValueError(f"Module '{module_id}' has no run()")

    return module.run(payload)
