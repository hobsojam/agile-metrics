"""Print the backend's OpenAPI schema as JSON, for the frontend's generate-types script.

Usage: uv run python scripts/export_openapi_schema.py > frontend/openapi.json
"""

import json

from agile_metrics.web import app

print(json.dumps(app.openapi()))
