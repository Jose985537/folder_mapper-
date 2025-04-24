# Folder Mapper 📂✨ (PyQt6 Version)

Aplicación de escritorio desarrollada con **PyQt6** para visualizar, gestionar y mapear la estructura de directorios de forma interactiva. Permite seleccionar carpetas (mediante diálogo o arrastrar y soltar), explorar su contenido de forma asíncrona, seleccionar/deseleccionar elementos (con propagación) para incluir en un mapa, filtrar por nombre, previsualizar la estructura y generar un archivo de texto con la estructura seleccionada.

## Características

* **Selección de Carpeta:** Elige la carpeta raíz mediante un diálogo de exploración o arrastrando y soltando la carpeta sobre la ventana. 📁
* **Visualización de Árbol Interactivo:** Explora la estructura de archivos y carpetas en una vista de árbol. 🌳
* **Carga Asíncrona de Directorios:** El contenido de los subdirectorios se carga en segundo plano al expandirlos, manteniendo la interfaz responsiva. ⏳⚙️
* **Selección y Deselección:** Marca qué archivos y carpetas incluir. La selección/deselección se propaga a los elementos hijos y padres según corresponda. Los elementos seleccionados tienen un resaltado visual. ✅☑️
* **Filtrado por Nombre:** Filtra los elementos en el árbol en tiempo real. 🔎
* **Vista Previa:** Visualiza una vista previa de la estructura que se generará, respetando la selección y el filtro. 👀📄
* **Generación de Mapa:** Crea un archivo `.txt` con la estructura seleccionada, incluyendo detalles como número de ítems o tamaño de archivos. 🗺️💾
* **Ayuda:** Accede a información sobre el desarrollador y funcionalidades. ❓💡
* **Abrir Ubicación:** Abre la carpeta contenedora de un archivo o directorio directamente desde el menú contextual.

## Instalación 🛠️

Asegúrate de tener Python instalado.

1.  Instala la biblioteca **PyQt6**: ✅
    ```bash
    pip install PyQt6
    ```
2.  Descarga el archivo `Folder_mapper.py` y la carpeta `recursos` con los iconos (`Icon.ico`) y colócalos en el mismo directorio. (Nota: `Logo.png` fue mencionado en el README anterior pero no directamente en el código de carga de recursos actual). 📂⬇️

## Uso ▶️

1.  Ejecuta el script Python:
    ```bash
    python Folder_mapper.py
    ```
2.  Selecciona la carpeta usando "Examinar" o arrastrando y soltando. 🖱️📂
3.  Explora la estructura. Haz doble clic o expande directorios para cargar su contenido. 🌳👀
4.  Usa la columna "Incluir" (☑/☐) o el menú contextual para seleccionar/deseleccionar elementos. ✅
5.  Usa la barra "FILTRAR" para buscar. 🔎
6.  Revisa la "Vista Previa de la Estructura". 📄👍
7.  Haz clic en "Generar Mapa" para crear el archivo `.txt`. 🗺️💾

## Tecnologías Utilizadas 💻

* **PyQt6**
* Python

[![Tecnologías](https://skillicons.dev/icons?i=py,qt)](https://skillicons.dev)

## Contacto 📧

Si tienes alguna pregunta o sugerencia:

* **José Gabriel Calderón**
* **GitHub:** [https://github.com/Jose985537](https://github.com/Jose985537)
* **Email:** gc5444592@gmail.com

---
©️ 2025 Todos los derechos reservados.