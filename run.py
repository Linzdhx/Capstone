import os
import sys
import uvicorn

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    browser_host = "localhost" if host in ("0.0.0.0", "::") else host

    print("\n" + "=" * 60)
    print("  🚀 CVW Inventory Monitor - YOLOv8 Live System")
    print(f"  🌐 Interfaz Web: http://{browser_host}:{port}")
    print(f"  📚 Documentación API: http://{browser_host}:{port}/docs")
    print("  💡 En Windows, accede siempre por 'localhost' o '127.0.0.1'")
    print("     (los navegadores en Windows no aceptan '0.0.0.0')")
    print("=" * 60 + "\n")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=False
    )