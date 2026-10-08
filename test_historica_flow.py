import requests
import cv2
import numpy as np
import time
from pathlib import Path
from backend.app.core.config import BASE_DIR

BASE_URL = 'http://localhost:8000'

def run_tests():
    print("==================================================")
    print("  EJECUTANDO PRUEBAS DEL NUEVO FLUJO /historica   ")
    print("==================================================")

    # 1. Verificar estado inactivo inicial
    r = requests.get(f'{BASE_URL}/api/stock/dashboard')
    dash = r.json()
    print('1. Estado Inactivo Inicial:')
    print(f'   is_active = {dash.get("is_active")} | total_aisles = {dash.get("total_aisles")}')
    assert dash.get("is_active") is False, "El Dashboard debe iniciar inactivo si /historica está vacía"

    # 2. Carga de imagen sin fallas -> Descartada
    clean_img = np.full((480, 640, 3), 180, dtype=np.uint8)
    _, clean_buf = cv2.imencode('.jpg', clean_img)
    files = [('files', ('estanteria_completa.jpg', clean_buf.tobytes(), 'image/jpeg'))]
    r = requests.post(f'{BASE_URL}/api/stock/upload', files=files)
    up_res = r.json()
    print('2. Carga de imagen sin faltantes:')
    print(f'   Total analizadas: {up_res["total_analyzed"]}')
    print(f'   Fallas detectadas: {up_res["faults_detected"]}')
    print(f'   Descartadas: {up_res["discarded_clean"]}')
    print(f'   Dashboard activo: {up_res["dashboard_active"]}')
    assert up_res['faults_detected'] == 0
    assert up_res['discarded_clean'] == 1
    assert up_res['dashboard_active'] is False

    # 3. Carga y almacenamiento en /historica
    hist_dir = BASE_DIR / 'historica'
    hist_dir.mkdir(parents=True, exist_ok=True)
    img1_path = hist_dir / 'gondola_lacteos.jpg'
    img2_path = hist_dir / 'gondola_panaderia.jpg'

    cv2.imwrite(str(img1_path), np.zeros((480, 640, 3), dtype=np.uint8))
    time.sleep(0.05)
    cv2.imwrite(str(img2_path), np.zeros((480, 640, 3), dtype=np.uint8))

    r = requests.get(f'{BASE_URL}/api/stock/dashboard')
    dash = r.json()
    print('3. Activación por Faltantes en /historica:')
    print(f'   is_active = {dash.get("is_active")} | total_aisles = {dash.get("total_aisles")}')
    for a in dash.get('aisles', []):
        print(f'   -> {a["display_name"]} | Archivo: {a["filename"]} | Severidad: {a["severity_info"]["severity"]}')
    assert dash.get("is_active") is True
    assert dash.get("total_aisles") == 2
    assert dash['aisles'][0]['display_name'] == 'Pasillo 1'
    assert dash['aisles'][1]['display_name'] == 'Pasillo 2'

    # 4. Resolver Pasillo 1 -> Pasillo 2 pasa automáticamente a ser Pasillo 1
    file_to_resolve = dash['aisles'][0]['filename']
    print(f'4. Resolviendo falla de Pasillo 1 ({file_to_resolve})...')
    r = requests.post(f'{BASE_URL}/api/stock/historica/{file_to_resolve}/resolve')
    res_data = r.json()
    print(f'   Respuesta de resolución: {res_data.get("message")}')

    r = requests.get(f'{BASE_URL}/api/stock/dashboard')
    dash_reordered = r.json()
    print('   Estado tras resolución:')
    print(f'   Pasillos restantes: {dash_reordered.get("total_aisles")}')
    for a in dash_reordered.get('aisles', []):
        print(f'   -> {a["display_name"]} | Archivo: {a["filename"]}')

    assert dash_reordered.get("total_aisles") == 1
    assert dash_reordered['aisles'][0]['display_name'] == 'Pasillo 1', "El antiguo Pasillo 2 DEBE ser ahora Pasillo 1"
    assert dash_reordered['aisles'][0]['filename'] == 'gondola_panaderia.jpg'
    print("   -> ÉXITO: El antiguo Pasillo 2 pasó a ser automáticamente Pasillo 1!")

    # 5. Resolver el pasillo restante -> El Dashboard vuelve al estado inactivo
    last_file = dash_reordered['aisles'][0]['filename']
    print(f'5. Resolviendo último pasillo ({last_file})...')
    requests.post(f'{BASE_URL}/api/stock/historica/{last_file}/resolve')

    r = requests.get(f'{BASE_URL}/api/stock/dashboard')
    dash_final = r.json()
    print('   Estado final con /historica vacía:')
    print(f'   is_active = {dash_final.get("is_active")} | total_aisles = {dash_final.get("total_aisles")}')
    assert dash_final.get("is_active") is False
    print("   -> ÉXITO: El Dashboard vuelve a quedar inactivo correctamente.")

    print("\n==================================================")
    print("   TODAS LAS PRUEBAS DEL NUEVO FLUJO PASARON 100% ")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
