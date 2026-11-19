#!/usr/bin/env bash
# Script de auditoría de seguridad para CVW Inventory Monitor
# Ejecuta Bandit (análisis estático de código) y pip-audit (vulnerabilidades en dependencias)

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================================="
echo "  1. AUDITORIA ESTATICA DE CODIGO BACKEND (BANDIT)"
echo "=========================================================="
bandit -r backend/ -x backend/tests -v

echo ""
echo "=========================================================="
echo "  2. AUDITORIA DE DEPENDENCIAS PYTHON (PIP-AUDIT)"
echo "=========================================================="
pip-audit -r requirements.txt

echo ""
echo "Auditoría de seguridad completada."

