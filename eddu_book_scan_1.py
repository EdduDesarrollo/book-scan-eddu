"""Programa para digitalizar diapositivas"""
import io
import os
import shutil
import logging
import subprocess
import threading
import sys
import json
from pathlib import Path # pylint: disable=W0611
from datetime import datetime

try:
    import cv2
except ModuleNotFoundError:
    print("pip3 install opencv-python")
    print("cv2 no está instalado. Instalando...")
    subprocess.check_call([sys.executable, "-m", "pip", "isntall", "opencv-python"])
    os.execv(sys.executable, ['python3'] + sys.argv)
    import cv2
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ModuleNotFoundError:
    print("Error: tkinter no está instalado. Por favor instálalo con:")
    print("sudo apt install python3-tk")
    print("e inicie nuevamente el programa!")
    sys.exit(1)

try:
    import gphoto2 as gp
except ModuleNotFoundError:
    print("gphoto2 no está instalado. Instalando...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gphoto2"])
    os.execv(sys.executable, ['python3'] + sys.argv)

import numpy as np
from PIL import Image as Imge

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.properties import StringProperty
    from kivy.uix.anchorlayout import AnchorLayout
    from kivy.uix.image import Image
    from kivy.clock import Clock
    from kivy.graphics.texture import Texture # pylint: disable=E0611
    from kivy.graphics import Color, Rectangle
    from kivy.uix.button import Button
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.popup import Popup
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.textinput import TextInput
    from kivy.core.window import Window
    from kivy.uix.filechooser import FileChooserListView #FileChooserIconView
    from kivy.uix.behaviors import ButtonBehavior
    from kivy.animation import Animation
    from kivy.core.image import Image as CoreImage
    from kivy.resources import resource_find
except ModuleNotFoundError:
    print("Kivy no está instalado. Instalando...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "kivy"])
    os.execv(sys.executable, ['python3'] + sys.argv)

logging.getLogger("PIL").setLevel(logging.CRITICAL)

# Ruta al archivo de configuración
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Utils', 'config.json')

# Cargar configuración desde el archivo
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
        PREFIJO_ARCHIVO = config.get("PREFIJO_ARCHIVO", "")
        NOMBRE_INGRESADO = config.get("NOMBRE_INGRESADO", "")
        DIRECTORIO = config.get("DIRECTORIO", "")
        TIEMPO_ESPERA_VAL = config.get('TIEMPO_ESPERA', '5')
        TIEMPO_ESPERA_STR = str(TIEMPO_ESPERA_VAL)
        if TIEMPO_ESPERA_STR.isdigit():
            TIEMPO_ESPERA = int(TIEMPO_ESPERA_STR)
        else:
            TIEMPO_ESPERA = 5

        MENSAJE_PIDO_ROLLO = config.get('MSJ_PIDO_ROLLO', '').replace('\\n', '\n')
        MENSAJE_CAMBIO_NOMBRE = (config.get('MSJ_CAMBIO_NOMBRE', '').replace('\\n', '\n'),
                            PREFIJO_ARCHIVO)
        MENSAJE_PIDO_QTY_CAMARAS = config.get('MSJ_PIDO_QTY_CAMARAS', '')

        CAMARA_1 = config.get('CAMARA_1', '')
        CAMARA_2 = config.get('CAMARA_2', '')

        color_str = config.get('COLOR_BOTONES', '')
        COLOR_BOTONES = tuple(map(float, [v.strip() for v in color_str.strip('()').split(',')]))
except Exception as e: # pylint: disable=W0703
    print(f"⚠️ No se pudo cargar el archivo de configuración: {e}")
    PREFIJO_ARCHIVO = "UY-UDELAR-AGU-AIH"
    NOMBRE_INGRESADO = ""
    DIRECTORIO = ""
    TIEMPO_ESPERA = 5
    CAMARA_1 = ""
    CAMARA_2 = ""
    COLOR_BOTONES = (0.175, 0.319, 0.513, 0.997)
    MENSAJE_PIDO_ROLLO = ""
    MENSAJE_CAMBIO_NOMBRE = ""
    MENSAJE_PIDO_QTY_CAMARAS = ""

print(f"CAMARA_1: {CAMARA_1}")
print(f"CAMARA_2: {CAMARA_2}")
FECHA_ACTUAL = datetime.now().strftime("%d%m%Y")

def guardar_configuracion(clave, valor):
    """Guarda una configuración específica en el archivo config.json"""
    try:
        # Leer la configuración actual
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)

        # Actualizar el valor
        config[clave] = valor

        # Guardar la configuración actualizada
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Configuración guardada: {clave} = {valor}")

    except Exception as e:
        print(f"⚠️ Error al guardar configuración: {e}")

def verificar_o_instalar_entangle():
    '''Verifica si entangle está instalado, si no, lo instala'''
    if shutil.which("entangle") is not None:
        print("Entangle ya está instalado.")
        return

    print("Entangle no está instalado. Intentando instalar...")

    try:
        subprocess.check_call(["sudo", "apt", "update"])
        subprocess.check_call(["sudo", "apt", "install", "-y", "entangle"])
        print("Entangle instalado correctamente.")
    except subprocess.CalledProcessError as error:
        print(f"Error al instalar Entangle:\n{error}")
        sys.exit(1)
    except OSError as error:
        print(f"Error inesperado:\n{error}")
        sys.exit(1)

def instalar_xclip():
    """Instala xclip si no está presente (solo Linux)."""
    if sys.platform.startswith("linux"):
        if shutil.which("xclip") is None:
            print("xclip no está instalado. Instalando...")
            try:
                subprocess.check_call(["sudo", "apt", "update"])
                subprocess.check_call(["sudo", "apt", "install", "-y", "xclip"])
                print("xclip instalado correctamente.")
            except Exception as e: # pylint: disable=W0703
                print(f"Error al instalar xclip: {e}")
        else:
            print("xclip ya está instalado.")

if sys.platform.startswith("linux"):
    verificar_o_instalar_entangle()
    instalar_xclip()

def ingresar_nombre_archivo():
    """Ingresar el nombre que le sigue a UY-UDELAR-AGU"""
    # Crear la ventana principal
    root = tk.Tk()
    root.title("Ingresa el nombre del archivo:")

    # Obtener las dimensiones de la pantalla
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Obtener las dimensiones de la ventana
    window_width = 400  # Ancho de la ventana
    window_height = 200  # Alto de la ventana

    # Calcular las coordenadas de la posición central
    position_top = int(screen_height / 2 - window_height / 2)
    position_right = int(screen_width / 2 - window_width / 2)

    # Establecer la geometría de la ventana (concentrada)
    root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    # Eviar que el usuario cierre la ventana sin ingresar datos
    def on_closing():
        if messagebox.askyesno("Salir", "¿Seguro que quieres salir?"):
            root.destroy()
            sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Etiqueta para mostrar el mensaje
    label = tk.Label(
        root,
        text="Ingresa el nombre del archivo:\n" + PREFIJO_ARCHIVO,
        font=("Arial", 12)
    )
    label.pack(pady=10)

    # Campo de texto centrado
    nombre_archivo_var = tk.StringVar()

    # Crear un Entry centrado
    entry = tk.Entry(
        root,
        textvariable=nombre_archivo_var,
        font=("Arial", 12),
        justify="center"
    )
    entry.pack(pady=10)
    entry.focus()

    # Función de acción para el botón
    def on_ok():
        if nombre_archivo_var.get().strip():
            root.destroy()  # Cerrar la ventana
        else:
            messagebox.showerror(
                "Error",
                "No ha ingresado el nombre del archivo.\nPor favor, ingrese nuevamente."
            )

    # Botón OK
    ok_button = tk.Button(root, text="OK", command=on_ok)
    ok_button.pack(pady=10)

    entry.bind("<Return>", lambda event: ok_button.invoke())
    entry.bind("<KP_Enter>", lambda event: ok_button.invoke())

    # Iniciar la ventana
    root.mainloop()

    return nombre_archivo_var.get().upper().strip()
    # return PREFIJO_ARCHIVO + nombre_archivo_var.get().upper().strip()

if NOMBRE_INGRESADO == '':
    NOMBRE_INGRESADO = ingresar_nombre_archivo()
    guardar_configuracion("NOMBRE_INGRESADO", NOMBRE_INGRESADO)

NOMBRE_ARCHIVO = PREFIJO_ARCHIVO + NOMBRE_INGRESADO
print(NOMBRE_ARCHIVO)

# directorio = config ['DEFAULT']['directorio']
def seleccionar_directorio():
    """
    Selecciona donde se van a guardar las fotos
    """
    root = tk.Tk()
    root.withdraw()
    while True:
        carpeta_seleccionada = filedialog.askdirectory(
                                    title="Selecionar Carpeta",
                                    initialdir="/home/eddu-agu/Documentos/Book_Scan_1/Fotos"
                                )
        if carpeta_seleccionada:
            guardar_configuracion("DIRECTORIO", carpeta_seleccionada)
            return carpeta_seleccionada

        respuesta = messagebox.askretrycancel(
            "Error",
            "No se ha seleccionado ninguna carpeta. ¿Quieres intentarlo de nuevo?"
        )
        if not respuesta:  # Si el usuario presiona 'Cancelar'
            sys.exit() # cierra completamente el programa

if DIRECTORIO == '':
    directorio = seleccionar_directorio()
else:
    directorio = DIRECTORIO
print(directorio)

#Nombre que se despliega del script
TITULO = NOMBRE_ARCHIVO
UTILS_PATH = str(Path(__file__).resolve().parent / 'Utils')
ROTAR_HORARIO_PNG = UTILS_PATH + '/' + 'rotar_h.png'
ROTAR_ANTI_H_PNG = UTILS_PATH + '/' + 'rotar_anti_h.png'
LOGO_PNG = UTILS_PATH + '/' + 'logo.png'

class IconButton(ButtonBehavior, Image):
    '''Clase Icon Button'''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.opacity = 0.7  # valor base
        self.scale = 1.0
        Window.bind(mouse_pos=self._on_mouse_pos)

    def _on_mouse_pos(self, window, pos): # pylint: disable=W0613
        if not self.get_root_window():
            return
        inside = self.collide_point(*self.to_widget(*pos))
        self.opacity = 1.0 if inside else 0.7

class CustomFileChooserListView(FileChooserListView):
    '''
    Clase para deshabilitar scroll en el FileChooserListView y permitir seleccionar solo carpetas.
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Habilitar solo la navegación por teclado
        self.do_scroll_y = False  # Deshabilitar el desplazamiento vertical
        self.do_scroll_x = False  # Deshabilitar el desplazamiento horizontal

        # Establecemos la selección inicial al primer elemento
        if self.files:
            self.selected = self.files[0]  # Seleccionar el primer archivo
        else:
            self.selected = None


    def is_selected(self, filename):
        '''
        Permitir seleccionar solo carpetas (no archivos).
        '''
        return os.path.isdir(filename) and not filename.startswith('.')

class MenuButton(ButtonBehavior, BoxLayout):
    '''Clase de los botones del menú'''
    text = StringProperty('')
    hover_text = StringProperty('')
    icon_path = StringProperty('')

    def __init__(self, icon_path='', **kwargs):
        super().__init__(
            orientation='vertical',
            size_hint=(None, None),  # Cambiado a (None, None)
            width=110,
            height=80,
            **kwargs
        )

        # Textura del fondo del botón
        texture_path = resource_find('atlas://data/images/defaulttheme/button')
        texture = CoreImage(texture_path).texture if texture_path else None

        with self.canvas.before:
            if icon_path:
                Color(1, 1, 1, 0)  # Fondo transparente si hay icono
                self.rect = Rectangle(pos=self.pos, size=self.size)
            else:
                Color(*COLOR_BOTONES)
                self.rect = Rectangle(texture=texture, pos=self.pos, size=self.size)

        self.bind(pos=self._update_rect, size=self._update_rect) # pylint: disable=E1101
        self.bind(text=self._on_text) # pylint: disable=E1101

        # Crear contenedor
        self.box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            height=self.height * 0.8,
            pos_hint={'center_y': 0.5},
            padding=[0.5, 9, 0.5, 15],
            spacing=1
        )

        self.bind( # pylint: disable=E1101
            height=lambda instance,
            value: setattr(self.box, 'height', value)
        )

        # Crear labels pero con texto vacío inicialmente
        self.label_texto_1 = Label(
            halign="center",
            valign="middle",
            size_hint_y=0.5,
            bold=True,
            font_size=16,
            text_size=(100, None)  # Ancho inicial fijo, altura libre para wrapping
        )
        self.label_texto_1.bind(size=self._update_label_text_size) # pylint: disable=E1101
        self.label_texto_2 = Label(
                halign="center",
                valign="middle",
                size_hint_y=0.4,
                text_size=(100, None)  # Ancho inicial fijo para wrapping
            )
        self.label_texto_2.bind(size=self._update_label_text_size) # pylint: disable=E1101

        if not icon_path:
            self.box.add_widget(self.label_texto_1)
            self.box.add_widget(self.label_texto_2)
        else:
            icon_anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_y=0.9)
            icon_img = Image(source=icon_path, size_hint=(None, None), size=(70, 70))
            icon_anchor.add_widget(icon_img)
            self.box.add_widget(icon_anchor)

        self.add_widget(self.box)
        if not icon_path:
            self._on_text(self, self.text)

        Window.bind(mouse_pos=self.on_mouse_pos)
        self._hover = False

    def on_mouse_pos(self, window, pos):
        if self.collide_point(*self.to_widget(*pos)):
            if not self._hover:
                self._hover = True
                Window.set_system_cursor("hand")
                self.on_hover()
        else:
            if self._hover:
                self._hover = False
                Window.set_system_cursor("arrow")
                self.on_leave()

    def on_hover(self):
        # Cambia el texto del botón al hover_text
        if self.hover_text:
            self.label_texto_1.text = self.hover_text

    def on_leave(self):
        # Vuelve al texto original
        self._on_text(self, self.text)

    def _on_text(self, instance, value): # pylint: disable=W0613
        partes = value.split('\n')
        self.label_texto_1.text = partes[0] if partes else ''
        self.label_texto_2.text = partes[1] if len(partes) > 1 else ''
        self.label_texto_2.opacity = 1 if len(partes) > 1 else 0

    def _update_rect(self, *args): # pylint: disable=W0613
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _update_label_text_size(self, instance, size):
        # Para label_texto_1, configurar text_size con el ancho disponible para permitir wrapping
        if instance == self.label_texto_1:
            # Usar el ancho del contenedor menos un margen mayor para evitar desbordamiento
            instance.text_size = (size[0] - 15, None)
        elif instance == self.label_texto_2:
            # Para el segundo label, también configurar wrapping
            instance.text_size = (size[0] - 15, None)  # Ancho restringido, altura libre
        else:
            # Para otros labels, comportamiento original
            instance.text_size = size

class CamApp(App):
    '''
    CamAppp
    '''
    directorio_app = directorio
    print(f"Directorio app {directorio_app}")

    nombre_archivo_app = NOMBRE_ARCHIVO

    ruta_script = os.path.abspath(__file__)
    directorio_base = os.path.dirname(ruta_script)
    directorio_temporal = os.path.join(directorio_base, "temp")

    if not os.path.exists(directorio_temporal):
        os.makedirs(directorio_temporal)

    camaras_conectadas = False  # Flag para saber si las cámaras están conectadas
    reconnect_attempts = 0 # Contador de intentos
    max_retries = 10 # Número máximo de intentos

    layout = any

    def __init__(self, **kwargs):
        '''Método de inicialización de la clase'''
        super().__init__(**kwargs)

        self.color_botones = COLOR_BOTONES  # Color original (rojo traslúcido)

        self.numero_de_rollo = ''
        self.camara_previ = '0'
        self.lview = False
        self.img1 = Image(source = LOGO_PNG, size = (1024,768))
        self.img2 = Image(source = LOGO_PNG, size = (1024,768))
        self.title = TITULO

        self.estado_actual = self.directorio_app
        self.numero_de_rollo_anterior = ''
        self.operacion_en_curso = False
        self.timer = ''
        self.path_label = ''
        self.popup = ''
        self.error_label = ''
        self.textinput = ''
        self.camera_01 = ''
        self.camera_02 = ''
        self.camara = ''
        self.camera_der = ''
        self.camera_izq = ''
        self.cartel_rollo = ''
        self.muestro_nro_rollo = Label(text="", halign="center", valign="middle")
        self.btn0 = ''
        self.btn_toggle_cuadricula = ''

        self.tecla_calibrar = 'c'
        self.tecla_preview = 'v'
        self.tecla_editar_numero = 'b'
        self.tecla_editar_nombre = 'n'
        self.tecla_cambiar_directorio = 'm'
        self.tecla_sumar_numero = '+'
        self.tecla_abrir_carpeta = '-'
        self.tecla_config_camaras = 'e'
        self.tecla_salir = 'q'
        self.tecla_cambiar_qty_camaras = 'y'

        self.tecla_rotar_img1 = "'"
        self.tecla_rotar_img2 = '¿'
        self.tecla_toggle_cuadricula = 'l'

        self.tecla_anverso = 'w' # z
        self.tecla_reverso = 'x'

        self.btn_calibrar = MenuButton(text=f"Calibrar\n({self.tecla_calibrar})")
        self.btn_preview = MenuButton(text=f"Preview\n({self.tecla_preview})")
        self.btn_editar_numero = MenuButton(text=f"Editar Número\n({self.tecla_editar_numero})")
        self.btn_nombre = MenuButton(text=f"Editar Nombre\n({self.tecla_editar_nombre})")
        self.btn_directorio = MenuButton(text=f"Directorio\n({self.tecla_cambiar_directorio})")
        self.btn_rollo = MenuButton(text=f"Rollo\n({self.tecla_sumar_numero})")
        self.btn_abrir_carpeta = MenuButton(text=f"Abrir Carpeta\n({self.tecla_abrir_carpeta})")
        self.btn_config_camaras = MenuButton(text=f"Config Cámaras\n({self.tecla_config_camaras})")
        self.btn_toggle_cuadricula = MenuButton(text=f"Cuadrícula\n({self.tecla_toggle_cuadricula})")
        self.btn_salir = MenuButton(text=f"Salir\n({self.tecla_salir})")

        self.icono_camara = 'Utils/Iconos/camera.png'
        self.icono_anverso = 'Utils/Iconos/anverso.png'
        self.icono_reverso = 'Utils/Iconos/reverso.png'
        self.btn_anverso = MenuButton(icon_path=self.icono_anverso, text=f"Anverso\n({self.tecla_anverso})")
        self.btn_reverso = MenuButton(icon_path=self.icono_reverso, text=f"Reverso\n({self.tecla_reverso})")
        self.btn_camara = MenuButton(icon_path=self.icono_camara, text=f"Cámara\n({self.tecla_anverso})")

        self.textinput_digitos = ''
        self.botones_ajuste = ''
        self.box2 = ''

        self.cantidad_camaras = 1
        self.img1_rotation = 0
        self.img2_rotation = 0
        self.img_rotation = 0
        self.mostrar_cuadricula = True

        self.btn_rotar_v1_icon = IconButton(
            source=ROTAR_HORARIO_PNG,
            size_hint=(None, None),
            size=(64, 64)
        )
        self.btn_rotar_v1_icon.scale = 1.0
        self.btn_rotar_v1_icon.bind( # pylint: disable=no-member
            on_press=lambda w: (
                self.animar_icono(w),
                self._rotar_img1()
            )
        )
        self.btn_rotar_v1_inverso_icon = IconButton(
            source=ROTAR_ANTI_H_PNG,
            size_hint=(None, None),
            size=(64, 64)
        )
        self.btn_rotar_v1_inverso_icon.scale = 1.0
        self.btn_rotar_v1_inverso_icon.bind( # pylint: disable=no-member
            on_press=lambda w: (
                self.animar_icono(w),
                self._rotar_img1_inverso()
            )
        )
        self.btn_rotar_v2_icon = IconButton(
            source=ROTAR_HORARIO_PNG,
            size_hint=(None, None),
            size=(64, 64)
        )
        self.btn_rotar_v2_icon.scale = 1.0
        self.btn_rotar_v2_icon.bind( # pylint: disable=no-member
            on_press=lambda w: (
                self.animar_icono(w), self._rotar_img2()
            )
        )
        self.btn_rotar_v2_inverso_icon = IconButton(
            source=ROTAR_ANTI_H_PNG,
            size_hint=(None, None),
            size=(64, 64)
        )
        self.btn_rotar_v2_inverso_icon.scale = 1.0
        self.btn_rotar_v2_inverso_icon.bind( # pylint: disable=no-member
            on_press=lambda w: (
                self.animar_icono(w), self._rotar_img2_inverso()
            )
        )

        self.img2_con_botones = ''
        self.imagenes_layout = ''
        self.img1_con_botones = ''

        self.popup_qty_camaras = ''
        self.popup_calibracion = ''
        self.processing_popup = ''
        self.message_label = ''
        self.nuevo_nombre = ''
        self.popup_nombre = ''
        self.textinput_nombre = ''
        self.cartel_nombre = ''
        self.sidebar = ''
        self.main_layout = ''
        self.root_layout = ''
        self.central_layout = ''
        self._dot_event = {}

    def build(self):
        '''Crea la aplicación con sidebar a la derecha de las imágenes'''
        Window.maximize()
        Window.top = 0
        Window.left = 0

        self.asignar_camaras()

        # Layout raíz vertical: parte superior (imagenes+sidebar) y parte inferior (botonera)
        self.root_layout = BoxLayout(orientation='vertical')

        # --- Layout central: imágenes + sidebar ---
        central_layout = BoxLayout(orientation='horizontal')

        # --- Imágenes (img1 y opcionalmente img2) ---
        self.imagenes_layout = BoxLayout(orientation='horizontal')

        # img1 con botones de rotación
        botones_rotacion_1 = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            size=(140, 64),
            spacing=10,
            pos_hint={'center_x': 0.5}
        )
        botones_rotacion_1.add_widget(self.btn_rotar_v1_icon)
        botones_rotacion_1.add_widget(self.btn_rotar_v1_inverso_icon)
        self.botones_ajuste = AnchorLayout(
            anchor_x='center',
            anchor_y='top',
            size_hint=(1, None),
            height=80
        )
        self.botones_ajuste.add_widget(botones_rotacion_1)

        self.img1_con_botones = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1)
        )
        self.img1_con_botones.add_widget(self.img1)
        self.img1_con_botones.add_widget(self.botones_ajuste)

        # --- ORDEN CORRECTO: primero img1 (izquierda), luego img2 (derecha) ---
        self.imagenes_layout.clear_widgets()
        if self.cantidad_camaras == 2:
            # Si img2_con_botones es un string vacío, crearlo correctamente
            if not isinstance(self.img2_con_botones, BoxLayout):
                botones_rotacion_2 = BoxLayout(
                    orientation='horizontal',
                    size_hint=(None, None),
                    size=(140, 64),
                    spacing=10,
                    pos_hint={'center_x': 0.5}
                )
                botones_rotacion_2.add_widget(self.btn_rotar_v2_icon)
                botones_rotacion_2.add_widget(self.btn_rotar_v2_inverso_icon)
                botones_ajuste_2 = AnchorLayout(
                    anchor_x='center',
                    anchor_y='top',
                    size_hint=(1, None),
                    height=80
                )
                botones_ajuste_2.add_widget(botones_rotacion_2)
                self.img2_con_botones = BoxLayout(
                    orientation='vertical',
                    size_hint=(1, 1)
                )
                self.img2_con_botones.add_widget(self.img2)
                self.img2_con_botones.add_widget(botones_ajuste_2)
            self.imagenes_layout.add_widget(self.img2_con_botones)  # Izquierda
            self.imagenes_layout.add_widget(self.img1_con_botones)  # Derecha
        else:
            self.imagenes_layout.add_widget(self.img1_con_botones)

        # --- Sidebar a la derecha ---
        self.sidebar = BoxLayout(
            orientation='vertical',
            size_hint=(None, 1),
            width=110,
            spacing=8,
            padding=6
        )

        self.btn_preview.bind(on_press=lambda *args: self.arranca_callback(self,'1')) # pylint: disable=E1101
        self.btn_editar_numero.bind(on_press=lambda *args: self.pido_rollo()) # pylint: disable=E1101
        self.btn_salir.bind(on_press=self.btn_exit_callback) # pylint: disable=E1101
        self.btn_directorio.bind(on_press=self.cambiar_directorio) # pylint: disable=E1101
        self.btn_rollo.bind(on_press=self.aumentar_1_nro_rollo) # pylint: disable=E1101
        self.btn_abrir_carpeta.bind(on_press=self.abrir_carpeta) # pylint: disable=E1101
        self.btn_nombre.bind(on_press=lambda *args: self.cambio_nombre()) # pylint: disable=E1101
        self.btn_config_camaras.bind(on_press=self.abrir_entangle) # pylint: disable=E1101
        self.btn_toggle_cuadricula.bind(on_press=lambda *args: self.toggle_cuadricula()) # pylint: disable=E1101

        self.btn_calibrar.bind(on_press=lambda *args: self.btn0_callback_calibrar(self,'calibrar')) # pylint: disable=E1101
        self.btn_camara.bind(on_press=lambda *args: self.btn0_callback_camera_01(self,'anverso')) # pylint: disable=E1101
        self.btn_anverso.bind(on_press=lambda *args: self.btn0_callback_camera_01(self,'anverso')) # pylint: disable=E1101
        self.btn_reverso.bind(on_press=lambda *args: self.btn0_callback_camera_01(self,'reverso')) # pylint: disable=E1101

        self.sidebar.add_widget(self.btn_calibrar)
        self.sidebar.add_widget(self.btn_preview)
        self.sidebar.add_widget(self.btn_editar_numero)
        self.sidebar.add_widget(self.btn_nombre)
        self.sidebar.add_widget(self.btn_directorio)
        self.sidebar.add_widget(self.btn_rollo)
        self.sidebar.add_widget(self.btn_abrir_carpeta)
        self.sidebar.add_widget(self.btn_config_camaras)
        self.sidebar.add_widget(self.btn_toggle_cuadricula)
        self.sidebar.add_widget(self.btn_salir)

        # Agregar imágenes y sidebar al layout central
        central_layout.add_widget(self.imagenes_layout)
        central_layout.add_widget(self.sidebar)

        # --- Barra inferior (botonera principal) ---
        bottom_layout = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=90,
            pos_hint={'center_x': 0.5, 'bottom': 1}
        )
        anchor_layout = AnchorLayout(anchor_x='center', anchor_y='bottom', size_hint=(1, 1))
        scroll_view = ScrollView(
            size_hint=(1, None),
            height=90,
            do_scroll_y=False,
            do_scroll_x=True
        )
        self.box2 = GridLayout(
            cols=11,
            col_default_width=20,
            row_default_height=80,
            size_hint=(None, None)
        )
        # pylint: disable=E1101
        self.box2.bind(minimum_width=self.box2.setter('width'))

        self.box2.add_widget(self.btn_camara)
        self.box2.add_widget(self.btn_anverso)
        self.box2.add_widget(self.btn_reverso)
        # Puedes agregar más botones a self.box2 si lo necesitas

        anchor_layout.add_widget(self.box2)
        scroll_view.add_widget(anchor_layout)
        bottom_layout.add_widget(scroll_view)

        # Agregar layouts al root
        self.root_layout.add_widget(central_layout)
        self.root_layout.add_widget(bottom_layout)

        return self.root_layout

    def animar_icono(self, widget):
        '''Animar icono'''
        anim = Animation(scale=1.1, duration=0.05) + Animation(scale=1.0, duration=0.05)
        anim.start(widget)

    def _rotar_img1(self, *args): # pylint: disable=W0613
        '''Rota img1 en 90° cada vez que se presiona'''
        self.img1_rotation = (self.img1_rotation + 90) % 360
        print(f"Rotación actual de img1: {self.img1_rotation}°")

    def _rotar_img1_inverso (self, *args): # pylint: disable=W0613
        '''Rota img1 en -90° cada vez que se presiona'''
        self.img1_rotation = (self.img1_rotation - 90) % 360
        print(f"Rotación actual de img1: {self.img1_rotation}°")

    def _rotar_img2(self, *args): # pylint: disable=W0613
        '''Rota img2 en 90° cada vez que se presiona'''
        self.img2_rotation = (self.img2_rotation + 90) % 360
        print(f"Rotación actual de img2: {self.img2_rotation}°")

    def _rotar_img2_inverso (self, *args): # pylint: disable=W0613
        '''Rota img1 en -90° cada vez que se presiona'''
        self.img2_rotation = (self.img2_rotation - 90) % 360
        print(f"Rotación actual de img1: {self.img2_rotation}°")

    def asignar_camaras(self):
        """Asignar las cámaras disponibles basadas en los seriales."""
        print("Comenzando asignación de camaras")
        try:
            # Liberar cualquier cámara previamente asignada
            if hasattr(self, 'camera_02') and self.camera_02:
                try:
                    self.camera_02.exit()
                except Exception: # pylint: disable=W0703
                    pass
                self.camera_02 = None
            if hasattr(self, 'camera_01') and self.camera_01:
                try:
                    self.camera_01.exit()
                except Exception: # pylint: disable=W0703
                    pass
                self.camera_01 = None

            # pylint: disable=no-member
            camera_list = list(gp.Camera.autodetect()) # Detecta todas las cámaras conectadas
            camera_list.sort(key=lambda x: x[0]) # Ordena las cámaras por nombre (o dirección)

            port_info_list = gp.PortInfoList() # pylint: disable=no-member
            port_info_list.load() # Carga la lista de puertos disponibles

            if not camera_list:
                print("No se detectaron cámaras.")
                self.camera_01 = None
                self.camera_02 = None
                return

            asignacion_ok = True
            for name, addr in camera_list:
                print(f"Nombre y puerto: {name, addr}")
                # pylint: disable=no-member
                cam = gp.Camera()  # Inicializa la cámara que se va a asignar
                idx = port_info_list.lookup_path(addr)  # Busca la cámara en la lista de puertos
                cam.set_port_info(port_info_list[idx])  # Asigna puerto a la cámara

                try:
                    print("Inicializando cámara...")
                    cam.init() # Inicializar la camara
                    config_camara = cam.get_config()
                    # pylint: disable=no-member
                    gp_ok, serialnumber_config = gp.gp_widget_get_child_by_name(
                        config_camara,
                        'serialnumber'
                    )
                    if gp_ok >= gp.GP_OK: # pylint: disable=no-member
                        raw_value = serialnumber_config.get_value()
                        print(f"Serial detectado: {raw_value}")
                        if raw_value == CAMARA_2:
                            self.camera_01 = cam
                        elif raw_value == CAMARA_1:
                            self.camera_02 = cam
                        else:
                            print(f"No se encontró la camara {raw_value}")
                            asignacion_ok = False
                    else:
                        print(f"No se pudo obtener el número de serie para la cámara {name}.")
                        print("Config de la cámara:")
                        print(config_camara)
                        asignacion_ok = False
                except gp.GPhoto2Error as e:
                    print(f"Error obteniendo configuración de la cámara {name}: {e}")
                    asignacion_ok = False
                    #self.camara.exit()
            if not self.camera_01 or not self.camera_02:
                print("No se pudieron asignar ambas cámaras correctamente.")
                self._show_error_popup("No se pudieron asignar ambas cámaras correctamente.\nVerifique los seriales y la conexión.")
                return

            if asignacion_ok:
                print("Cámaras asignadas correctamente.")
        except gp.GPhoto2Error as e:
            print(f"Error de GPhoto2: {e}")
        except ValueError as e:
            print(f"Error de valor: {e}")
        except OSError as e:
            print(f"Error del sistema operativo: {e}")

    def key_action(self, *args):
        '''Teclas'''
        print (f"got a key event: {args[3]}")
        if args[3] == self.tecla_sumar_numero:
            self.btn_exit_callback()
        elif args[3] == self.tecla_anverso:
            self.btn0_callback_camera_01(self,'anverso')
        elif args[3] == self.tecla_reverso:
            if self.cantidad_camaras == 1:
                self.btn0_callback_camera_01(self,'reverso')
        elif args[3] == self.tecla_calibrar:
            self.btn0_callback_calibrar(self,'calibrar')
        elif args[3] == self.tecla_preview:
            self.arranca_callback(self,'1')
        elif args[3] == self.tecla_editar_numero:
            self.pido_rollo()
        elif args[3] == self.tecla_editar_nombre:
            self.cambio_nombre()
        elif args[3] == self.tecla_cambiar_directorio:
            self.cambiar_directorio()
        elif args[3] == self.tecla_abrir_carpeta:
            self.abrir_carpeta()
        elif args[3] == self.tecla_sumar_numero:
            self.aumentar_1_nro_rollo()
        elif args[3] == self.tecla_rotar_img1:
            self._rotar_img1()
        elif args[3] == self.tecla_rotar_img2:
            if self.cantidad_camaras == 2:
                self._rotar_img2()
        elif args[3] == self.tecla_toggle_cuadricula: # l
            self.toggle_cuadricula()
        elif args[3] == self.tecla_config_camaras:
            self.abrir_entangle()
        elif args[3] == self.tecla_cambiar_qty_camaras: # y
            self.cambiar_qty_camaras()
        return True

    def on_start(self):
        # Tamaño de la pantalla
        Window.clearcolor = (0.1, 0.1, 0.1, 0.2)
        Window.bind(on_request_close=self.btn_exit_callback)

        # Pregunto cuantas cámaras va a usar
        Clock.schedule_once(lambda dt: self.pido_qty_camaras(), 0.1)

        print ('arrancó')

    def pido_qty_camaras(self):
        '''Popup para seleccionar la cantidad de cámaras'''
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        mensaje = Label(
            text=MENSAJE_PIDO_QTY_CAMARAS,
            size_hint=(1, 0.4)
        )
        layout.add_widget(mensaje)

        botones = GridLayout(cols=2, spacing=10, size_hint=(1, 0.6))
        btn_1_camara = Button(text="1 Cámara")
        btn_2_camaras = Button(text="2 Cámaras")

        botones.add_widget(btn_1_camara)
        botones.add_widget(btn_2_camaras)

        layout.add_widget(botones)

        self.popup_qty_camaras = Popup(
            title="Seleccionar cantidad de cámaras",
            content=layout,
            size_hint=(None, None),
            size=(350, 250),
            auto_dismiss=False
        )

        btn_1_camara.bind( # pylint: disable=no-member
            on_release=self._set_cantidad_camaras_1
        )
        btn_2_camaras.bind( # pylint: disable=no-member
            on_release=self._set_cantidad_camaras_2
        )

        self.popup_qty_camaras.open()

    def _set_cantidad_camaras_1(self, *args): # pylint: disable=W0613
        self.cantidad_camaras = 1
        self.popup_qty_camaras.dismiss()
        # Limpiar y dejar solo img1_con_botones
        self.imagenes_layout.clear_widgets()
        self.imagenes_layout.add_widget(self.img1_con_botones)
        if self.img2.parent is not None:
            self.imagenes_layout.remove_widget(self.img2_con_botones)
        self.box2.remove_widget(self.btn_camara)
        self.pido_rollo()
        # self.crear_directorio_temporal()

    def _set_cantidad_camaras_2(self, *args): # pylint: disable=W0613
        self.cantidad_camaras = 2
        self.popup_qty_camaras.dismiss()
        # Limpiar y agregar primero img2_con_botones (izquierda), luego img1_con_botones (derecha)
        self.imagenes_layout.clear_widgets()
        # Si img2_con_botones es un string vacío, crearlo correctamente
        if not isinstance(self.img2_con_botones, BoxLayout):
            botones_rotacion = BoxLayout(
                orientation='horizontal',
                size_hint=(None, None),
                size=(140, 64),
                spacing=10,
                pos_hint={'center_x': 0.5}
            )
            botones_rotacion.add_widget(self.btn_rotar_v2_icon)
            botones_rotacion.add_widget(self.btn_rotar_v2_inverso_icon)
            botones_ajuste = AnchorLayout(
                anchor_x='center',
                anchor_y='top',
                size_hint=(1, None),
                height=80
            )
            botones_ajuste.add_widget(botones_rotacion)
            self.img2_con_botones = BoxLayout(
                orientation='vertical',
                size_hint=(1,1)
            )
            self.img2_con_botones.add_widget(self.img2)
            self.img2_con_botones.add_widget(botones_ajuste)
        self.imagenes_layout.add_widget(self.img1_con_botones)  # Izquierda
        self.imagenes_layout.add_widget(self.img2_con_botones)  # Derecha
        
        if self.btn_anverso in self.box2.children:
            self.box2.remove_widget(self.btn_anverso)
        if self.btn_reverso in self.box2.children:
            self.box2.remove_widget(self.btn_reverso)
        self.pido_rollo()
        # self.crear_directorio_temporal()

    def cambiar_qty_camaras(self):
        '''Apaga o enciende la segunda camara'''
        print(f"Cantidad de cámaras: {self.cantidad_camaras}")
        if self.cantidad_camaras == 1:
            self._set_cantidad_camaras_2()
        else:
            self._set_cantidad_camaras_1()

    def cambio_nombre(self):
        '''Ventana emergente para pedir nombre'''
        Window.unbind(on_key_down=self.key_action)

        #Layout para el popup
        self.cartel_nombre = GridLayout(cols = 1, rows = 4)

        # Etiqueta para el mensaje
        cartel = Label(
            text=f"Ingresa el nombre del archivo:\n {PREFIJO_ARCHIVO}",
            valign='middle',
            halign='center'
        )
        # Etiqueta para el mensaje de error
        self.error_label = Label(text='', color=(1, 0, 0, 1)) # Rojo para el mensaje de error

        #Botón para continuar y cancelar
        btn_archivo_nuevo = Button(text = "Continuar")
        btn_cancelar = Button(text="Cancelar")

        botones_box = BoxLayout(orientation='horizontal', spacing=10)
        botones_box.add_widget(btn_archivo_nuevo)
        botones_box.add_widget(btn_cancelar)

        # Input para nuevo nombre
        self.textinput_nombre = TextInput(
            multiline=False,
            hint_text=NOMBRE_INGRESADO
        )
        self.cartel_nombre.add_widget(cartel)
        self.cartel_nombre.add_widget(self.textinput_nombre)

        self.cartel_nombre.add_widget(self.error_label)
        self.cartel_nombre.add_widget(botones_box)

        self.popup_nombre = Popup(
            title='Ingrese nombre del archivo',
            content=self.cartel_nombre,
            size_hint=(None, None),
            size=(450, 400),
            auto_dismiss=False
        )
        self.popup_nombre.open()

        # Función para poner el foco en el campo de texto
        # pylint: disable=unused-argument
        def focus_input(*args):
            self.textinput_nombre.focus = True
        Clock.schedule_once(focus_input, 0.1)

        # Vincular el botón "Continuar" a la función de asignación del número de rollo
        # pylint: disable=no-member
        btn_archivo_nuevo.bind(on_press=self.asignar_nuevo_nombre)
        btn_cancelar.bind(on_press=self.cancelar_nuevo_nombre)

        # Vincular Enter (on_text_validate) al mismo método del botón
        # pylint: disable=no-member
        self.textinput_nombre.bind(
            on_text_validate=lambda instance: btn_archivo_nuevo.trigger_action(duration=0.1)
        )

    def cancelar_nuevo_nombre(self, *args): # pylint: disable=W0613
        '''Cerrar el popup de nombre'''
        Window.bind(on_key_down=self.key_action)
        self.popup_nombre.dismiss()

    def asignar_nuevo_nombre(self, *args): # pylint: disable=W0613
        '''Asigno nuevo nombre'''
        try:
            Window.unbind(on_key_down=self.key_action)
            # Obtener el texto ingresado y quitar espacios extra
            self.nuevo_nombre = self.textinput_nombre.text.strip().upper()

            # Verificar que el campo no esté vacío
            if self.nuevo_nombre:
                print(f"Nuevo nombre ingresado: {self.nuevo_nombre}")
                # TODO: GUARDAR EN CONFIG

                self.nombre_archivo_app = PREFIJO_ARCHIVO + self.nuevo_nombre
                print(f"Nombre del archivo actualizado: {self.nombre_archivo_app}")
                self.title = self.nombre_archivo_app

                Window.bind(on_key_down=self.key_action)

                # Cerrar el popup
                self.popup_nombre.dismiss()
            else:
                self.error_label.text = "Debe ingresar un nuevo nombre" # Mensaje de error
        except Exception as error: # pylint: disable=W0718
            print(f"Error: {error}")
            # Si el valor no se puede conovertir a número, mostrar mensaje de error
            self.error_label.text = "Debe ingresar un nuevo nombre" # Mensaje de error
            self.textinput_nombre.text = '' # Limpiar el campo texto
            Window.unbind(on_key_down=self.key_action)

    def pido_rollo(self):
        '''Ventana emergente para pedir el número de rollo'''
        Window.unbind(on_key_down=self.key_action)

        path = self.directorio_app #directorio
        # paths = sorted(Path(path).iterdir(), key=os.path.getmtime, reverse=True)

        ultimo_rollo = ""
        print('Data:', self.numero_de_rollo, path)

        # Crear el layout del popup
        self.cartel_rollo = GridLayout(cols = 1, rows = 7)

        # Etiqueta para el mensaje
        cartel = Label(
            text=MENSAJE_PIDO_ROLLO,
            valign='middle'
        )

        # Etiqueta para el mensaje de error
        self.error_label = Label(text='', color=(1, 0, 0, 1)) # Rojo para el mensaje de error

        #Botón para continuar
        archivo_nuevo = Button(text = "Continuar")

        # Agregar widgets al layout
        self.cartel_rollo.add_widget(cartel)

        # Etiqueta "Cantidad de dígitos"
        label_digitos = Label(
            text="Cantidad de dígitos",
            size_hint_y=None,
            height=30,
            valign='middle'
        )

        if self.textinput_digitos:
            digitos = self.textinput_digitos.text
        else:
            digitos = '4'

        # Input para asignar entre 1 y 4
        self.textinput_digitos = TextInput(
            text=digitos,
            input_filter='int',
            multiline=False,
            hint_text="Cantidad de dígitos"
        )

        # Etiqueta "Número de rollo"
        label_num_rollo = Label(
            text="Número de Página",
            size_hint_y=None,
            height=30,
            valign='middle'
        )

        if self.numero_de_rollo:
            ultimo_rollo = int(self.numero_de_rollo)

        # Campo de entrada para el número de rollo
        self.textinput = TextInput(
            text=str(ultimo_rollo),
            unfocus_on_touch=False,
            multiline = False,
            input_filter='int',
            hint_text="Número de Página",
        )

        # Agrega la etiqueta y el spinner al layout
        self.cartel_rollo.add_widget(label_digitos)
        self.cartel_rollo.add_widget(self.textinput_digitos)
        self.cartel_rollo.add_widget(label_num_rollo)
        self.cartel_rollo.add_widget(self.textinput)
        self.cartel_rollo.add_widget(self.error_label)

        # Agregar el botón "Continuar"
        self.cartel_rollo.add_widget(archivo_nuevo)

        self.popup = Popup(
            title='Ingrese Número de Página y Cantidad de Dígitos',
            content=self.cartel_rollo,
            size_hint=(None, None),
            size=(450, 400),
            auto_dismiss=False
        )
        self.popup.open()

        # Función para poner el foco en el campo de texto
        # pylint: disable=unused-argument
        def focus_input(*args):
            self.textinput.focus = True
        Clock.schedule_once(focus_input, 0.1)

        # Vincular el botón "Continuar" a la función de asignación del número de rollo
        # pylint: disable=no-member
        archivo_nuevo.bind(on_press=self.asignar_numero_rollo)

        # Vincular Enter (on_text_validate) al mismo método del botón
        # pylint: disable=no-member
        self.textinput.bind(
            on_text_validate=lambda instance: archivo_nuevo.trigger_action(duration=0.1)
        )

        # Crea el directorio temporal
        self.crear_directorio_temporal()
        #return

    def asignar_numero_rollo(self, *args): # pylint: disable=unused-argument
        '''Asigna el numero de rollo'''
        try:
            Window.bind(on_key_down=self.key_action)
            # Obtener el texto ingresado y quitar espacios extra
            self.numero_de_rollo = self.textinput.text.strip()

            # Verificar que el campo no esté vacío
            if self.numero_de_rollo:
                # Intentar convertir a entero para asegurar que es un número
                num_rollo = int(self.numero_de_rollo)

                cantidad_digitos_text = self.textinput_digitos.text.strip()
                if cantidad_digitos_text:
                    cantidad_digitos = int(cantidad_digitos_text)
                else:
                    self.error_label.text = "Por favor, ingrese la cantidad de dígitos."
                    return

                # Formatear con ceros a la izquierda
                self.numero_de_rollo = f"{num_rollo:0{cantidad_digitos}d}"

                # Actualizar la interfaz con el número de rollo
                self.muestro_nro_rollo.text = self.numero_de_rollo
                print('Num Rollo',self.numero_de_rollo)
                self.btn_rollo.text = f"+ ítem ({self.tecla_sumar_numero})\n" + self.numero_de_rollo

                Window.bind(on_key_down=self.key_action)

                # Cerrar el popup
                self.popup.dismiss()

                # Llamar al callback para continuar con el flujo
                self.arranca_callback(self,'1')
            else:
                # Si el campo está vacío, mostrar mensaje de error
                self.error_label.text = "Por favor, ingrese un número válido."
                self.textinput.text = '' # Limpiar el campo texto
        except ValueError:
            # Si el valor no se puede conovertir a número, mostrar mensaje de error
            self.error_label.text = "Debe ingresar un número válido." # Mensaje de error
            self.textinput.text = '' # Limpiar el campo texto

    def crear_directorio (self):
        '''Crea directorio si es necesario'''
        path = self.directorio_app+self.numero_de_rollo

        try:
            os.mkdir(path)
        except OSError:
            print (f"Falló la creación del directorio {path}. Ya existe?")
        else:
            print (f"Se creó el directorio: {path} ")

    def crear_directorio_temporal(self):
        '''Crea carpeta temp'''
        path = self.directorio_temporal

        try:
            os.mkdir(path)
        except OSError:
            print (f"Falló la creación del directorio temporal {path} . Ya existe?")
        else:
            print (f"Se creó el directorio temporal: {path} ")

    def eliminar_directorio_temporal(self):
        '''Elimina carpeta temp'''
        # path = f"{self.directorio_app}/temp/"
        path = self.directorio_temporal
        print(f"Eliminando directorio temporal: {path}")
        try:
            shutil.rmtree(path)
        except shutil.Error:
            print (f"Falló la creación del directorio temporal {path} . Ya existe?")
        else:
            print (f"Se eliminó el directorio temporal: {path} ")

    def arranca_callback(self, *args):
        '''Callback'''
        if self.lview:
            self.timer = Clock.unschedule(self.update, 2)

        self.camara_previ = args[1]
        self.lview = True
        print ('Self.camara_previ', self.camara_previ)
        self.timer = Clock.schedule_interval(self.update, 1.0/24.0)
        self.loading_cursor(False)

    def _show_processing_popup(self, mensaje="Procesando..."):
        print("Mostrando popup:", mensaje)
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Crear el mensaje que se actualizará
        self.message_label = Label(
            text=mensaje,
            font_size='18sp',
            size_hint=(1, 0.2)
        )

        hint_label = Label(
            text="Paciencia... este proceso puede durar unos minutos",
            font_size='12sp',
            size_hint=(1, 0.2),
            color=(0.6, 0.6, 0.6, 1)
        )

        box.add_widget(self.message_label)
        box.add_widget(hint_label)

        self.processing_popup = Popup(
            title='Procesando',
            content=box,
            size_hint=(None, None),
            size=(300, 200),
            auto_dismiss=False
        )
        self.processing_popup.open()

    def _cerrar_processing_popup(self):
        '''Cancelar el ciclo de puntos si está corriendo'''
        if hasattr(self, '_dot_event') and self._dot_event:
            self._dot_event.cancel() # pylint: disable=no-member
            self._dot_event = None

        # Cerrar el popup
        if hasattr(self, 'processing_popup') and self.processing_popup:
            self.processing_popup.dismiss()
            self.processing_popup = None

    def _show_error_popup(self, mensaje="Ha ocurrido un error"):
        if hasattr(self, 'processing_popup') and self.processing_popup:
            self.processing_popup.dismiss()

        box = BoxLayout(orientation='vertical', padding=20, spacing=10)
        box.add_widget(Label(text=mensaje))
        btn = Button(text='Cerrar', size_hint_y=None, height=40)
        box.add_widget(btn)

        error_popup = Popup(
            title='Error',
            content=box,
            size_hint=(None, None),
            size=(600, 250),
            auto_dismiss=False
        )
        btn.bind(on_release=error_popup.dismiss) # pylint: disable=E1101
        error_popup.open()

    def btn0_callback(self, *args):
        '''Camara Marco - Anverso/Reverso'''
        self.capture_and_save_image(self.camera_02, args, 'camera_02')

    def btn0_callback_camera_01(self, *args):
        '''Camara Diapo'''
        print(f"Tomando fotos de {self.cantidad_camaras} camaras")
        def despues_de_primera():
            print("camara 1 guardada")
            self.aumentar_1_nro_rollo()
            if self.cantidad_camaras == 2:
                ajustada = (self.img2_rotation + 180) % 360
                if ajustada == 0 or ajustada == 180:
                    self.img_rotation = ajustada + 180
                else:
                    self.img_rotation = ajustada
                self.capture_and_save_image(
                    self.camera_02, args,
                    'camera_02',
                    on_done=lambda: print("camara 2 guardada")
                )
                self.aumentar_1_nro_rollo()

        if self.img1_rotation == 0 or self.img1_rotation == 180:
            self.img_rotation = self.img1_rotation + 180
        else:
            self.img_rotation = self.img1_rotation

        self.capture_and_save_image(self.camera_01, args, 'camera_01', on_done=despues_de_primera)

    def _mostrar_confirmacion_calibrar(self, callback, tipo_mensaje):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        mensaje = Label(
            text=f"¿Deseás calibrar {tipo_mensaje}?",
            size_hint=(1, 0.6)
        )
        layout.add_widget(mensaje)

        botones = BoxLayout(size_hint=(1, 0.4), spacing=10)
        btn_si = Button(text="Sí")
        btn_no = Button(text="No")
        botones.add_widget(btn_si)
        botones.add_widget(btn_no)
        layout.add_widget(botones)

        self.popup = Popup(
            title="Confirmación",
            content=layout,
            size_hint=(None, None),
            size=(300, 200),
            auto_dismiss=False
        )

        btn_si.bind(on_release=lambda instancia: callback(instancia, 1)) # pylint: disable=E1101
        btn_no.bind(on_release=lambda instancia: callback(instancia, 0)) # pylint: disable=E1101

        self.popup.open()

    def _iniciar_calibracion(self, args, tipo):
        if hasattr(self, 'popup_calibracion') and self.popup_calibracion:
            # Si el popup ya está abierto, no lo volvemos a mostrar
            print("El popup ya está abierto, no se abrirá nuevamente")
            self.popup_calibracion.dismiss()
            self.popup_calibracion = None

        self._capturar_calibracion(args, tipo)

    def _capturar_calibracion(self, args, tipo):
        def despues_de_primera():
            print("Primera calibración completada")
            if self.cantidad_camaras == 2:
                ajustada = (self.img2_rotation + 180) % 360
                if ajustada == 0 or ajustada == 180:
                    self.img_rotation = ajustada + 180
                else:
                    self.img_rotation = ajustada

                self._show_processing_popup(f"Calibrando {tipo} en cámara 2...")
                self.capture_and_save_image(
                    self.camera_02, args, 'camera_02', True, tipo,
                    on_done=lambda: print("Segunda calibración completada")
                )

        self._show_processing_popup(f"Calibrando {tipo}...")

        if self.img1_rotation == 0 or self.img1_rotation == 180:
            self.img_rotation = self.img1_rotation + 180
        else:
            self.img_rotation = self.img1_rotation

        self.capture_and_save_image(
            self.camera_01, args, 'camera_01', True, tipo,
            on_done=despues_de_primera
        )

    def btn0_callback_calibrar(self, *args):
        '''Función para calibrar las cámaras'''
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        mensaje = Label(
            text="¿Qué calibración deseás realizar?",
            size_hint=(1, 0.4)
        )
        layout.add_widget(mensaje)

        botones = GridLayout(cols=2, spacing=10, size_hint=(1, 0.6))
        btn_iluminacion = Button(text="Iluminación")
        btn_color = Button(text="Color")
        btn_formas = Button(text="Formas")
        btn_cancelar = Button(text="Cancelar")

        botones.add_widget(btn_iluminacion)
        botones.add_widget(btn_color)
        botones.add_widget(btn_formas)
        botones.add_widget(btn_cancelar)

        layout.add_widget(botones)

        self.popup_calibracion = Popup(
            title="Seleccionar calibración",
            content=layout,
            size_hint=(None, None),
            size=(350, 250),
            auto_dismiss=False
        )

        btn_iluminacion.bind( # pylint: disable=E1101
            on_release=lambda instancia: self._iniciar_calibracion(args, 'iluminacion')
        )
        btn_color.bind( # pylint: disable=E1101
            on_release=lambda instancia: self._iniciar_calibracion(args, 'color')
        )
        btn_formas.bind( # pylint: disable=E1101
            on_release=lambda instancia: self._iniciar_calibracion(args, 'forma')
        )
        btn_cancelar.bind( # pylint: disable=E1101
            on_release=lambda instancia: self.popup_calibracion.dismiss()
        )

        self.popup_calibracion.open()

    def capture_and_save_image(
            self, camera, args, camera_type,
            calibrar=False, tipo=None, on_done=None
    ):
        '''Lógica común para capturar y guardar imagen de cualquier cámara'''
        if hasattr(self, 'operacion_en_curso') and self.operacion_en_curso:
            print("Otra operación está en curso. Espera a que termine.")
            return
        self.operacion_en_curso = True
        if camera_type == 'camera_01':
            nombre_camara = 'camara_1'
        else:
            nombre_camara = 'camara_2'
        try:
            # Cancelamos cualquier temporizador previo antes de realizar cualquier acción
            if hasattr(self, 'timer') and self.timer:
                Clock.unschedule(self.timer)
                print("Temporizador cancelado")

            self.loading_cursor()
            print(f'Camera {camera_type} Canon')

            ## Desactivo el reloj
            print(f"Timer {self.timer}")
            self.timer = Clock.unschedule(self.update)
            Clock.schedule_once(self._despues_de_esperar, TIEMPO_ESPERA)

            ## Me traigo dónde dejará la captura
            file_path = camera.capture(gp.GP_CAPTURE_IMAGE) # pylint: disable=no-member
            print(f'Camera {camera_type} file path: {file_path.folder}/{file_path.name}')

            # Nombre y destino de la imagen
            parametro = '-' + str(args[1])
            if self.cantidad_camaras == 2:
                parametro = ''

            nombre = self.nombre_archivo_app + '-' +str(self.numero_de_rollo) + parametro + '.jpg'
            target = os.path.join(self.directorio_app, nombre)
            print('Copying image to', target)

            # Verificación extra antes de comprobar existencia del archivo
            if not os.path.isdir(self.directorio_app):
                print(f"ERROR: El directorio '{self.directorio_app}' no existe.")
                self.operacion_en_curso = False
                return

            # Guardar imagen temporal
            camera_file = camera.file_get(
                file_path.folder,
                file_path.name,
                gp.GP_FILE_TYPE_NORMAL # pylint: disable=no-member
            )
            target_temp = os.path.join(self.directorio_temporal, args[1] + '-' + file_path.name)
            print("Guardando imagen temporal")

            try:
                camera_file.save(target_temp)
                img = Imge.open(target_temp)
                print(f"Rotating image by {self.img_rotation} degrees")
                img = img.rotate(self.img_rotation, expand=True)
                img.save(target_temp)
                print("Luego de guardar la imagen temporal")
            except Exception as e: # pylint: disable=W0718
                self.operacion_en_curso = False
                print(f"Error al guardar la imagen temporal Camera {camera_type}: {e}")
                self.loading_cursor(False)
                self._cerrar_processing_popup()
                self._show_error_popup(f"Ocurrió un error: {e}")
                return

            # Verificación de si el popup ya está abierto
            #if hasattr(self, 'popup') and self.popup.parent:
            #    self.operacion_en_curso = False
            #    return  # Si el popup ya está abierto, no permitir abrir otro

            def save_image():
                self.loading_cursor()
                print("Copying image to ", target)
                print("Nombre camara: ", nombre_camara)
                try:
                    camera_file = camera.file_get(
                        file_path.folder,
                        file_path.name,
                        gp.GP_FILE_TYPE_NORMAL # pylint: disable=E1101
                    )
                    camera_file.save(target)
                    img = Imge.open(target)
                    img = img.rotate(self.img_rotation, expand=True)
                    img.save(target)
                except Exception as e: # pylint: disable=W0718
                    self.operacion_en_curso = False
                    print(f"Error al guardar la imagen Camera {camera_type}: {e}")
                    self.loading_cursor(False)
                    self._cerrar_processing_popup()
                    self._show_error_popup(f"Ocurrió un error: {e}")
                    return

                typ, data = camera.wait_for_event(200)
                attempts = 10
                while typ != gp.GP_EVENT_TIMEOUT and attempts > 0: # pylint: disable=no-member
                    if typ == gp.GP_EVENT_FILE_ADDED: # pylint: disable=no-member
                        print(f'Camera: {camera_type} - file path: {data.folder}/{data.name}')

                        parametro = '-' + str(args[1])
                        print('Parametro: ',parametro)
                        if parametro == '-calibrar':
                            parametro = nombre_camara + '-' + tipo
                        elif self.cantidad_camaras == 2:
                            parametro = ''

                        raw_nombre = (
                            self.nombre_archivo_app +
                            str(self.numero_de_rollo) +
                            parametro +
                            '.cr3'
                        )
                        raw_target = os.path.join(self.directorio_app, raw_nombre)
                        print('Copying image to', raw_target)
                        try:
                            camera_file = camera.file_get(
                                data.folder,
                                data.name,
                                gp.GP_FILE_TYPE_NORMAL # pylint: disable=no-member
                            )
                            camera_file.save(raw_target)
                        except Exception as e: # pylint: disable=W0718
                            print(f"Error al guardar RAW: {e}")

                        try:
                            camera.file_delete(data.folder, data.name)
                            print(f"Archivo RAW eliminado: {data.folder}/{data.name}")
                        except gp.GPhoto2Error as e:
                            print(f"Error eliminando archivo RAW: {e}")

                    typ, data = camera.wait_for_event(1)
                    attempts -= 1

            if calibrar:
                nombre_camara = 'camara_1'
                if camera_type == 'camera_02':
                    nombre_camara = "camara_2"

                print(f"Target: {target}")
                if tipo == 'iluminacion':
                    print("Iniciando análisis de intensidad...")
                    # Aquí vamos a analizar la imagen capturada
                    image_calibrar = self.analyze_intensity_of_image(target_temp)
                    #highlighted_image_path = target_temp.replace('.jpg', f'-highlighted.jpg')

                    # Guardar la imagen procesada con un nombre diferente
                    image_calibrar_path = os.path.join(
                        self.directorio_app,
                        f"{FECHA_ACTUAL}-{nombre_camara}-iluminacion.jpg"
                    )
                    image_calibrar.save(image_calibrar_path)
                    print(f"Imagen calibrada guardada en: {image_calibrar_path}")

                    self._cerrar_processing_popup()
                    save_image()
                    if os.path.exists(target):
                        os.remove(target)
                elif tipo == 'color' or tipo == 'forma':
                    print(f"Calibrar {tipo}")
                    target = os.path.join(
                        self.directorio_app,
                        f"{FECHA_ACTUAL}-{nombre_camara}-{tipo}.jpg"
                    )
                    save_image()
                    # Mostrar popup solo como confirmación visual
                    self._cerrar_processing_popup()

                else:
                    print(f"tipo recibido: {tipo}, calibrar: {calibrar}")
            else:
                self._cerrar_processing_popup()
                save_image()

            self.operacion_en_curso = False
            try:
                camera.file_delete(file_path.folder, file_path.name)
            except gp.GPhoto2Error as e:
                self.operacion_en_curso = False
                print(f"Error deleting file: {e}")
                self._cerrar_processing_popup()
                self._show_error_popup("Mensaje del error...")
            if on_done:
                on_done()
            try:
                camera.exit()
                camera.init()
            except Exception as e: # pylint: disable=W0718
                print(f"Error al reiniciar la cámara {camera_type}: {e}")

        except (gp.GPhoto2Error, FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error durante la operación: {e}")
            self.operacion_en_curso = False
            self._cerrar_processing_popup()
            self._show_error_popup(f"Ocurrió un error: {e}")

    def _show_confirmation_popup(self, target, target_temp, save_image=None, on_done=None):
        self.loading_cursor(False)
        def on_confirm(instance=None): # pylint: disable=unused-argument
            self.loading_cursor()
            self.popup.dismiss()
            self.timer = Clock.schedule_interval(self.update, 1.0 / 24.0)

            if callable(save_image):
                try:
                    save_image()
                except Exception as e: # pylint: disable=W0718
                    print(f"Error al ejecutar save_image(): {e}")
            if callable(on_done):
                on_done()

            if os.path.exists(target_temp):
                os.remove(target_temp)

            self.loading_cursor(False)
            self.operacion_en_curso = False

        def on_cancel(instance=None): # pylint: disable=unused-argument
            self.loading_cursor(False)
            self.popup.dismiss()
            self.timer = Clock.schedule_interval(self.update, 1.0 / 24.0)
            if os.path.exists(target_temp):
                os.remove(target_temp)
            if os.path.exists(target):
                os.remove(target)
            print("Operación cancelada por el usuario.")
            self.operacion_en_curso = False
            Clock.schedule_once(self._despues_de_esperar, TIEMPO_ESPERA)

        box = BoxLayout(orientation='vertical', spacing=10, padding=10)
        img_preview = Image(
            source=target_temp,
            size_hint=(None, None),
            size=(800, 600),
            pos_hint={'center_x': 0.5}
        )

        btn_yes = Button(text="Sí", size_hint_y=None, height=40)
        btn_no = Button(text="No", size_hint_y=None, height=40)

        btn_yes.bind(on_release=on_confirm) # pylint: disable=E1101
        btn_no.bind(on_release=on_cancel) # pylint: disable=E1101

        print(f"Target: {target}")
        print(f"Exite? {os.path.isfile(target)}")
        if os.path.isfile(target):
            label_popup = (f"El archivo '{os.path.basename(target)}' " +
                            "ya existe. ¿Desea sobreescribirlo?")
        else:
            label_popup = "¿Desea guardar la imágen?"

        box.add_widget(Label(
            text=label_popup
        ))
        box.add_widget(img_preview)
        box.add_widget(btn_yes)
        box.add_widget(btn_no)

        self.popup = Popup(
            title="Confirmación",
            content=box,
            size_hint=(None, None),
            size=(1024, 768),
            auto_dismiss=False
        )
        self.popup.open()

    def btn_exit_callback(self, *args): # pylint: disable=unused-argument
        '''Salir del programa'''
        self.eliminar_directorio_temporal()
        if self.cantidad_camaras == 2:
            self.camera_02.exit()
            self.camera_02.init()
        self.camera_01.exit()
        self.camera_01.init()
        App.get_running_app().stop()

    def _despues_de_esperar(self, dt): # pylint: disable=unused-argument
        # Código a ejecutar después de la espera de 2 segundos
        print(f"Esperando {TIEMPO_ESPERA} segundos...")
        print(" para que la cámara termine la operación anterior...")
        self.loading_cursor(False)

    def capture_preview_from_camara(self, camera, camera_id):
        '''Captura la vista previa de la cámara indicada'''
        # print(f"camera: {camera}, camera_id: {camera_id}")
        num_camara = 1
        if camera_id == 'camera_02':
            num_camara = 2

        if not hasattr(camera, "capture_preview"):
            error_message = (f"Error: La cámara {num_camara} no está disponible o es inválida.\n"+
                             "Debe de reiniciar o encender las cámaras")
            print(error_message)
            self.show_error_dialog(error_message)
            return None
        try:
            return camera.capture_preview()
        except gp.GPhoto2Error as e:
            print(f"Error al capturar la vista previa de {camera_id}: {e}")

        return None

    def show_error_dialog(self, message):
        '''Muestra un popup de error con un botón para cerrar la aplicación.'''
        try:
            Clock.unschedule(self.update)
        except Exception: # pylint: disable=W0718
            pass
        try:
            Window.unbind(on_key_down=self.key_action)
        except Exception: # pylint: disable=W0718
            pass

        if hasattr(self, 'popup') and self.popup.parent:
            self.popup.dismiss()

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        message_label = Label(text=message, size_hint=(1, 0.7))
        close_button = Button(text="Cerrar", size_hint=(1, 0.3))
        layout.add_widget(message_label)
        layout.add_widget(close_button)

        popup = Popup(
            title="Error",
            content=layout,
            size_hint=(None, None),
            size=(500, 200),
            auto_dismiss=False  # Evita que el usuario cierre el popup sin el botón
        )

        def close_app(instance): # pylint: disable=unused-argument
            popup.dismiss()
            App.get_running_app().stop()
            sys.exit()  # Cierra la aplicación cuando el usuario presiona "Cerrar"

        # Botón "Cerrar"
        close_button.bind(on_press=close_app) # pylint: disable=E1101
        popup.open()

    def update(self, *args): # pylint: disable=unused-argument
        '''Update'''
        capture = None
        # Intentamos capturar la vista previa de las cámaras
        capture = self.capture_preview_from_camara(self.camera_01, 'camera_01')
        capture_2 = False
        if self.cantidad_camaras == 2:
            capture_2 = self.capture_preview_from_camara(self.camera_02, 'camera_02')

        if capture:
            # Procesamiento de la imagen
            filedata = capture.get_data_and_size()
            image = Imge.open(io.BytesIO(filedata))
            image_array = np.asarray(image)
            image_array = np.fliplr(image_array)

            # Aplicar rotación de acuerdo a self.img1_rotation
            if self.img1_rotation == 90:
                rotated_image = np.rot90(image_array, k=1)
            elif self.img1_rotation == 180:
                rotated_image = np.rot90(image_array, k=2)
            elif self.img1_rotation == 270:
                rotated_image = np.rot90(image_array, k=3)
            else:
                rotated_image = image_array

            preview_array = rotated_image
            if self.mostrar_cuadricula:
                preview_array = self.aplicar_cuadricula(preview_array)

            video_texture = Texture.create(
                size=(preview_array.shape[1], preview_array.shape[0]),
                colorfmt='bgr'
            )

            video_texture.blit_buffer(
                preview_array.tobytes(),
                colorfmt='rgb',
                bufferfmt='ubyte'
            )

            # Asignar la textura a la iagen de Kivy
            self.img1.texture = video_texture
            self.img1.allow_stretch = True
            self.img1.keep_ratio = True
        else:
            print("No se pudo capturar la vista previa de la cámara 1.")
        if self.cantidad_camaras == 2:
            if capture_2:
                # Procesamiento de la imagen
                filedata = capture_2.get_data_and_size()
                image = Imge.open(io.BytesIO(filedata))
                image_array = np.asarray(image)
                image_array = np.fliplr(image_array)

                # Aplicar rotación de acuerdo a self.img_rotation
                ajustada = (self.img2_rotation + 180) % 360
                if ajustada == 90:
                    rotated_image = np.rot90(image_array, k=1)
                elif ajustada == 180:
                    rotated_image = np.rot90(image_array, k=2)
                elif ajustada == 270:
                    rotated_image = np.rot90(image_array, k=3)
                else:
                    rotated_image = image_array

                preview_array = rotated_image
                if self.mostrar_cuadricula:
                    preview_array = self.aplicar_cuadricula(preview_array)

                # Crear una textura con la imagen para Kivy
                video_texture = Texture.create(
                    size=(preview_array.shape[1], preview_array.shape[0]),
                    colorfmt='bgr'
                )
                video_texture.blit_buffer(
                    preview_array.tobytes(),
                    colorfmt='rgb',
                    bufferfmt='ubyte'
                )

                # Asignar la textura a la iagen de Kivy
                self.img2.texture = video_texture
                self.img2.allow_stretch = True
                self.img2.keep_ratio = True
            else:
                print("No se pudo capturar la vista previa de la cámara 2.")

    def aplicar_cuadricula(self, image_array, lineas=6, color=(180, 180, 180), thickness=1):
        '''Dibuha una cuadrícula sobre un array de imagen'''
        result = image_array.copy()
        h, w, _ = result.shape

        # Lineas verticales
        for i in range(1,lineas):
            x = i * w // lineas
            cv2.line(result, (x, 0), (x, h), color, thickness) # pylint: disable=E1101

        # Lineas horizontales
        for i in range(1, lineas):
            y = i * h // lineas
            cv2.line(result, (0, y), (w, y), color, thickness) # pylint: disable=E1101

        cv2.rectangle(result, (0, 0), (w - 1, h - 1), color, thickness) # pylint: disable=E1101

        return result

    def toggle_cuadricula(self):
        '''Mostrar cuadricula en preview'''
        self.mostrar_cuadricula = not self.mostrar_cuadricula
        print(f"Cuadrícula {'activada' if self.mostrar_cuadricula else 'desactivada'}")

    def analyze_intensity_of_image(self, image_path):
        '''
        Analiza la intensidad de luz de la imagen capturada
        y resalta los píxeles según su intensidad
        '''

        # Cargar la imagen
        image = Imge.open(image_path)
        image_array = np.asarray(image)

        # Convertir la imagen a luminancia con la fórmula Y = 0.299 * R + 0.587 * G + 0.114 * B
        luminance_image = np.dot(image_array[...,:3], [0.299, 0.587, 0.114])
        # Obtener el tamaño de la imagen
        height, width = luminance_image.shape

        # Obtener las coordenadas del píxel central
        center_y = height // 2
        center_x = width // 2

        # Obtener la luminancia del píxel central
        center_luminance = luminance_image[10, 10]

        # Imprimir el valor de luminancia del píxel central en consola
        print(f"Luminancia del píxel 10,10 ({center_x}, {center_y}): {int(center_luminance)}")


        # Definir umbrales para los colores
        umbral_max = 240  # Intensidad mayor a este valor será rojo
        umbral_min = 210  # Intensidad menor a este valor será azul

        # Crear una copia de la imagen para no modificar la original
        highlighted_image = np.copy(image_array)

        # Recorrer todos los píxeles y aplicar el color correspondiente según la intensidad de luz
        for y in range(highlighted_image.shape[0]):
            for x in range(highlighted_image.shape[1]):
                intensidad = int(luminance_image[y, x])

                if intensidad >= umbral_max:
                    # Píxel rojo para intensidades altas
                    highlighted_image[y, x] = [255, 0, 0]  # Rojo (RGB)
                elif intensidad < umbral_min:
                    # Píxel verde para intensidad baja
                    highlighted_image[y, x] = [0, 0, 255]  # Azul (RGB)
                else:
                    # Píxel con intensidad ok (azul o negro)
                    highlighted_image[y, x] = [0, 255, 0]  # Verde (RGB) o [0, 0, 0] para negro

        # Guardar la imagen resaltada
        highlighted_image_path = image_path.replace('.jpg', '-highlighted.jpg')
        highlighted_image = Imge.fromarray(highlighted_image)
        highlighted_image.save(highlighted_image_path)
        print(f"Imagen con intensidad resaltada guardada en {highlighted_image_path}")
        return highlighted_image

    def mostrar_pregunta(self, callback):
        ''' Muestra un popup con una pregunta de Sí o No '''
        # Esperamos 2 segundo antes de continuarr para dar tiempo a la cámara a terminar
        print("Esperando 2 segundo para que la cáamara termina la operación anterior...")
        Clock.schedule_once(self._despues_de_esperar, TIEMPO_ESPERA)

        if hasattr(self, 'popup') and self.popup.parent:
            # Si el popup ya está abierto, no lo volvemos a mostrar
            print("El popup ya está abierto, no se abrirá nuevamente")
            self.popup.dismiss()

        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text="¿Desea finalizar?", size_hint_y=None, height=50)

        botones = BoxLayout(orientation='horizontal', spacing=10)
        btn_si = Button(text="Sí")
        btn_no = Button(text="No")

        botones.add_widget(btn_si)
        botones.add_widget(btn_no)

        box.add_widget(label)
        box.add_widget(botones)

        # Vincular botones a las funciones correspondientes
        # pylint: disable=no-member
        btn_si.bind(on_press=lambda instance: self._cerrar_popup(callback, True))
        # pylint: disable=no-member
        btn_no.bind(on_press=lambda instance: self._cerrar_popup(callback, False))

        self.popup = Popup(
            title="Finalizar proceso",
            content=box,
            size_hint=(None, None),
            size=(400, 200),
            auto_dismiss=False
        )
        self.popup.open()

        self.loading_cursor(False)

    def _cerrar_popup(self, callback, respuesta):
        ''' Cierra el popup y llama a la función de callback con la respuesta '''
        Clock.schedule_once(lambda dt: self.popup.dismiss(), 0.1)
        # Ensure the callback is invoked only after the popup is dismissed
        Clock.schedule_once(lambda dt: callback(respuesta), 0.2)

    def aumentar_1_nro_rollo(self, *args): # pylint: disable=W0613
        '''Función para aumentar en 1 el nro de rollo'''
        self.textinput.text = str(int(self.numero_de_rollo) + 1)
        print(f'Nuevo numero de rollo: {self.textinput.text}')
        self.asignar_numero_rollo()

    def abrir_carpeta(self, *args): # pylint: disable=W0613
        '''Función para abrir la carpeta desitno'''
        try:
            subprocess.run(["xdg-open", self.directorio_app], check=False)
        except subprocess.CalledProcessError as e:
            print(f"Occurió un error al intentar abrir la carpeta: {e}")

    def loading_cursor(self, wait = True):
        '''Cargando'''
        if wait:
            Window.set_system_cursor("wait")
        else:
            Window.set_system_cursor("arrow")

    def close_popup(self, *args): # pylint: disable=unused-argument
        '''Cierre popup'''
        self.popup.dismiss()

    def cambiar_directorio(self, *args): # pylint: disable=unused-argument
        '''Solucionar la selección'''
        chooser = CustomFileChooserListView(dirselect=True)

        # Establecer el directorio inicial
        if self.directorio_app == '':
            chooser.path = '/home/lapa/Documentos/Slides/Fotos'  # Ruta inicial
        else:
            chooser.path = self.directorio_app

        # Crear un botón adicional dentro del Popup
        btn_aceptar = Button(text="Aceptar", size_hint=(None, None), width=200)
        # pylint: disable=no-member
        btn_aceptar.bind(on_press=lambda *args: self.selecciona_directorio(chooser.selection))

        # Crear un label para mostrar la ruta
        self.path_label = Label(text='Ruta: ', size_hint_y=None, height=30)

        # Función para actualizar la ruta cuando el usuario seleccione un archivo o carpeta
        def update_label(instance, value):
            if value:
                selected_path = value[0]
                if os.path.isfile(selected_path):
                    # Si es un archivo, obtener su carpeta
                    selected_path = os.path.dirname(selected_path)
                self.path_label.text = f"Ruta: {selected_path}"
            else:
                self.path_label.text = f'Ruta: {instance.path}'


        # Vincular la propiedad 'selection' del FileChooserIconView con la función update_label
        chooser.bind(selection=update_label)

        # Usar un ScrollView para permitir el desplazamiento solo cuando sea necesario
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        scroll.add_widget(chooser)

        # Layout para la parte inferior (botón y ruta)
        box2 = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        box2.add_widget(self.path_label)
        box2.add_widget(btn_aceptar)

        # Layout del Popup (contendrá tanto el selector como el botón adicional)
        popup_layout = BoxLayout(orientation='vertical')
        popup_layout.add_widget(scroll) # El selector de directorios está dentro de un ScrollView
        popup_layout.add_widget(box2) # El BoxLayout estará en la parte inferior

        # Crear el popup
        self.popup = Popup(title="Seleccionar Carpeta", content=popup_layout, size_hint=(0.8, 0.8))
        self.popup.open()

    def selecciona_directorio(self, seleccion):
        '''Selecciona directorio'''
        if not seleccion:
            print("No se seleccionó ninguna carpeta.")
            return  # Evita continuar si no hay selección

        selected_path = seleccion[0]
        if os.path.isfile(selected_path):
            selected_path = os.path.dirname(selected_path)

        if selected_path != self.directorio_app:
            self.directorio_app = selected_path
            # Corregido: solo actualizar el label si es un widget válido
            if hasattr(self, 'estado_actual') and hasattr(self.estado_actual, 'text'):
                self.estado_actual.text = f"Directorio: {selected_path}"
            print(f"Carpeta seleccionada: {self.directorio_app}")
        else:
            print("La carpeta seleccionada es la misma.")

        # Cerrar popup de manera segura
        if hasattr(self, 'popup') and self.popup and self.popup.parent:
            self.popup.dismiss()

    def mostrar_popup_error(self, mensaje):
        '''Crear un popup para mostar el mensaje de error'''
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text=mensaje, font_size=20, halign='center', valign='middle')
        boton = Button(text="Cerrar", size_hint=(None, None), size=(100, 50))
        layout.add_widget(label)
        layout.add_widget(boton)

        self.popup = Popup(
            title="Error",
            content=layout,
            size_hint=(None, None),
            size=(400, 200),
            auto_dismiss=False
        )
        boton.bind(on_press=self.popup.dismiss) # pylint: disable=no-member
        self.popup.open()
        self.loading_cursor(False)

    def abrir_entangle(self, *args): # pylint: disable=W0613
        '''Abre Engangle, pausa la previsualización y la reactiva al cerrar'''
        print("Abriendo Entangle...")

        # Detener la previsualización
        if hasattr(self, 'timer') and self.timer:
            Clock.unschedule(self.update)
            self.timer = None
            print("Previsualización detenida")

        # Cerrar conexiones con las cámaras
        if hasattr(self, 'camera_01') and self.camera_01:
            try:
                self.camera_01.exit()
                print("Cámara 1 cerrada")
            except Exception as e: # pylint: disable=W0718
                print(f"Error al cerrar cámara 1: {e}")

        if hasattr(self, 'camera_02') and self.camera_02:
            try:
                self.camera_02.exit()
                print("Cámara 2 cerrada")
            except Exception as e: # pylint: disable=W0718
                print(f"Error al cerrar cámara 2: {e}")

        def ejecutar_entangle():
            try:
                # Ejecutar Entangle
                proceso = subprocess.Popen(["entangle"])
                print("Entangle ejecutándose...")
                proceso.wait() # Esperar a que el usuario cierre Entangle
                print("Entangle cerrado")

                # Volver a ativar la previsualización desde el hilo principal
                Clock.schedule_once(lambda dt: self._reanudar_previsualizacion(), 0)

            except FileNotFoundError:
                Clock.schedule_once(lambda dt: self._show_error_popup(
                    "No se encontró el programa Entangle. Asegúrese de que esté instalado."
                ))
            except Exception as e: # pylint: disable=W0718
                Clock.schedule_once(lambda dt:
                    self._show_error_popup(f"Error al ejecutar Entangle:\n{e}")
                )

        # Ejecutar en un hilo para no bloquear la interfaz
        threading.Thread(target=ejecutar_entangle, daemon=True).start()

    def _reanudar_previsualizacion(self):
        print("Reconectando cámaras...")

        try:
            self.asignar_camaras()
            print("Cámaras asignadas correctamente")

            self.timer = Clock.schedule_interval(self.update, 1.0 / 24.0)
            print("Previsualización reactivada")

        except Exception as e: # pylint: disable=W0718
            self._show_error_popup(f"Error al reconectar la(s) cámara(s):\n{e}")

if __name__ == "__main__":
    CamApp().run()
