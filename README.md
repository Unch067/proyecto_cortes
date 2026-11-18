# 📐 OptiCorte 1D — Manual de Operación (Grupo 3)

Aplicación interactiva en **Streamlit** para optimizar el corte unidimensional (*1D Cutting Stock Problem*) de perfiles y tuberías en obra. Prioriza el aprovechamiento del inventario de retales existentes antes de adquirir tubos comerciales nuevos, garantizando un balance de masa exacto al 100%.

---

## 1. Reglas de Negocio y Algoritmo

1. **Unidades Internas (`int`)**: Todas las longitudes se procesan internamente en **milímetros enteros (`int`)**.
2. **Algoritmo Best-Fit Decreasing (BFD)**:
   - Ordena las piezas requeridas de mayor a menor longitud.
   - Evalúa todos los retales disponibles y tubos abiertos, seleccionando aquel que deje el **menor remanente** tras el corte.
   - En caso de empate en remanente, desempata por: 1) menor longitud inicial de la barra y 2) orden alfabético del identificador (`Origen_ID`).
3. **Regla de Ajuste Físico y Pérdida por Corte (*Kerf*)**:
   - **Encaje exacto (`pieza == saldo`)**: La pieza ocupa exactamente la totalidad de la barra o retal disponible sin requerir corte final (**0 mm de pérdida**).
   - **Corte estándar (`pieza + perdida <= saldo`)**: Se descuenta la longitud de la pieza más el espesor del disco (`kerf`).
4. **Clasificación del Sobrante**:
   - **Retal Reutilizable (`sobrante >= retal_minimo`)**: Se reincorpora al almacén para futuros proyectos.
   - **Descarte Inútil (`0 < sobrante < retal_minimo`)**: Merma no aprovechable.
   - **Exacto (`sobrante == 0`)**: Aprovechamiento total de la barra.
5. **Caso de Comprobación Oficial**:
   - **Entradas**: Retal `R1 = 3000 mm`, Tubo comercial `6000 mm`, Piezas `[2900, 2000, 1900, 1800] mm`, Pérdida `4 mm`, Retal mínimo `200 mm`.
   - **Resultado validado**: **1 unidad nueva**, **9000 mm** material origen, **8600 mm** incorporados, **16 mm** pérdida por corte, **96 mm** descarte y **288 mm** retal reutilizable (`8600 + 16 + 96 + 288 = 9000 mm`).

---

## 2. Formas de Ejecución

### Opción A: Ejecutable Portable (`OptiCorte1D.exe`)
Si utilizas la versión compilada con PyInstaller (no requiere tener Python instalado):
```powershell
.\dist\OptiCorte1D\OptiCorte1D.exe
```

### Opción B: Lanzador Automático (`ejecutar_app.bat`)
Haz doble clic sobre `ejecutar_app.bat` o ejecútalo desde la terminal:
```powershell
.\ejecutar_app.bat
```
*(Verifica el entorno virtual `venv`, instala dependencias si faltan e inicia la aplicación automáticamente).*

### Opción C: Desde el Entorno Virtual (`venv`)
```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

---

## 3. Guía de Uso Paso a Paso

La interfaz conserva tus datos y resultados en memoria mientras navegas entre sus 4 pestañas:

1. **⚙️ Configuración**:
   - **Tubo Nuevo (mm)**: Longitud comercial estándar de compra (por defecto `6000 mm`).
   - **Pérdida por corte (mm)**: Espesor del disco o sierra (*kerf*, por defecto `4 mm`).
   - **Retal Mínimo (mm)**: Umbral a partir del cual un sobrante se considera reutilizable (por defecto `200 mm`).
2. **📦 Inventario**:
   - Registra los retales disponibles en obra (`ID_Retal`, `Longitud_mm`, `Cantidad`), ya sea editando directamente la tabla interactiva o subiendo un archivo CSV.
3. **📋 Pedidos**:
   - Ingresa las piezas requeridas (`ID_Pieza`, `Longitud_mm`, `Cantidad`) en la tabla o mediante carga de un archivo CSV.
   - Haz clic en **"🚀 Calcular Optimización"**.
4. **📊 Resultados**:
   - **Balance de Materiales**: Indicadores de Material Origen, Tubos Nuevos a Comprar, Material Incorporado, Pérdida por Corte y Descarte Inútil.
   - **Comparativa de Eficiencia**: Compara el algoritmo **Optimizado (IA)** contra el **Orden Original** de ingreso.
   - **Exportar Resultados**: Descarga el plan de corte (`plan.csv`), el balance (`balance.csv`), el informe técnico para taller (`informe_tecnico_corte.txt`) y, si existieran, las piezas pendientes (`pendientes.csv`).
   - **📐 Gemelo Digital 3D**: Modelo volumétrico interactivo de las barras, piezas útiles (azul), cortes de disco (rojo), retales reutilizables (ámbar) y descartes (gris).
   - **⚙️ Simulador de Taller**: Selecciona cualquier barra y desplaza el control deslizante para simular el avance físico de la sierra milímetro a milímetro.
   - **📊 Análisis Visual Comparativo**: Gráfico dona de porcentaje de aprovechamiento y gráfico de barras comparativo.

---

## 4. Formato de Archivos CSV y Carpeta `datos_ejemplo/`

El importador CSV soporta archivos separados por **coma (`,`)** o **punto y coma (`;`)**, y valores numéricos con **punto (`.`)** o **coma (`,`)** decimal (redondeando las longitudes automáticamente a milímetros enteros).

### Columnas Requeridas
- **Para Inventario**: `ID_Retal`, `Longitud_mm`, `Cantidad`
- **Para Pedidos**: `ID_Pieza`, `Longitud_mm`, `Cantidad`

### Archivos Incluidos en `datos_ejemplo/`
| Archivo | Pestaña | Descripción |
| :--- | :--- | :--- |
| `datos_ejemplo/inventario_valido.csv` | 📦 Inventario | Retal oficial `R1` de `3000 mm` separado por comas (`,`). |
| `datos_ejemplo/pedidos_validos.csv` | 📋 Pedidos | Las 4 piezas del caso oficial (`2900, 2000, 1900, 1800 mm`) separadas por comas (`,`). |
| `datos_ejemplo/datos_punto_y_coma.csv` | 📋 Pedidos | Ejemplo exportado estilo Excel en español con delimitador `;` y decimales con coma/punto (`2900,0`, `1900,4`, `1799,6`). |
| `datos_ejemplo/pedidos_con_errores.csv` | 📋 Pedidos | Archivo con errores intencionales (`Cantidad = 1,5` y pieza de `6500 mm`) para probar los mensajes de validación. |

---

## 5. Catálogo de Mensajes de Error y Solución

| Mensaje de Error | Causa | Cómo Solucionarlo |
| :--- | :--- | :--- |
| `Error en CSV de ...: Faltan las columnas [...]` | El archivo CSV subido no tiene los encabezados exactos requeridos. | Verifica que la primera línea del CSV tenga `ID_Retal,Longitud_mm,Cantidad` (en Inventario) o `ID_Pieza,Longitud_mm,Cantidad` (en Pedidos). |
| `Error en ...: Existen celdas vacías o sin completar.` | Se agregó una fila nueva en la tabla o en el CSV dejando campos en blanco. | Completa todas las celdas de la fila o elimina la fila vacía seleccionándola en el borde izquierdo y pulsando `Supr`. |
| `Error en ...: El identificador (...) no puede estar vacío.` | Una fila tiene el `ID_Retal` o `ID_Pieza` compuesto solo por espacios. | Escribe un código identificador único (ej. `R1`, `P100`). |
| `Error en ...: Las cantidades no admiten decimales.` | Se ingresó una cantidad fraccionaria (ej. `1.5` o `0,5` piezas). | Ingresa únicamente números enteros mayores o iguales a `0` (`0, 1, 2...`). *(Las filas con cantidad `0` se ignoran en el cálculo).* |
| `Error en ...: Las cantidades no pueden ser negativas.` | Se ingresó una cantidad menor que `0` (ej. `-1`). | Corrige la cantidad a un entero positivo o `0`. |
| `Error en ...: Las longitudes deben ser números enteros positivos.` | Una longitud es `<= 0` o tiene decimales en la tabla manual. | Ingresa la longitud en milímetros enteros mayores a `0` (ej. `2500`). |
| `IDs de retales duplicados.` / `IDs de piezas duplicados.` | Dos filas activas (`Cantidad > 0`) comparten el mismo código ID. | Asigna un ID único a cada fila o agrupa la cantidad en una sola fila. |
| `Existen retales mayores al tubo nuevo.` | Un retal de inventario tiene `Longitud_mm > Tubo Nuevo (mm)`. | Verifica la longitud del retal o aumenta la longitud del tubo comercial en **⚙️ Configuración**. |
| `Piezas imposibles de cortar considerando kerf: [...]` | Una pieza mide más que el tubo comercial, o mide entre `l_comercial - kerf + 1` y `l_comercial - 1` (donde no hay margen para el espesor del disco). | Ajusta la longitud de la pieza, reduce el `kerf` o incrementa la longitud del `Tubo Nuevo (mm)` en **⚙️ Configuración**. |

---

## 6. Pruebas Unitarias y Compilación con PyInstaller

### Ejecutar la Batería de Pruebas Unitarias
```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Compilar el Ejecutable Portable `OptiCorte1D.exe`
```powershell
.\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --name OptiCorte1D --copy-metadata streamlit --copy-metadata plotly --collect-data streamlit --collect-data plotly --add-data "app.py;." --add-data "core;core" --add-data "components;components" --add-data "datos_ejemplo;datos_ejemplo" run_app.py
```
El ejecutable quedará disponible en `dist\OptiCorte1D\OptiCorte1D.exe`.
