import sys
import os
import json
import yaml

# Add the project root to the Python path so it can find 'services'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.gateway.main import app

def export():
    # Get the OpenAPI schema from FastAPI
    openapi_schema = app.openapi()
    
    # Save as JSON
    with open("docs/contracts/openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
        
    # Save as YAML
    with open("docs/contracts/openapi.yaml", "w") as f:
        yaml.dump(openapi_schema, f, sort_keys=False)
        
    print("✅ Successfully exported openapi.yaml and openapi.json")

if __name__ == "__main__":
    export()