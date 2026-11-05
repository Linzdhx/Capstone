"""Desktop client that periodically sends new images from a folder to CVW."""
import json
import mimetypes
import threading
import uuid
from pathlib import Path
from typing import Callable
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Entry, Frame, Label, StringVar, TclError, Tk, filedialog, messagebox
from tkinter.ttk import Spinbox, Treeview
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_RESULT_ROWS = 500


class ImageSenderTestApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("CVW - Image Sender Test")
        self.root.geometry("1020x680")
        self.root.minsize(760, 500)
        self.server_url = StringVar(value="http://127.0.0.1:8000")
        self.folder_path = StringVar()
        self.interval_var = StringVar(value="1")
        self.status = StringVar(value="Selecciona una carpeta para comenzar.")
        self._interval_seconds = 1
        self._interval_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._interval_changed = threading.Event()
        self._monitor_thread: threading.Thread | None = None

        self._build_ui()
        self.interval_var.trace_add("write", self._on_interval_changed)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        container = Frame(self.root, padx=16, pady=14)
        container.pack(fill=BOTH, expand=True)

        Label(container, text="Cliente de prueba — envío periódico de imágenes", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        Label(
            container,
            text="Vigila una carpeta y envía cada imagen nueva una sola vez a la API de CVW.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 14))

        Label(container, text="URL base del servidor").pack(anchor="w")
        url_row = Frame(container)
        url_row.pack(fill=X, pady=(4, 10))
        self.url_entry = Entry(url_row, textvariable=self.server_url)
        self.url_entry.pack(side=LEFT, fill=X, expand=True)
        Label(url_row, text="/api/stock/upload", fg="#475569").pack(side=LEFT, padx=(8, 0))

        Label(container, text="Carpeta de imágenes").pack(anchor="w")
        folder_row = Frame(container)
        folder_row.pack(fill=X, pady=(4, 10))
        self.folder_entry = Entry(folder_row, textvariable=self.folder_path, state="readonly")
        self.folder_entry.pack(side=LEFT, fill=X, expand=True)
        self.browse_button = Button(folder_row, text="Elegir carpeta…", command=self._choose_folder)
        self.browse_button.pack(side=LEFT, padx=(8, 0))

        controls = Frame(container)
        controls.pack(fill=X, pady=(0, 12))
        Label(controls, text="Revisar cada").pack(side=LEFT)
        self.interval_input = Spinbox(
            controls,
            from_=1,
            to=3600,
            increment=1,
            textvariable=self.interval_var,
            width=6,
        )
        self.interval_input.pack(side=LEFT, padx=(6, 4))
        Label(controls, text="segundo(s)").pack(side=LEFT)
        self.start_button = Button(controls, text="Iniciar envío periódico", command=self._start_monitoring)
        self.start_button.pack(side=LEFT, padx=(20, 6))
        self.stop_button = Button(controls, text="Detener", command=self._stop_monitoring, state="disabled")
        self.stop_button.pack(side=LEFT)

        Label(
            container,
            text="Las imágenes existentes y las que agregues mientras está activo se envían una sola vez. "
            "Se revisa esta carpeta, sin subcarpetas. Si el archivo todavía se está copiando, "
            "se espera a que su tamaño se estabilice. Al reiniciar el cliente se revisarán de nuevo.",
            font=("Segoe UI", 9),
            fg="#475569",
            wraplength=950,
            justify=LEFT,
        ).pack(anchor="w", pady=(0, 10))

        Label(container, text="Resultados por imagen", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        columns = ("filename", "status", "missing", "products", "percentage", "message")
        self.results = Treeview(container, columns=columns, show="headings", height=12)
        headings = {
            "filename": ("Archivo", 180),
            "status": ("Resultado", 110),
            "missing": ("Faltantes", 75),
            "products": ("Productos", 75),
            "percentage": ("% faltante", 85),
            "message": ("Detalle", 360),
        }
        for column, (heading, width) in headings.items():
            self.results.heading(column, text=heading)
            self.results.column(column, width=width, minwidth=60, anchor="w")
        self.results.tag_configure("missing", foreground="#be123c")
        self.results.tag_configure("clean", foreground="#047857")
        self.results.tag_configure("error", foreground="#b45309")
        self.results.pack(fill=BOTH, expand=True)

        Label(container, textvariable=self.status, anchor="w", fg="#475569").pack(fill=X, pady=(8, 0))

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="Seleccionar carpeta de imágenes")
        if selected:
            self.folder_path.set(selected)

    def _on_interval_changed(self, *_args: str) -> None:
        try:
            seconds = int(self.interval_var.get())
        except ValueError:
            return
        if seconds < 1 or seconds > 3600:
            return
        with self._interval_lock:
            self._interval_seconds = seconds
        self._interval_changed.set()

    def _start_monitoring(self) -> None:
        folder = Path(self.folder_path.get().strip())
        base_url = self.server_url.get().strip().rstrip("/")
        try:
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("Intervalo inválido", "El intervalo debe ser un número entero de segundos.")
            return

        if not folder.is_dir():
            messagebox.showerror("Carpeta inválida", "Selecciona una carpeta existente.")
            return
        if not base_url.startswith(("http://", "https://")):
            messagebox.showerror("URL inválida", "La URL debe comenzar con http:// o https://.")
            return
        if interval < 1 or interval > 3600:
            messagebox.showerror("Intervalo inválido", "El intervalo debe estar entre 1 y 3600 segundos.")
            return

        with self._interval_lock:
            self._interval_seconds = interval
        self._stop_event.clear()
        self._interval_changed.clear()
        self._set_running_state(True)
        self.status.set(f"Vigilando {folder} cada {interval} segundo(s)…")
        self._monitor_thread = threading.Thread(
            target=self._monitor_folder,
            args=(base_url, folder),
            daemon=True,
        )
        self._monitor_thread.start()

    def _stop_monitoring(self) -> None:
        self._stop_event.set()
        self._interval_changed.set()
        self.stop_button.configure(state="disabled")
        self.status.set("Deteniendo el envío periódico…")

    def _close(self) -> None:
        self._stop_event.set()
        self._interval_changed.set()
        self.root.destroy()

    def _schedule_ui(self, callback: Callable[..., None], *args: object) -> None:
        try:
            self.root.after(0, callback, *args)
        except TclError:
            if not self._stop_event.is_set():
                raise

    def _set_running_state(self, running: bool) -> None:
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.browse_button.configure(state="disabled" if running else "normal")
        self.url_entry.configure(state="disabled" if running else "normal")
        self.folder_entry.configure(state="readonly")

    def _get_interval(self) -> int:
        with self._interval_lock:
            return self._interval_seconds

    def _monitor_folder(self, base_url: str, folder: Path) -> None:
        observed: dict[Path, tuple[int, int]] = {}
        sent: dict[Path, tuple[int, int]] = {}
        try:
            while not self._stop_event.is_set():
                interval = self._get_interval()
                self._interval_changed.wait(interval)
                if self._stop_event.is_set():
                    break
                if self._interval_changed.is_set():
                    self._interval_changed.clear()
                    continue

                try:
                    ready_files = self._find_stable_new_images(folder, observed, sent)
                except OSError as error:
                    self._set_status(f"No se pudo revisar la carpeta: {error}")
                    continue

                if not ready_files:
                    continue

                self._set_status(f"Enviando {len(ready_files)} imagen(es) nueva(s)…")
                try:
                    payload = self._upload_files(base_url, ready_files)
                except (URLError, TimeoutError, OSError, RuntimeError, ValueError) as error:
                    self._set_status(f"Error al enviar imágenes: {error}. Se reintentará en el próximo intervalo.")
                    continue

                for path in ready_files:
                    sent[path] = observed[path]
                self._schedule_ui(self._show_results, payload)
        finally:
            self._schedule_ui(self._monitor_stopped)

    @staticmethod
    def _file_signature(path: Path) -> tuple[int, int]:
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns

    @classmethod
    def _find_stable_new_images(
        cls,
        folder: Path,
        observed: dict[Path, tuple[int, int]],
        sent: dict[Path, tuple[int, int]],
    ) -> list[Path]:
        ready: list[Path] = []
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            signature = cls._file_signature(path)
            if observed.get(path) == signature and sent.get(path) != signature:
                ready.append(path)
            observed[path] = signature
        return ready

    def _upload_files(self, base_url: str, files: list[Path]) -> dict:
        body, content_type = self._encode_multipart(files)
        request = Request(
            f"{base_url}/api/stock/upload",
            data=body,
            headers={"Content-Type": content_type, "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"HTTP {error.code}: {detail}") from error

    @staticmethod
    def _encode_multipart(files: list[Path]) -> tuple[bytes, str]:
        boundary = uuid.uuid4().hex
        chunks: list[bytes] = []
        for path in files:
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if not mime_type.startswith("image/"):
                raise ValueError(f"El archivo no parece ser una imagen: {path.name}")
            ascii_filename = path.name.encode("ascii", errors="replace").decode("ascii")
            ascii_filename = "".join(
                character if character.isprintable() and character not in '"\\/' else "_"
                for character in ascii_filename
            )
            chunks.extend([
                f"--{boundary}\r\n".encode("ascii"),
                (
                    f'Content-Disposition: form-data; name="files"; filename="{ascii_filename}"\r\n'
                    f"Content-Type: {mime_type}\r\n\r\n"
                ).encode("ascii"),
                path.read_bytes(),
                b"\r\n",
            ])
        chunks.append(f"--{boundary}--\r\n".encode("ascii"))
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def _show_results(self, payload: dict) -> None:
        for result in payload.get("results", []):
            failed = result.get("processing_error", False)
            has_missing = result.get("saved_to_historica", False) and not failed
            status = "Error" if failed else "Con faltantes" if has_missing else "Stock correcto"
            tag = "error" if failed else "missing" if has_missing else "clean"
            self.results.insert(
                "",
                END,
                values=(
                    result.get("filename", ""),
                    status,
                    result.get("missing_count", 0),
                    result.get("product_count", 0),
                    f'{result.get("missing_percentage", 0)}%',
                    result.get("message", ""),
                ),
                tags=(tag,),
            )

        rows = self.results.get_children()
        for row in rows[:-MAX_RESULT_ROWS]:
            self.results.delete(row)

        self.status.set(
            f"Lote {payload.get('batch_id', 'sin ID')}: "
            f"{payload.get('total_analyzed', 0)} analizadas · "
            f"{payload.get('faults_detected', 0)} con faltantes · "
            f"{payload.get('discarded_clean', 0)} correctas · "
            f"{payload.get('failed_count', 0)} errores. "
            f"Vigilando cada {self._get_interval()} segundo(s)."
        )

    def _set_status(self, message: str) -> None:
        self._schedule_ui(self.status.set, message)

    def _monitor_stopped(self) -> None:
        self._set_running_state(False)
        if self._stop_event.is_set():
            self.status.set("Envío periódico detenido.")


if __name__ == "__main__":
    root = Tk()
    ImageSenderTestApp(root)
    root.mainloop()
