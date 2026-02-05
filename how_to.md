python.exe
│
├── main.py                 # Entry point
├── app/
│   ├── server.py           # FastAPI setup
│   ├── registry.py         # Module discovery & metadata
│   ├── executor.py         # Task execution layer
│   └── models.py           # Shared dataclasses / schemas
│
├── modules/
│   ├── excel_tools/
│   │   ├── module.py
│   │   ├── ui.html
│   │   └── config.json
│   │
│   └── address_check/
│       ├── module.py
│       ├── ui.html
│       └── config.json
│
└── venv/
