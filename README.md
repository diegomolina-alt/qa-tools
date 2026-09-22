# QA Test Generator

Aplicación local de escritorio para transformar criterios de aceptación de una historia de usuario en casos de prueba base y un archivo CSV para Xray. No usa base de datos ni conserva la información al cerrar la ventana.

## Requisitos

- Python 3.11 o superior
- Tcl/Tk 8.6 o superior (incluido con una instalación moderna de Python)

## Instalación

```bash
python -m pip install -r requirements.txt
```

## Ejecutar QA Test Generator en macOS

### Instalar Python compatible

La aplicación necesita una instalación independiente y actual de Python. El Python incluido en Apple Command Line Tools no es compatible, porque utiliza Tcl/Tk 8.5.

1. Descargue el instalador de macOS desde [python.org](https://www.python.org/downloads/macos/) e instálelo con las opciones predeterminadas.
2. Cierre y abra una terminal nueva.
3. Compruebe que se instaló una versión válida:

```bash
python3 --version
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

Debe obtener Python 3.11 o superior y Tk 8.6 o superior. Como alternativa, puede instalarlo con Homebrew:

```bash
brew install python
```

La forma recomendada de iniciar la aplicación es:

```bash
./run.command
```

El script busca un Python válido, prioriza instalaciones de python.org y Homebrew, valida Python 3.11+ y Tcl/Tk 8.6+, crea `.venv` solo si no existe e instala `python-docx` únicamente cuando falta.

No use el Python de Apple Command Line Tools (`/Library/Developer/CommandLineTools/usr/bin/python3`), porque normalmente incluye Tcl/Tk 8.5 y no renderiza correctamente la interfaz.

Puede comprobar el entorno activo con:

```bash
python --version
python -c "import tkinter; print(tkinter.TkVersion)"
```

Debe obtener Python 3.11 o superior y Tk 8.6 o superior. Si no dispone de una instalación compatible, instale Python y abra una nueva terminal antes de ejecutar `./run.command`.

También puede iniciar directamente la aplicación después de activar un entorno compatible:

```bash
python app.py
```

## Uso

1. Abra la pestaña **Generar Casos**.
2. Ingrese el número de Jira, analista QA y el directorio repositorio Xray.
3. Pegue los criterios de aceptación. Los encabezados `CA01`, `CA02` o `CA-01` se detectan como criterios independientes.
4. Seleccione **GENERAR CASOS** y elija la carpeta de destino.
5. La aplicación crea `carga casos XRAY <JIRA>.csv` en esa carpeta.

El CSV se crea en UTF-8 estándar, separado por comas y con escape seguro de comillas, comas, saltos de línea, tildes y eñes.

### Generar Evidencia API

En la pestaña **Generar Evidencia**, seleccione **API**, ingrese como mínimo Número Jira y QA Agile, complete Fecha Ejecución, Servicio y Test Plan cuando corresponda. En **Títulos de los Test** pegue cada bloque Xray con este formato:

```text
Xray Test
TAP-79281

T-ADN1-2694 Título del test
```

Seleccione **CARGAR CASOS** para crear las tarjetas plegables. Cada tarjeta conserva de forma independiente Método, Endpoint, Status Response, Value Status Response, Request, Response y Verificación. Finalmente seleccione **GENERAR EVIDENCIA**. El resultado se guarda en la carpeta elegida con el nombre `Evidencias_APIs_<JIRA>.docx`.

La generación utiliza [templates/Evidencias_APIs_template.docx](templates/Evidencias_APIs_template.docx) como plantilla y nunca la sobrescribe. La opción Mobile permanece pendiente de su plantilla oficial.

### Iniciar un documento nuevo

Cada pestaña incluye un botón **NUEVO** en la parte superior. Este limpia solamente el formulario de su propia pestaña, sin cerrar la aplicación ni modificar la otra. Si existen datos, se solicita confirmación antes de descartarlos.

## Estructura

```text
qa-tools/
├── app.py              # Interfaz gráfica y flujo de generación
├── qa_engine.py        # Procesamiento de criterios y casos base
├── csv_generator.py    # Exportación CSV
├── evidence_generator.py # Generación de evidencia API desde plantilla
├── report_generator.py # Exportación DOCX
├── templates/
│   └── Evidencias_APIs_template.docx
├── run.command          # Inicio compatible con macOS
├── requirements.txt
└── README.md
```
