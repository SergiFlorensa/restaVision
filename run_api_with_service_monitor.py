#!/usr/bin/env python
"""
Script para iniciar el servidor API con TableServiceMonitor integrado.
Ejecuta: python run_api_with_service_monitor.py
"""

import sys
from pathlib import Path

import uvicorn

# Asegurar que el proyecto está en el path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    print("\n" + "=" * 70)
    print("🚀 RestaurIA - API con Análisis de Servicio de Mesa")
    print("=" * 70 + "\n")

    print("📚 Documentación:")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc\n")

    print("🎥 Endpoints de Monitoreo de Mesa:")
    print("   - Status: GET /api/v1/demo/table-service/status")
    print("   - Stream MJPEG: GET /api/v1/demo/table-service/stream")
    print("   - Análisis JSON: POST /api/v1/demo/table-service/analyze\n")

    print("🎯 Otros Endpoints:")
    print("   - Cámaras: GET /api/v1/cameras")
    print("   - Zonas: GET /api/v1/zones")
    print("   - Mesas: GET /api/v1/tables")
    print("   - Sesiones: GET /api/v1/sessions")
    print("   - Eventos: GET /api/v1/events")
    print("   - Alertas: GET /api/v1/alerts\n")

    print("⏹️  Presiona Ctrl+C para detener el servidor.\n")
    print("=" * 70 + "\n")

    # Iniciar Uvicorn
    uvicorn.run(
        "apps.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
