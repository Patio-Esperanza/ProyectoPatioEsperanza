# Módulo de Reportes para Clientes — Especificación de Diseño

## Resumen Ejecutiva
Permitir que los usuarios con rol `CLIENTE` puedan autogestionarse reportes operativos de sus contenedores en patio, con visualización en pantalla (KPIs, tabla paginada, filtros) y opciones de exportación a **Excel** (vía backend `openpyxl`) y **PDF** (vía impresión optimizada del navegador).

## Alcance y Restricciones de Seguridad
1. **Seguridad / Aislamiento de Datos:** 
   - Un usuario con rol `CLIENTE` solo puede consultar y exportar datos correspondientes a su propio `cliente_id` (vinculado a su cuenta de usuario).
   - Los endpoints de backend (`/api/v1/reportes/{tipo}/preview` y `/api/v1/reportes/{tipo}/exportar`) validarán el rol `CLIENTE` y aplicarán automáticamente el filtro `Contenedor.cliente_id == user.cliente_id` (o equivalente en cada tipo de reporte).
2. **Tipos de Reportes Disponibles para Clientes:**
   - Contenedores en Patio (`containers-in-yard`)
   - Movimientos de Entrada (`entry-movements`)
   - Movimientos de Salida (`departure-movements`)
   - Posiciones Actuales (`positions`)
   - Servicios Especiales (`special-services`)

## Arquitectura y Componentes

### 1. Backend (`backend/app/api/routes/reportes.py` y `reportes_datos.py`)
- Actualizar dependencias de seguridad en los endpoints de reportes para permitir `RolUsuario.CLIENTE` además de _ROLES_STAFF.
- En `obtener_datos_reporte` (y funciones auxiliares), si `user.rol == RolUsuario.CLIENTE`, forzar el filtro por `cliente_id = user.cliente_id`.
- Mantener exportación a Excel existente (`/exportar`).

### 2. Frontend (`frontend/app/reportes/page.tsx` y componentes asociados)
- Asegurar que la ruta `/reportes` en `rutas.ts` y el Sidebar permitan acceso a rol `CLIENTE`.
- Ajustar `FiltrosReporteBar.tsx` para ocultar o adaptar filtros no aplicables a clientes (por ejemplo, selector global de cliente, ya que el cliente solo ve los suyos).
- Agregar botón de **Exportar a PDF** usando `window.print()` con estilos `@media print` dedicados para ocultar barras de navegación y mostrar una cabecera limpia y profesional del reporte.

## Pruebas y Verificación
- Pruebas unitarias de backend para verificar que un usuario `CLIENTE` recibe únicamente sus contenedores y recibe error 403 si intenta acceder a datos de otro cliente.
- Pruebas E2E / manuales de visualización en pantalla, paginación, exportación Excel y exportación PDF.
