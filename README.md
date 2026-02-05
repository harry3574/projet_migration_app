# Local Tool Suite — Architecture & Usage

This project provides a **simple web interface to host and run local tools and scripts**.
Its goal is to give standalone Python utilities a **shared home and UI**, without rewriting them as full web apps.

The system is intentionally minimal:

* Python backend
* HTML + JavaScript frontend
* Drop-in modules
* No framework on the frontend
* No complex plugin system

---

##  Project Goal

> Create a single interface for a collection of local tools and scripts, allowing each one to:
>
> * Expose a UI
> * Receive structured input
> * Run locally
> * Return structured output

Each tool lives as an **independent module**, with its own backend logic and frontend UI.

---

##  High-Level Overview

```
Browser
 └─ root.html (main shell)
     ├─ loads available modules
     ├─ displays sidebar
     └─ embeds module UI (iframe)
          ↓
FastAPI backend
 ├─ module registry (discovery)
 ├─ module UI loader
 ├─ execution endpoint
 └─ file upload helper
          ↓
Dynamic module import
 └─ module.run(payload)
```

---

##  Backend API Endpoints

### `GET /`

Serves the main application UI (`root.html`).

This is the only page the user directly navigates to.

---

### `GET /api/modules`

Returns the list of available modules discovered at startup.

**Response example:**

```json
[
  {
    "id": "excel_tools",
    "name": "Excel Tools",
    "description": "Utilities for Excel file processing",
    "entrypoint": "module.py",
    "ui": "ui.html"
  }
]
```

Used by the sidebar to display available tools.

---

### `GET /ui/{module_id}`

Returns the raw HTML UI of a module.

* Loaded inside an `<iframe>`
* Fully isolated from other modules
* No frontend framework required

Returns `404` if the module does not exist.

---

### `POST /api/run/{module_id}`

Executes a module.

* Accepts a JSON payload
* Dynamically imports the module
* Calls its `run(payload)` function
* Returns the result as JSON

**Example request:**

```json
{
  "file_path": "/tmp/data.xlsx"
}
```

**Errors**

* Any exception raised inside the module becomes an HTTP error response

---

### `POST /api/upload`

Utility endpoint for modules that need file input.

* Accepts a multipart file
* Saves it to a temporary directory
* Returns a safe local file path

**Response example:**

```json
{
  "path": "/tmp/local_tool_uploads/example.xlsx"
}
```

---

##  How Modules Work

Modules are **self-contained tool packages**.

Each module consists of:

* Metadata
* Backend logic
* Frontend UI

They are **automatically discovered** — no registration required.

---

##  Module Structure

```
modules/
└── my_module/
    ├── config.json
    ├── module.py
    └── ui.html
```

As long as this structure is respected, the module will appear in the UI.

---

##  `config.json` — Module Metadata

Defines how the module is identified and loaded.

```json
{
  "name": "My Tool",
  "id": "my_module",
  "description": "Does one specific thing",
  "entrypoint": "module.py",
  "ui": "ui.html"
}
```

### Required fields

| Field         | Description                           |
| ------------- | ------------------------------------- |
| `id`          | Unique identifier (also used in URLs) |
| `name`        | Display name in the sidebar           |
| `description` | Optional, informational               |
| `entrypoint`  | Python file containing `run()`        |
| `ui`          | HTML file served to the frontend      |

⚠️ The `id` must:

* Be unique
* Match the folder name
* Be import-safe (`a-z`, `_`, no spaces)

---

##  `module.py` — Backend Logic

Each module must expose **exactly one required function**:

```python
def run(payload: dict) -> dict:
    ...
```

### Characteristics

* `payload` comes directly from frontend JSON
* Return value must be JSON-serializable
* Exceptions are allowed (they become API errors)
* No FastAPI or web code inside modules

### Example

```python
def run(payload):
    value = payload["value"]
    return {"result": value * 2}
```

---

##  `ui.html` — Frontend UI

Each module defines its own UI.

* Plain HTML
* Plain JavaScript
* Communicates via `fetch()`
* Runs inside an iframe

Example API call:

```js
fetch("/api/run/my_module", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ value: 42 })
});
```

Modules are responsible for:

* Gathering input
* Calling the API
* Rendering output

---

##  Creating & Adding a New Module (Drag & Drop)

### Step-by-step

1. Create a new folder inside `modules/`
2. Add:

   * `config.json`
   * `module.py`
   * `ui.html`
3. Restart the application

That’s it.
The module will automatically appear in the sidebar.

No imports.
No registration.
No configuration changes.

---

##  Dependencies & Virtual Environment

Modules **do not manage their own dependencies**.

### Requirement

> Any Python library used by a module **must be installed manually** into the project’s `.venv`.

For example:

```bash
pip install pandas openpyxl
```

This is a **deliberate design choice**:

* Keeps the system simple
* Avoids dependency isolation complexity
* Fits local / personal tool usage

---

##  Design Philosophy

* Simple over clever
* Explicit over abstract
* Local tools, not SaaS
* UI as a convenience layer
* Scripts get a home, not a rewrite

This project is meant to:

* Organize scripts
* Make them usable by non-developers
* Provide just enough structure
* Stay hackable and extendable

---

##  Best Practices for Modules

* Validate inputs inside `run()`
* Keep modules stateless
* Avoid long-running blocking calls if possible
* Return structured data (not formatted strings)
* Treat modules as independent tools