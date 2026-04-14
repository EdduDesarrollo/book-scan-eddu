# Book Scan

Book Scan es una aplicación diseñada para digitalizar documentos en papel, como libros, afiches y otros materiales impresos. El programa automatiza el proceso de captura de imágenes mediante cámaras conectadas, permitiendo gestionar el flujo de trabajo, configurar parámetros y guardar los archivos digitalizados de forma organizada. Incluye una interfaz gráfica intuitiva desarrollada con Kivy y Tkinter.

## Estructura del proyecto

- `eddu_book_scan_1.py`: Script principal de la aplicación.
- `config.json`: Archivo de configuración con parámetros personalizables.
- `Utils/`: Carpeta con recursos gráficos y archivos de utilidad.
- `Fotos/`: Carpeta sugerida para almacenar las imágenes digitalizadas.

## Requisitos

- Python 3

Instalación de Python 3 en Linux:
```bash
sudo apt update
sudo apt install python3
```

Todas las dependencias (incluyendo Entangle, Kivy, Tkinter, Pillow, OpenCV, gphoto2) se instalan automáticamente al ejecutar el programa si no están presentes en el sistema.

## Uso

Ejecuta el script principal:
```bash
python3 eddu_book_scan_1.py
```

Sigue las instrucciones en pantalla para configurar el nombre de archivo, seleccionar el directorio de destino y operar las cámaras.

### Crear un icono ejecutable en el escritorio (Linux/Ubuntu)

1. Abre un editor de texto y crea un archivo llamado `BookScan.desktop` en tu escritorio:

```bash
nano ~/Escritorio/BookScan.desktop
```

2. Copia y pega el siguiente contenido, ajustando la ruta si es necesario:

```ini
[Desktop Entry]
Type=Application
Name=Book Scan
Exec=python3 /ruta/a/Book_Scan/eddu_book_scan_1.py
Icon=/ruta/a/Book_Scan/Utils/logo.png
Terminal=false
Categories=Utility;
```

> Reemplaza `/ruta/a/Book_Scan/` por la ruta donde hayas descargado o clonado el proyecto.

3. Guarda el archivo y dale permisos de ejecución:

```bash
chmod +x ~/Escritorio/BookScan.desktop
```

4. Ahora puedes ejecutar el programa haciendo doble clic en el icono del escritorio.

## Autor

Eddu Agu

---

Para dudas o mejoras, revisa el código fuente y la documentación incluida.
