# Definition of Done (DoD) — Computer Vision Walmart (CVW)

> **Fuentes:** requisitos no funcionales del ERS v4 (RNF-01 a RNF-10), evidencias y observaciones del Plan de Trabajo de la Guía 1.5, y prácticas ya presentes en el repositorio (pruebas con pytest, README).
> Los criterios se derivan de esos documentos. **El equipo debe revisarlos y confirmarlos.**

Un ítem del Product Backlog se considera **terminado** cuando cumple todos los criterios que le aplican:

## 1. Criterios generales (todo ítem)

- [ ] Cumple la descripción del requisito funcional asociado (RF) del ERS.
- [ ] El código está en el repositorio del equipo, en la rama `main`, mediante Pull Request.
- [ ] El código está organizado de forma modular en VS Code (RNF-09).
- [ ] No hay claves ni credenciales en el código; se usan variables de entorno o secretos (RNF-05).
- [ ] La documentación afectada está actualizada (README, ERS o el artefacto correspondiente).
- [ ] Fue revisado por al menos otro integrante del equipo.

## 2. Ítems de datos y modelo (Sprints 1 y 2)

- [ ] La partición del dataset y el entrenamiento usan semilla fija (42) y la validación se hace sobre imágenes no aumentadas (RNF-07).
- [ ] Se reportan Precisión, Recall, mAP50 y mAP50-95, globales y por clase (RF-06).
- [ ] La nueva versión del modelo iguala o supera la línea base v1: mAP50 global 72,8 % y mAP50 missing 59,9 % (RNF-02).
- [ ] El tiempo de inferencia por imagen es menor a 5 s (RNF-01).
- [ ] Los pesos `best.pt` quedan disponibles para su uso fuera de Colab (RF-12).

## 3. Ítems de software (Sprints 3, 4 y 5)

- [ ] Tiene pruebas automatizadas con pytest y todas pasan.
- [ ] Una imagen que no se puede leer se omite sin detener el lote (RNF-06).
- [ ] El cálculo del semáforo respeta los umbrales: Verde 100–41 %, Amarillo 40–21 %, Rojo 20–0 %.
- [ ] El sistema no accede a cámaras, CCTV ni a la red corporativa (RNF-03), ni procesa datos personales (RNF-04).

## 4. Criterios de un sprint terminado

- [ ] Se cumplió el objetivo del sprint (ver `Sprint_Backlog.md`).
- [ ] Se generó la evidencia comprometida para ese sprint (Guía 1.5, sección 6).
- [ ] Se presentó el avance al docente o al cliente.
- [ ] Se realizó la retrospectiva del sprint (qué funcionó, qué no y qué mejorar) y quedó registrada en `Retrospectivas.md`.