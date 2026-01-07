# main.py en la raíz de ontester
import traceback
from pathlib import Path
from datetime import datetime
from src.Frontend.ui.inicio_view import run_app 

if __name__ == "__main__":
    try:
        run_app()
    except Exception as e:
        log_path = Path("C:/ONT/ontester_exe_error.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n\n=== EXCEPCIÓN NO MANEJADA ===\n")
            f.write(f"Fecha/hora: {datetime.now().isoformat()}\n")
            f.write(f"Tipo: {type(e).__name__}\n")
            f.write(f"Mensaje: {e}\n\n")
            traceback.print_exc(file=f)