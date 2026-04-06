# main.py en la raíz de ontester
import traceback
from pathlib import Path
from datetime import datetime
from src.backend.sua_client.local_db import init_db
from src.backend.endpoints.peticiones_sua import solicitar_registro_sua
from src.backend.endpoints.resources import get_pc_id_from_mac_suffix
from src.backend.sua_client.iot_client import llamada_verision_instalada
import sys
import tkinter as tk
from tkinter import messagebox

if __name__ == "__main__":
    try:
        # Iniciar la db
        init_db()
        # Hacer la petición a SUA para que registre mi ID station (el de la mac)
        result = solicitar_registro_sua(get_pc_id_from_mac_suffix())
        

        # from src.backend.mixins.common_mixin import CommonMixin
        # cm = CommonMixin()
        # nets_all = cm.scan_wifi_windows(target_ssid=None, retries=3, delay=1.0, debug=True)
        # print("SSIDs vistos:", sorted({n["ssid"] for n in nets_all if n.get("ssid")}))
        # Correr interfaz
        if result is True:
            root = tk.Tk()
            root.withdraw()

            messagebox.showwarning(
                "Aplicación no autenticada",
                "No se puede iniciar la aplicación porque esta estación no está autenticada.\n\n"
                "Ya se mandó la solicitud de enrolamiento a SSUA."
            )

            root.destroy()
            sys.exit(0)

        elif result is None:
            from src.Frontend.ui.inicio_view import run_app
            # Reportar versión instalada al arranque si es el caso
            llamada_verision_instalada()
            run_app()

        else:
            root = tk.Tk()
            root.withdraw()

            messagebox.showerror(
                "Error",
                "No se pudo inicializar la aplicación."
            )

            root.destroy()
            sys.exit(1)

     

    except Exception as e:
        log_path = Path("C:/ONT/ontester_exe_error.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n\n=== EXCEPCIÓN NO MANEJADA ===\n")
            f.write(f"Fecha/hora: {datetime.now().isoformat()}\n")
            f.write(f"Tipo: {type(e).__name__}\n")
            f.write(f"Mensaje: {e}\n\n")
            traceback.print_exc(file=f)

        root = tk.Tk()
        root.withdraw()

        messagebox.showerror(
            "Error fatal",
            f"Ocurrió un error al iniciar la aplicación:\n\n{e}"
        )

        root.destroy()
        sys.exit(1) 