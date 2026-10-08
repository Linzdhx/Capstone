import unittest
import numpy as np
from backend.app.schemas.detection import DetectionItem
from backend.app.services.incident_service import (
    IncidentService, compute_severity, compute_stock_metrics
)

class TestInventoryStockSystem(unittest.TestCase):
    def setUp(self):
        self.service = IncidentService(confidence_threshold=0.5, duplicate_window_seconds=30.0)

    def test_case_1_no_missing(self):
        """Caso 1: Imagen sin faltantes -> No crear incidencia, no almacenar imagen."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [
            DetectionItem(class_id=1, class_name='product', confidence=0.92, box=[10, 10, 50, 50])
        ]
        inc = self.service.process_frame(detections=detections, frame=frame, location_id='GND-TEST-1')
        self.assertIsNone(inc, 'No debe crearse incidencia si no hay faltantes')

    def test_case_2_with_missing(self):
        """Caso 2: Imagen con missing -> Crear/actualizar incidencia, calcular métricas y severidad."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [
            DetectionItem(class_id=0, class_name='missing', confidence=0.88, box=[10, 10, 50, 50]),
            DetectionItem(class_id=1, class_name='product', confidence=0.91, box=[60, 10, 100, 50]),
            DetectionItem(class_id=1, class_name='product', confidence=0.95, box=[110, 10, 150, 50]),
        ]
        inc = self.service.process_frame(detections=detections, frame=frame, location_id='GND-TEST-2')
        self.assertIsNotNone(inc)
        self.assertEqual(inc.missing_count, 1)
        self.assertEqual(inc.expected_count, 3)
        self.assertEqual(inc.remaining_count, 2)
        # 1/3 = 33.33% -> CRITICAL (>20%)
        self.assertAlmostEqual(inc.missing_percentage, 33.33, places=1)
        self.assertEqual(inc.severity, 'CRITICAL')
        self.assertEqual(inc.status, 'ACTIVE')

    def test_case_3_deduplication(self):
        """Caso 3: Múltiples frames consecutivos con el mismo faltante -> No crear incidencias duplicadas."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [
            DetectionItem(class_id=0, class_name='missing', confidence=0.88, box=[10, 10, 50, 50])
        ]
        inc1 = self.service.process_frame(detections=detections, frame=frame, location_id='GND-TEST-3')
        inc2 = self.service.process_frame(detections=detections, frame=frame, location_id='GND-TEST-3')
        self.assertEqual(inc1.id, inc2.id, 'Las llamadas consecutivas deben actualizar la misma incidencia')

    def test_case_4_resolve_and_reorder(self):
        """Caso 4: Se resuelve Pasillo 1 -> El siguiente pasillo puede ocupar display_order = 1, location_id original permanece intacto, histórico intacto."""
        loc_a = self.service.create_location('GND-ORIG-1', 'Pasillo 1')
        loc_b = self.service.create_location('GND-ORIG-2', 'Pasillo 2')

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        inc_a = self.service.process_frame(
            [DetectionItem(class_id=0, class_name='missing', confidence=0.85, box=[1,1,2,2])],
            frame, location_id='GND-ORIG-1'
        )
        inc_b = self.service.process_frame(
            [DetectionItem(class_id=0, class_name='missing', confidence=0.85, box=[1,1,2,2])],
            frame, location_id='GND-ORIG-2'
        )

        # Resolver incidencia de GND-ORIG-1
        resolved_a = self.service.resolve_incident(inc_a.id)
        self.assertEqual(resolved_a.status, 'RESOLVED')
        self.assertEqual(resolved_a.location_id, 'GND-ORIG-1', 'location_id histórico NUNCA debe cambiar')

        # Verificar histórico
        history = self.service.get_incidents()
        hist_a = next(i for i in history if i.id == inc_a.id)
        self.assertEqual(hist_a.location_id, 'GND-ORIG-1')
        self.assertEqual(hist_a.status, 'RESOLVED')

    def test_case_5_critical_severity(self):
        """Caso 5: Faltante = 25% -> CRITICAL, Urgente, Reposición total."""
        sev = compute_severity(25.0, 'Pasillo 1')
        self.assertEqual(sev.severity, 'CRITICAL')
        self.assertEqual(sev.status, 'Urgente')
        self.assertEqual(sev.action, 'Reposición total')
        self.assertIn('Atención inmediata: El Pasillo 1 requiere reposición total', sev.message)

    def test_case_6_moderate_severity(self):
        """Caso 6: Faltante = 15% -> MODERATE, Atención Rápida, Reposición moderada."""
        sev = compute_severity(15.0, 'Pasillo 2')
        self.assertEqual(sev.severity, 'MODERATE')
        self.assertEqual(sev.status, 'Atención Rápida')
        self.assertEqual(sev.action, 'Reposición moderada')
        self.assertIn('Aviso: El Pasillo 2 requiere reposición parcial', sev.message)

    def test_case_7_low_severity(self):
        """Caso 7: Faltante = 5% -> LOW, Prevención, Reposición preventiva."""
        sev = compute_severity(5.0, 'Pasillo 3')
        self.assertEqual(sev.severity, 'LOW')
        self.assertEqual(sev.status, 'Prevención')
        self.assertEqual(sev.action, 'Reposición preventiva')
        self.assertIn('Aviso preventivo: El Pasillo 3 presenta un nivel bajo de faltantes', sev.message)

    def test_case_8_send_alert(self):
        """Caso 8: Se envía una alerta -> Registrar envío, feedback al usuario, evitar duplicación accidental."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        inc = self.service.process_frame(
            [DetectionItem(class_id=0, class_name='missing', confidence=0.89, box=[1,1,2,2])],
            frame, location_id='GND-ALERT-TEST'
        )
        # Primer envío: debe ser exitoso
        rec = self.service.send_replenishment_alert(inc.id, channel='webhook')
        self.assertEqual(rec.status, 'sent')
        self.assertEqual(rec.incident_id, inc.id)
        self.assertIn('event', rec.payload)
        self.assertEqual(rec.payload['event'], 'stock_replenishment_alert')

        # Segundo envío: debe bloquearse para evitar duplicación
        with self.assertRaises(ValueError):
            self.service.send_replenishment_alert(inc.id, channel='webhook')

if __name__ == '__main__':
    unittest.main(verbosity=2)
