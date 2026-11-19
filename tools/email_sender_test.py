"""Desktop client for testing email alerts through the CVW API."""
import json
import threading
from tkinter import BOTH, END, LEFT, X, Button, Entry, Frame, Label, StringVar, Text, Tk, messagebox
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmailSenderTestApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("CVW - Email Sender Test")
        self.root.geometry("760x570")
        self.root.minsize(620, 480)

        self.server_url = StringVar(value="http://127.0.0.1:8000")
        self.subject = StringVar(value="Prueba de alerta de inventario")
        self.recipients = StringVar()
        self.status = StringVar(value="Configura el mensaje y presiona Enviar prueba.")

        self._build_ui()

    def _build_ui(self) -> None:
        container = Frame(self.root, padx=16, pady=14)
        container.pack(fill=BOTH, expand=True)

        Label(container, text="Cliente de prueba — alertas por correo", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        Label(
            container,
            text="Envía una alerta mediante el endpoint SMTP configurado en la API.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 14))

        Label(container, text="URL base del servidor").pack(anchor="w")
        url_row = Frame(container)
        url_row.pack(fill=X, pady=(4, 10))
        Entry(url_row, textvariable=self.server_url).pack(side=LEFT, fill=X, expand=True)
        Label(url_row, text="/api/alerts/email", fg="#475569").pack(side=LEFT, padx=(8, 0))

        Label(container, text="Destinatarios (separados por coma; opcional)").pack(anchor="w")
        Entry(container, textvariable=self.recipients).pack(fill=X, pady=(4, 10))

        Label(container, text="Asunto").pack(anchor="w")
        Entry(container, textvariable=self.subject).pack(fill=X, pady=(4, 10))

        Label(container, text="Cuerpo del mensaje").pack(anchor="w")
        self.body_input = Text(container, height=11, wrap="word")
        self.body_input.pack(fill=BOTH, expand=True, pady=(4, 10))
        self.body_input.insert(
            "1.0",
            "Esta es una prueba de envío de alertas por correo desde CVW.\n\n"
            "Si recibes este mensaje, la configuración SMTP funciona correctamente.",
        )

        controls = Frame(container)
        controls.pack(fill=X)
        self.example_button = Button(controls, text="Cargar alerta crítica", command=self._load_critical_example)
        self.example_button.pack(side=LEFT)
        self.send_button = Button(controls, text="Enviar prueba", command=self._send)
        self.send_button.pack(side=LEFT, padx=(8, 0))
        Label(container, textvariable=self.status, anchor="w", fg="#475569").pack(fill=X, pady=(10, 0))

    def _load_critical_example(self) -> None:
        self.subject.set("Alerta crítica de góndola — prueba")
        self.body_input.delete("1.0", END)
        self.body_input.insert(
            "1.0",
            "Alerta Crítica: Góndola en estado crítico.\n\n"
            "Faltantes: 8/10 (80%).\n"
            "Esta alerta fue generada por la herramienta de prueba.",
        )

    def _send(self) -> None:
        base_url = self.server_url.get().strip().rstrip("/")
        subject = self.subject.get().strip()
        body = self.body_input.get("1.0", END).strip()
        recipients = [value.strip() for value in self.recipients.get().split(",") if value.strip()]

        if not base_url.startswith(("http://", "https://")):
            messagebox.showerror("URL inválida", "La URL debe comenzar con http:// o https://.")
            return
        if not subject or not body:
            messagebox.showerror("Mensaje incompleto", "El asunto y el cuerpo son obligatorios.")
            return

        self.send_button.configure(state="disabled")
        self.status.set("Enviando alerta…")
        threading.Thread(
            target=self._send_request,
            args=(base_url, subject, body, recipients),
            daemon=True,
        ).start()

    def _send_request(self, base_url: str, subject: str, body: str, recipients: list[str]) -> None:
        payload = {"subject": subject, "body": body}
        if recipients:
            payload["recipients"] = recipients

        request = Request(
            f"{base_url}/api/alerts/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            self.root.after(0, self._show_result, True, result.get("message", "Alerta enviada."))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except json.JSONDecodeError:
                pass
            self.root.after(0, self._show_result, False, f"HTTP {error.code}: {detail}")
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            self.root.after(0, self._show_result, False, f"No se pudo contactar la API: {error}")

    def _show_result(self, success: bool, message: str) -> None:
        self.send_button.configure(state="normal")
        self.status.set(message)
        if success:
            messagebox.showinfo("Resultado", message)
        else:
            messagebox.showerror("Error de envío", message)


if __name__ == "__main__":
    root = Tk()
    EmailSenderTestApp(root)
    root.mainloop()
