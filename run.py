import os
import sys
import uvicorn

if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))

    print("\n" + "=" * 60)
    print("  🚀 CVW Inventory Monitor - YOLOv8 Live System")
    print(f"  🌐 Interfaz Web: http://localhost:{port}")
    print(f"  📚 Documentación API: http://localhost:{port}/docs")
    print("=" * 60 + "\n")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=False
    )
