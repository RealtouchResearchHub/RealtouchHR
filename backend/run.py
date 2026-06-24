import sys
print("Importing server...", flush=True)
try:
    from server import app
    print("Import OK", flush=True)
except Exception as e:
    print(f"IMPORT ERROR: {e}", flush=True)
    sys.exit(1)

import uvicorn
print("Starting uvicorn...", flush=True)
try:
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
except Exception as e:
    print(f"STARTUP ERROR: {e}", flush=True)
    sys.exit(1)
