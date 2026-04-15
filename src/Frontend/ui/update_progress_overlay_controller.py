from __future__ import annotations

from pathlib import Path
from typing import Any

from src.Frontend.ui.progress_overlay import FloatingProgressOverlay


class UpdateProgressOverlayController:
    """
    Controlador del overlay flotante de progreso de actualización.

    Responsabilidades:
    - Crear el overlay bajo demanda.
    - Recibir eventos desde el dispatcher.
    - Actualizar texto y porcentaje.
    - Cerrar el overlay cuando corresponda.

    Eventos esperados:
    kind = "update_progress"

    payload ejemplo:
    {
        "show": True,
        "status": "Actualización disponible",
        "progress": 5,
        "done": False,
        "hide": False,
    }
    """

    EVENT_KIND = "update_progress"

    def __init__(
        self,
        root,
        *,
        outline_image_path: str | Path,
        full_image_path: str | Path,
        width: int = 320,
        height: int = 260,
        auto_close_on_done: bool = False,
        auto_close_delay_ms: int = 1500,
    ) -> None:
        self.root = root
        self.outline_image_path = str(outline_image_path)
        self.full_image_path = str(full_image_path)
        self.width = width
        self.height = height
        self.auto_close_on_done = auto_close_on_done
        self.auto_close_delay_ms = auto_close_delay_ms

        self.overlay: FloatingProgressOverlay | None = None
        self._close_after_id = None

    def on_event(self, kind: str, payload: dict[str, Any] | None) -> None:
        """
        Punto de entrada para integrarse con EventDispatcher.
        """
        print(f"[OVERLAY_CONTROLLER] kind={kind}, payload={payload}")

        if kind != self.EVENT_KIND:
            return

        payload = payload or {}

        if payload.get("show"):
            self.show()

        if payload.get("hide"):
            self.hide()
            return

        if self.overlay is None or not self._overlay_exists():
            # Si llega progreso sin show explícito, lo creamos automáticamente.
            self.show()

        status = payload.get("status")
        progress = payload.get("progress")
        done = payload.get("done", False)

        if status is not None:
            self.set_status(status)

        if progress is not None:
            self.set_progress(progress)

        if done:
            self.set_progress(100)
            if status is None:
                self.set_status("Descarga completada")

            if self.auto_close_on_done:
                self._schedule_close()

    def show(self) -> None:
        print("[OVERLAY_CONTROLLER] show() llamado")

        if self._overlay_exists():
            return

        self._cancel_scheduled_close()

        self.overlay = FloatingProgressOverlay(
            self.root,
            outline_image_path=self.outline_image_path,
            full_image_path=self.full_image_path,
            width=self.width,
            height=self.height,
        )
        self.overlay.set_status("Preparando descarga...")
        self.overlay.set_progress(0)
        print(f"[OVERLAY_CONTROLLER] overlay creado: {self.overlay}")

    def hide(self) -> None:
        self._cancel_scheduled_close()

        if self._overlay_exists():
            self.overlay.close_overlay()

        self.overlay = None

    def set_status(self, text: str) -> None:
        if self._overlay_exists():
            self.overlay.set_status(text)

    def set_progress(self, percent: int) -> None:
        print(f"[OVERLAY_CONTROLLER] set_progress({percent})")
        if self._overlay_exists():
            self.overlay.set_progress(percent)

    def emit_show(self, status: str = "Preparando descarga...", progress: int = 0) -> None:
        """
        Helper opcional si quieres usar esta clase manualmente sin dispatcher.
        """
        self.show()
        self.set_status(status)
        self.set_progress(progress)

    def emit_done(self, status: str = "Descarga completada") -> None:
        if not self._overlay_exists():
            self.show()

        self.set_status(status)
        self.set_progress(100)

        if self.auto_close_on_done:
            self._schedule_close()

    def _overlay_exists(self) -> bool:
        return self.overlay is not None and self.overlay.winfo_exists()

    def _schedule_close(self) -> None:
        self._cancel_scheduled_close()
        self._close_after_id = self.root.after(self.auto_close_delay_ms, self.hide)

    def _cancel_scheduled_close(self) -> None:
        if self._close_after_id is not None:
            try:
                self.root.after_cancel(self._close_after_id)
            except Exception:
                pass
            self._close_after_id = None