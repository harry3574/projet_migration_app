import json
from pathlib import Path

MODULES_PATH = Path("modules")

class ModuleRegistry:
    def __init__(self):
        self.modules = {}
        self.errors = {}
        self.discover()

    def discover(self):
        if not MODULES_PATH.exists():
            return

        for folder in MODULES_PATH.iterdir():
            if not folder.is_dir():
                continue

            config = folder / "config.json"
            if not config.exists():
                continue

            try:
                raw = config.read_text(encoding="utf-8").strip()
                if not raw:
                    raise ValueError("config.json is empty")

                meta = json.loads(raw)

                module_id = meta.get("id")
                if not module_id:
                    raise ValueError("Missing 'id' in config.json")

                self.modules[module_id] = {
                    "path": folder,
                    "meta": meta
                }

            except Exception as e:
                self.errors[folder.name] = str(e)

    def list_errors(self):
        return self.errors

    def list_modules(self):
        return [m["meta"] for m in self.modules.values()]

    def load_ui(self, module_id):
        module = self.modules[module_id]
        return (module["path"] / module["meta"]["ui"]).read_text()

registry = ModuleRegistry()
