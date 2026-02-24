import sys
import json
import importlib
import traceback

def main():
    try:
        raw = sys.stdin.read()
        req = json.loads(raw)

        module_id = req["module_id"]
        payload = req["payload"]
        mode = req.get("mode", "sync")
        format = req.get("format")

        module = importlib.import_module(f"modules.{module_id}.module")

        if mode == "download":
            result = module.download(payload, format=format)
        elif mode == "stream":
            raise RuntimeError("stream not supported via subprocess")
        else:
            result = module.run(payload)

        print(json.dumps({
            "success": True,
            "result": result
        }))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }))

if __name__ == "__main__":
    main()
