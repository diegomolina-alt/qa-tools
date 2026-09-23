# QA Tools

QA Tools permite generar casos de prueba para Xray y documentos de evidencias para pruebas API y Mobile.

## Instalación en macOS

### 1. Obtener el proyecto

Clona el repositorio y entra a la carpeta:

```bash
git clone https://github.com/diegomolina-alt/qa-tools.git
cd qa-tools
```

### 2. Crear la aplicación

Haz doble clic en `BUILD_QA_TOOLS.command`.

También puedes ejecutarlo desde Terminal:

```bash
bash BUILD_QA_TOOLS.command
```

El proceso prepara lo necesario y genera la aplicación automáticamente. Requisito para generar la aplicación: Python 3.11 o superior. El script valida Python antes de continuar.

Cuando termine, Finder abrirá la carpeta `dist/`.

### 3. Instalar QA Tools

Copia `QA Tools.app` desde `dist/` a la carpeta **Aplicaciones**.

Importante: copia `QA Tools.app`, no la carpeta `QA Tools` ni el ejecutable interno.

Después abre **Aplicaciones → QA Tools**.

Python solamente se necesita para construir `QA Tools.app`. Una vez instalada, abre la aplicación normalmente desde Aplicaciones; no necesitas ejecutar el código fuente nuevamente.

## Uso

### Generar casos para Xray

Completa los siguientes datos:

- Número Jira
- Analista QA
- Directorio del repositorio Xray
- Dominio
- Criterios de aceptación

Pulsa **GENERAR CASOS** y selecciona dónde guardar el CSV.

### Generar evidencias

QA Tools genera documentos Word de evidencias para:

- API
- Mobile

Selecciona el tipo de evidencia, carga los casos y pulsa **GENERAR DOCUMENTO**. Después selecciona la carpeta donde deseas guardar el DOCX.

El botón **NUEVO** limpia la información actual para comenzar otra generación. Los documentos que ya guardaste no se eliminan.

## Actualizar QA Tools

Cuando exista una nueva versión:

1. Actualiza o descarga nuevamente el repositorio.
2. Ejecuta `BUILD_QA_TOOLS.command`.
3. Reemplaza la aplicación anterior de Aplicaciones por la nueva `QA Tools.app`.

## Ayuda

Si QA Tools muestra un error, reporta el mensaje mostrado por la aplicación al equipo responsable.

La distribución para Windows se preparará por separado.
