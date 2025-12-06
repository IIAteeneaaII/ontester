import customtkinter as ctk
import sys
from pathlib import Path
from tkinter import messagebox

# Para poder usar imports absolutos
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion
from src.Frontend.ui.menu_superior_view import MenuSuperiorDesplegable


class CambiarEstacionDialog(ctk.CTkToplevel):
    """
    Ventana emergente para cambiar el número de estación.
    """
    
    def __init__(self, parent, estacion_actual):
        super().__init__(parent)
        
        self.nuevo_numero = None
        
        # Configuración de la ventana
        self.title("Cambiar Estación")
        self.geometry("400x200")
        self.resizable(False, False)
        
        # Centrar la ventana
        self.transient(parent)
        self.grab_set()
        
        # Configurar el grid
        self.grid_columnconfigure(0, weight=1)
        
        # ---------- Contenido ----------
        # Título
        titulo_label = ctk.CTkLabel(
            self,
            text="Ingrese el número de estación\na donde se hará el cambio",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50"
        )
        titulo_label.grid(row=0, column=0, pady=(20, 10), padx=20)
        
        # Entry para el número
        self.entry_estacion = ctk.CTkEntry(
            self,
            width=150,
            height=40,
            font=ctk.CTkFont(size=16),
            justify="center",
            fg_color="white",
            border_color="#6B9080",
            border_width=2
        )
        self.entry_estacion.grid(row=1, column=0, pady=10)
        self.entry_estacion.insert(0, estacion_actual)
        self.entry_estacion.focus()
        
        # Bind para Enter
        self.entry_estacion.bind("<Return>", lambda e: self.confirmar())
        
        # Frame para botones
        botones_frame = ctk.CTkFrame(self, fg_color="transparent")
        botones_frame.grid(row=2, column=0, pady=20, padx=20)
        
        # Botón Aceptar
        btn_aceptar = ctk.CTkButton(
            botones_frame,
            text="ACEPTAR",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            width=120,
            height=35
        )
        btn_aceptar.pack(side="left", padx=5)
        
        # Botón Cancelar
        btn_cancelar = ctk.CTkButton(
            botones_frame,
            text="CANCELAR",
            command=self.cancelar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#C1666B",
            hover_color="#A4161A",
            width=120,
            height=35
        )
        btn_cancelar.pack(side="left", padx=5)
    
    def confirmar(self):
        """Valida y guarda el nuevo número de estación."""
        valor = self.entry_estacion.get().strip()
        
        # Validar que sea un número
        if not valor:
            messagebox.showwarning(
                "Advertencia",
                "Por favor ingrese un número de estación.",
                parent=self
            )
            return
        
        if not valor.isdigit():
            messagebox.showerror(
                "Error",
                "El número de estación debe contener solo dígitos.",
                parent=self
            )
            return
        
        # Formatear con ceros a la izquierda si es necesario (opcional)
        self.nuevo_numero = valor.zfill(2)  # Asegura 2 dígitos mínimo (01, 02, etc.)
        self.destroy()
    
    def cancelar(self):
        """Cancela el cambio."""
        self.nuevo_numero = None
        self.destroy()


class ModificarEtiquetadoDialog(ctk.CTkToplevel):
    """
    Ventana emergente para configurar el modo de etiqueta.
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.resultado = None
        
        # Configuración de la ventana
        self.title("Configuración de Etiqueta")
        self.geometry("450x250")
        self.resizable(False, False)
        self.configure(fg_color="#E8E8E8")
        
        # Centrar la ventana
        self.transient(parent)
        self.grab_set()
        
        # ---------- Botón de cerrar (X roja) ----------
        close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            height=30,
            corner_radius=5,
            fg_color="#C1666B",
            hover_color="#A4161A",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.cancelar
        )
        close_btn.place(x=410, y=10)
        
        # ---------- Título ----------
        titulo_label = ctk.CTkLabel(
            self,
            text="CONFIGURACIÓN DE ETIQUETA",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50"
        )
        titulo_label.pack(pady=(20, 30), padx=20)
        
        # ---------- Sección de opciones ----------
        opciones_label = ctk.CTkLabel(
            self,
            text="MODO DE ETIQUETA DE FIBERHOME",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#2C3E50"
        )
        opciones_label.pack(pady=(0, 15))
        
        # Variable para los radio buttons
        self.etiqueta_var = ctk.StringVar(value="unica")
        
        # Radio button: ETIQUETA ÚNICA
        radio_unica = ctk.CTkRadioButton(
            self,
            text="ETIQUETA ÚNICA",
            variable=self.etiqueta_var,
            value="unica",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50",
            fg_color="#4EA5D9",
            hover_color="#3B8CC2"
        )
        radio_unica.pack(pady=5, padx=40, anchor="w")
        
        # Radio button: ETIQUETA DOBLE
        radio_doble = ctk.CTkRadioButton(
            self,
            text="ETIQUETA DOBLE",
            variable=self.etiqueta_var,
            value="doble",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50",
            fg_color="#4EA5D9",
            hover_color="#3B8CC2"
        )
        radio_doble.pack(pady=5, padx=40, anchor="w")
        
        # ---------- Botón Aceptar ----------
        btn_aceptar = ctk.CTkButton(
            self,
            text="Aceptar",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            width=120,
            height=35
        )
        btn_aceptar.pack(pady=(20, 15))
    
    def confirmar(self):
        """Guarda la configuración seleccionada."""
        self.resultado = self.etiqueta_var.get()
        print(f"Modo de etiqueta seleccionado: {self.resultado}")
        self.destroy()
    
    def cancelar(self):
        """Cancela sin guardar cambios."""
        self.resultado = None
        self.destroy()


class ModificarParametrosDialog(ctk.CTkToplevel):
    """
    Ventana emergente para configurar los parámetros del ONT TESTER.
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.resultado = None
        
        # Configuración de la ventana
        self.title("Parámetros de ONT Tester")
        self.geometry("550x700")
        self.resizable(False, False)
        self.configure(fg_color="#E8E8E8")
        
        # Centrar la ventana
        self.transient(parent)
        self.grab_set()
        
        # ---------- Botón de cerrar (X roja) ----------
        close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            height=30,
            corner_radius=5,
            fg_color="#C1666B",
            hover_color="#A4161A",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.cancelar
        )
        close_btn.place(x=510, y=10)
        
        # ---------- Título ----------
        titulo_label = ctk.CTkLabel(
            self,
            text="PARÁMETROS DE ONT TESTER",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50"
        )
        titulo_label.pack(pady=(20, 25), padx=20)
        
        # Frame principal con scrollbar
        main_scrollable = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            width=500,
            height=500
        )
        main_scrollable.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # ---------- RANGO DE VALORES EN TX ----------
        self._crear_seccion_rango(
            main_scrollable, 
            "RANGO DE VALORES EN TX",
            "tx_min", "tx_max",
            valores_min=["1.00", "2.00", "3.00", "4.00", "5.00"],
            valores_max=["3.00", "4.00", "5.00", "6.00"],
            default_min="1.00",
            default_max="5.00"
        )
        
        # ---------- RANGO DE VALORES EN RX ----------
        self._crear_seccion_rango(
            main_scrollable,
            "RANGO DE VALORES EN RX",
            "rx_min", "rx_max",
            valores_min=["-15.00", "-12.00", "-10.00", "-8.00"],
            valores_max=["-12.00", "-10.00", "-8.00", "-5.00"],
            default_min="-15.00",
            default_max="-10.00"
        )
        
        # ---------- RANGO DE VALORES RSSI 2.4 GHz ----------
        self._crear_seccion_rango(
            main_scrollable,
            "RANGO DE VALORES RSSI 2.4 GHz",
            "rssi24_min", "rssi24_max",
            valores_min=["-80", "-70", "-60", "-50"],
            valores_max=["-10", "-5", "0"],
            default_min="-80",
            default_max="-5"
        )
        
        # ---------- RANGO DE VALORES RSSI 5.0 GHz ----------
        self._crear_seccion_rango(
            main_scrollable,
            "RANGO DE VALORES RSSI 5.0 GHz",
            "rssi50_min", "rssi50_max",
            valores_min=["-80", "-70", "-60", "-50"],
            valores_max=["-10", "-5", "0"],
            default_min="-80",
            default_max="-5"
        )
        
        # ---------- BÚSQUEDAS PARA ENCONTRAR SEÑALES WIFI ----------
        busquedas_frame = ctk.CTkFrame(main_scrollable, fg_color="transparent")
        busquedas_frame.pack(fill="x", pady=(20, 10))
        
        busquedas_label = ctk.CTkLabel(
            busquedas_frame,
            text="BÚSQUEDAS PARA ENCONTRAR SEÑALES WIFI",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        )
        busquedas_label.pack(anchor="w", pady=(0, 10))
        
        self.busquedas_combo = ctk.CTkComboBox(
            busquedas_frame,
            values=["10", "20", "30", "40", "50"],
            width=200,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.busquedas_combo.set("40")
        self.busquedas_combo.pack(anchor="w", pady=(0, 10))
        
        # ---------- Botones ----------
        botones_frame = ctk.CTkFrame(self, fg_color="transparent")
        botones_frame.pack(pady=(5, 20))
        
        btn_aceptar = ctk.CTkButton(
            botones_frame,
            text="Aceptar",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D4AF37",
            hover_color="#C19B2B",
            text_color="#2C3E50",
            width=120,
            height=35
        )
        btn_aceptar.pack(side="left", padx=5)
        
        btn_restaurar = ctk.CTkButton(
            botones_frame,
            text="Restaurar",
            command=self.restaurar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#A8DADC",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            width=120,
            height=35
        )
        btn_restaurar.pack(side="left", padx=5)
        
        btn_cancelar = ctk.CTkButton(
            botones_frame,
            text="Cancelar",
            command=self.cancelar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#C1666B",
            hover_color="#A4161A",
            text_color="white",
            width=120,
            height=35
        )
        btn_cancelar.pack(side="left", padx=5)
    
    def _crear_seccion_rango(self, parent, titulo, var_min_name, var_max_name, 
                             valores_min, valores_max, default_min, default_max):
        """Crea una sección de rango con dos comboboxes."""
        # Frame contenedor de la sección
        seccion_frame = ctk.CTkFrame(parent, fg_color="transparent")
        seccion_frame.pack(fill="x", pady=(15, 10))
        
        # Título de la sección
        label = ctk.CTkLabel(
            seccion_frame,
            text=titulo,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        )
        label.pack(anchor="w", pady=(0, 10))
        
        # Frame para los combos en horizontal
        combos_frame = ctk.CTkFrame(seccion_frame, fg_color="transparent")
        combos_frame.pack(anchor="w")
        
        # Combo mínimo
        combo_min = ctk.CTkComboBox(
            combos_frame,
            values=valores_min,
            width=140,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        combo_min.set(default_min)
        combo_min.pack(side="left", padx=(0, 10))
        setattr(self, var_min_name, combo_min)
        
        # Label "a"
        ctk.CTkLabel(
            combos_frame,
            text="a",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        ).pack(side="left", padx=10)
        
        # Combo máximo
        combo_max = ctk.CTkComboBox(
            combos_frame,
            values=valores_max,
            width=140,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        combo_max.set(default_max)
        combo_max.pack(side="left", padx=(10, 0))
        setattr(self, var_max_name, combo_max)
    
    def confirmar(self):
        """Guarda la configuración."""
        self.resultado = {
            'tx_min': self.tx_min.get(),
            'tx_max': self.tx_max.get(),
            'rx_min': self.rx_min.get(),
            'rx_max': self.rx_max.get(),
            'rssi24_min': self.rssi24_min.get(),
            'rssi24_max': self.rssi24_max.get(),
            'rssi50_min': self.rssi50_min.get(),
            'rssi50_max': self.rssi50_max.get(),
            'busquedas': self.busquedas_combo.get()
        }
        print(f"Parámetros guardados: {self.resultado}")
        self.destroy()
    
    def restaurar(self):
        """Restaura los valores por defecto."""
        self.tx_min.set("1.00")
        self.tx_max.set("5.00")
        self.rx_min.set("-15.00")
        self.rx_max.set("-10.00")
        self.rssi24_min.set("-80")
        self.rssi24_max.set("-5")
        self.rssi50_min.set("-80")
        self.rssi50_max.set("-5")
        self.busquedas_combo.set("40")
        print("Valores restaurados a los valores por defecto")
    
    def cancelar(self):
        """Cancela sin guardar cambios."""
        self.resultado = None
        self.destroy()


class TesterMainView(ctk.CTkFrame):
    """
    Vista principal del ONT TESTER con botones superiores y panel de pruebas.
    """

    def __init__(self, parent, viewmodel=None, **kwargs):
        super().__init__(parent, fg_color="#E8F4F8", **kwargs)

        self.viewmodel = viewmodel
        self.numero_estacion = "09"  # Número de estación por defecto

        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # título
        self.grid_rowconfigure(1, weight=1)  # botones superiores
        self.grid_rowconfigure(2, weight=0)  # panel de pruebas

        # ---------- Título verde ----------
        title_frame = ctk.CTkFrame(self, fg_color="#6B9080", corner_radius=0)
        title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        # SOLO menú a la izquierda y título al lado
        title_frame.grid_columnconfigure(0, weight=0)  # menú
        title_frame.grid_columnconfigure(1, weight=1)  # título

        # Menú desplegable en esquina superior izquierda
        self.menu_superior = MenuSuperiorDesplegable(
            title_frame,
            on_open_tester=self.ir_a_ont_tester,
            on_open_base_diaria=self.ir_a_base_diaria,
            on_open_base_global=self.ir_a_base_global,
            on_open_otros=self.ir_a_otros,
        )
        self.menu_superior.grid(row=0, column=0, sticky="w", padx=20, pady=6)

        # Título del módulo
        self.titulo = ctk.CTkLabel(
            title_frame,
            text=f"ONT TESTER - REPARANDO EN ESTACIÓN {self.numero_estacion}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        self.titulo.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        # ---------- Contenedor de botones superiores ----------
        buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        buttons_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        
        # Configurar grid para centrar los botones
        buttons_container.grid_columnconfigure(0, weight=1)
        buttons_container.grid_rowconfigure(0, weight=1)
        
        # Frame interno para los botones (para que no ocupen todo el espacio)
        buttons_frame = ctk.CTkFrame(buttons_container, fg_color="transparent")
        buttons_frame.grid(row=0, column=0)
        
        # Configurar columnas para los 4 botones
        for col in range(4):
            buttons_frame.grid_columnconfigure(col, weight=0, minsize=250)

        # ---------- Botones superiores estilo tarjeta ----------
        # Botón 1: CAMBIAR ESTACIÓN (gris)
        btn1_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#B8B8B8",
            corner_radius=15,
            width=250,
            height=180
        )
        btn1_frame.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        btn1_frame.grid_propagate(False)
        
        ctk.CTkLabel(
            btn1_frame,
            text="👤",
            font=ctk.CTkFont(size=50)
        ).pack(pady=(20, 10))
        
        btn1 = ctk.CTkButton(
            btn1_frame,
            text="CAMBIAR ESTACIÓN",
            command=self.on_cambiar_estacion,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#A0A0A0",
            text_color="#2C3E50",
            height=40
        )
        btn1.pack(fill="x", padx=15, pady=(0, 20))

        # Botón 2: MODIFICAR ETIQUETADO (rosa)
        btn2_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#F1B4BB",
            corner_radius=15,
            width=250,
            height=180
        )
        btn2_frame.grid(row=0, column=1, padx=15, pady=10, sticky="nsew")
        btn2_frame.grid_propagate(False)
        
        ctk.CTkLabel(
            btn2_frame,
            text="🏷️",
            font=ctk.CTkFont(size=50)
        ).pack(pady=(20, 10))
        
        btn2 = ctk.CTkButton(
            btn2_frame,
            text="MODIFICAR ETIQUETADO",
            command=self.on_modificar_etiquetado,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            height=40
        )
        btn2.pack(fill="x", padx=15, pady=(0, 20))

        # Botón 3: MODIFICAR PARÁMETROS (azul)
        btn3_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#A8DADC",
            corner_radius=15,
            width=250,
            height=180
        )
        btn3_frame.grid(row=0, column=2, padx=15, pady=10, sticky="nsew")
        btn3_frame.grid_propagate(False)
        
        ctk.CTkLabel(
            btn3_frame,
            text="⚙️",
            font=ctk.CTkFont(size=50)
        ).pack(pady=(20, 10))
        
        btn3 = ctk.CTkButton(
            btn3_frame,
            text="MODIFICAR PARÁMETROS",
            command=self.on_modificar_parametros,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            height=40
        )
        btn3.pack(fill="x", padx=15, pady=(0, 20))

        # Botón 4: PRUEBA (rosa)
        btn4_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#F1B4BB",
            corner_radius=15,
            width=250,
            height=180
        )
        btn4_frame.grid(row=0, column=3, padx=15, pady=10, sticky="nsew")
        btn4_frame.grid_propagate(False)
        
        ctk.CTkLabel(
            btn4_frame,
            text="🔧",
            font=ctk.CTkFont(size=50)
        ).pack(pady=(20, 10))
        
        btn4 = ctk.CTkButton(
            btn4_frame,
            text="PRUEBA",
            command=self.on_prueba,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            height=40
        )
        btn4.pack(fill="x", padx=15, pady=(0, 20))

        # ---------- Panel de pruebas de conexión (parte inferior) ----------
        self.panel_pruebas = PanelPruebasConexion(self)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

    # ---------- Callbacks de los botones ----------
    def on_cambiar_estacion(self):
        """Acción del botón CAMBIAR ESTACIÓN - Abre ventana emergente."""
        dialog = CambiarEstacionDialog(self, self.numero_estacion)
        self.wait_window(dialog)
        
        # Si el usuario confirmó el cambio
        if dialog.nuevo_numero is not None:
            self.numero_estacion = dialog.nuevo_numero
            self.actualizar_titulo()
    
    def actualizar_titulo(self):
        """Actualiza el título con el nuevo número de estación."""
        self.titulo.configure(
            text=f"ONT TESTER - REPARANDO EN ESTACIÓN {self.numero_estacion}"
        )

    def on_modificar_etiquetado(self):
        """Acción del botón MODIFICAR ETIQUETADO - Abre ventana de configuración."""
        dialog = ModificarEtiquetadoDialog(self)
        self.wait_window(dialog)
        
        if dialog.resultado is not None:
            print(f"Configuración de etiqueta guardada: {dialog.resultado}")
            if self.viewmodel:
                # Llamar al viewmodel para guardar la configuración
                pass

    def on_modificar_parametros(self):
        """Acción del botón MODIFICAR PARÁMETROS - Abre ventana de parámetros."""
        dialog = ModificarParametrosDialog(self)
        self.wait_window(dialog)
        
        if dialog.resultado is not None:
            print(f"Parámetros guardados: {self.resultado}")
            if self.viewmodel:
                # Llamar al viewmodel para guardar los parámetros
                pass

    def on_prueba(self):
        """Acción del botón PRUEBA."""
        print("Prueba clickeado")
        if self.viewmodel:
            # Llamar al viewmodel
            pass

    # ---------- Callbacks de navegación del menú superior ----------

    def ir_a_ont_tester(self):
        """Opción de menú: ONT TESTER"""
        print("Navegando a ONT TESTER")
        if self.viewmodel and hasattr(self.viewmodel, "abrir_tester_view"):
            self.viewmodel.abrir_tester_view()

    def ir_a_base_diaria(self):
        """Opción de menú: BASE DIARIA"""
        print("Navegando a BASE DIARIA")
        if self.viewmodel and hasattr(self.viewmodel, "abrir_escaneos_dia"):
            self.viewmodel.abrir_escaneos_dia()

    def ir_a_base_global(self):
        """Opción de menú: BASE GLOBAL"""
        print("Navegando a BASE GLOBAL")
        if self.viewmodel and hasattr(self.viewmodel, "abrir_reporte_global"):
            self.viewmodel.abrir_reporte_global()

    def ir_a_otros(self):
        """Opción de menú: OTROS"""
        print("Navegando a OTROS")
        if self.viewmodel and hasattr(self.viewmodel, "abrir_otros"):
            self.viewmodel.abrir_otros()


# Test de la vista
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("ONT TESTER - Vista Principal")
    app.geometry("1400x700")

    view = TesterMainView(app)
    view.pack(fill="both", expand=True)

    app.mainloop()