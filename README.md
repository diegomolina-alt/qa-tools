# QA Tools

Herramienta local para generación de casos y evidencias QA. Convierte criterios de aceptación en un CSV compatible con Xray y genera evidencias API en DOCX desde la plantilla incluida.

## Inicio rápido

No necesitas crear un entorno virtual, activar Python ni instalar paquetes manualmente. La primera ejecución lo prepara todo; las siguientes reutilizan el entorno y son rápidas.

Solo necesitas tener instalado Python 3.11 o superior con soporte gráfico Tcl/Tk 8.6 o superior. Tkinter forma parte de esa instalación de Python; no se instala mediante `pip`.

### macOS

Después de descargar o clonar el proyecto:

```bash
cd qa-tools
bash run.command
```

Eso es todo. El script crea automáticamente el entorno virtual, instala las dependencias necesarias y abre QA Tools.

### Windows

Después de descargar o clonar el proyecto, abre CMD en la carpeta y ejecuta:

```bat
cd qa-tools
run.bat
```

Desde PowerShell:

```powershell
cd qa-tools
.\run.bat
```

El script crea automáticamente el entorno virtual, instala las dependencias necesarias y abre QA Tools.

## Uso

### Generar Casos

Completa Número Jira, Analista QA, Directorio repositorio Xray, Dominio y los Criterios de aceptación. **Dominio es obligatorio** para generar el CSV. Los encabezados `CA01`, `CA02` o `CA-01` se detectan como criterios independientes.

Selecciona **GENERAR CASOS** y una carpeta de destino. Los diálogos abren inicialmente en Downloads/Descargas del usuario, aunque puedes elegir otra ubicación.

La columna **Resumen** del CSV usa únicamente:

```text
Dominio - nombre del caso
```

Por ejemplo:

```text
Urpipro/Loan/Bandeja de entrada - Consulta bandeja de solicitudes del AdN
```

Número Jira continúa utilizándose donde corresponde, pero no forma parte de Resumen.

### Generar Evidencia API

Selecciona **API** como tipo de evidencia y completa los campos actuales: Número Jira, QA Agile, Test Plan, Servicio y **TÍTULOS DE LOS TEST**. Mobile continúa pendiente. Pega directamente el contenido copiado de Jira/Xray Test Execution y selecciona **CARGAR CASOS**.

El parser reconoce el formato real de Jira/Xray, extrae TAP y título, y muestra los casos detectados antes de generar la estructura del documento. No necesitas limpiar manualmente valores como `Cucumber`, `TO DO`, contadores de defectos, metadatos, enlaces Markdown o columnas auxiliares. También admite el formato simple:

```text
Xray Test
TAP-79281

T-ADN1-2694 Título del test
```

Al generar el DOCX, QA Tools completa automáticamente Método `POST`, Endpoint con el valor de Servicio, Status Response `200`, Value Status Response `OK`, Estado general `PASSED` y la Fecha Ejecución actual. Request, Response y Verificación se completan manualmente después en el documento Word generado; allí también puedes cambiar `POST` si un caso requiere otro método.

La plantilla necesaria está incluida en `templates/Evidencias_APIs_template.docx`; no hace falta copiarla ni configurarla.

### Nuevo documento y carpeta de salida

Las dos pestañas tienen el botón **NUEVO**. Limpia únicamente los datos de la pestaña actual, no cierra QA Tools y permite comenzar otro documento de inmediato. Si hay información cargada, solicita confirmación antes de descartarla.

Al guardar CSV o DOCX, los diálogos abren inicialmente en Descargas/Downloads del usuario actual. Puedes seleccionar otra carpeta si lo necesitas.

## Si aparece un problema

**No se encontró Python compatible**

Instala Python 3.11 o superior desde la página oficial: [macOS](https://www.python.org/downloads/macos/) o [Windows](https://www.python.org/downloads/windows/). En Windows habilita Python Launcher y Add Python to PATH cuando el instalador lo ofrezca. Después ejecuta nuevamente el script de inicio.

**Python no incluye Tcl/Tk**

Reinstala Python desde python.org con soporte Tkinter/Tcl-Tk. Tcl/Tk no se instala mediante `pip`.

**No se pudieron instalar las dependencias**

Verifica tu conexión a Internet, red corporativa o proxy y vuelve a ejecutar el script.

**macOS bloquea la ejecución**

Usa `bash run.command`; no depende de permisos de ejecución del archivo.

## Información técnica y soporte

Los scripts `run.command` y `run.bat` localizan Python 3.11+ con Tkinter y Tcl/Tk 8.6+, crean o reparan `.venv`, instalan `requirements.txt` en la primera ejecución o cuando ese archivo cambia, validan los imports críticos y ejecutan la aplicación directamente con el Python del entorno. No necesitan activar el entorno.

`requirements.txt` es la fuente única de dependencias externas y actualmente contiene `python-docx==1.2.0`. Tkinter, `pathlib`, `csv` y otros módulos estándar no se instalan con pip.

Para soporte o desarrollo, el flujo manual equivalente es:

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## Estructura

```text
qa-tools/
├── app.py
├── bootstrap.py
├── csv_generator.py
├── evidence_generator.py
├── qa_engine.py
├── report_generator.py
├── requirements.txt
├── run.command
├── run.bat
└── templates/
    └── Evidencias_APIs_template.docx
```
