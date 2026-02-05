import importlib.util

def execute(module_id: str, payload: dict):
    module_path = f"modules.{module_id}.module"
    module = importlib.import_module(module_path)
    return module.run(payload)
