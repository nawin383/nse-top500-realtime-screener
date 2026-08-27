"""Enhance OpenAPI: tags, examples, sorted paths. Import in main.py."""
from fastapi import FastAPI

TAGS = [
    {"name": "health", "description": "Liveness / readiness probes"},
    {"name": "market", "description": "Market status & overview"},
    {"name": "stocks", "description": "Universe & per-symbol detail"},
    {"name": "screener", "description": "Ranked screeners (gainers, volume, breakout...)"},
    {"name": "alerts", "description": "Real-time alerts"},
    {"name": "options", "description": "Options chain & Greeks"},
    {"name": "institutional", "description": "FII/DII & sector flows"},
    {"name": "watchlists", "description": "User watchlists"},
    {"name": "webhooks", "description": "Webhook subscriptions"},
]

EXAMPLES = {
    "/api/stocks": {"search": "RELIANCE", "sector": "Energy", "limit": 20},
    "/api/screener/{name}": {"name": "gainers", "limit": 20},
}

def enhance_openapi(app: FastAPI) -> None:
    if app.openapi_schema:
        return
    orig = app.openapi

    def custom():
        if app.openapi_schema:
            return app.openapi_schema
        schema = orig()
        schema["tags"] = TAGS
        # ensure examples
        for path, methods in schema.get("paths", {}).items():
            for m, op in methods.items():
                if path in EXAMPLES and "parameters" in op:
                    for p in op["parameters"]:
                        if p["name"] in EXAMPLES[path]:
                            p["example"] = EXAMPLES[path][p["name"]]
        # sort paths for /docs readability
        schema["paths"] = dict(sorted(schema["paths"].items()))
        app.openapi_schema = schema
        return schema

    app.openapi = custom  # type: ignore
