# Panel escolar — plan de implementación

Objetivo: completar el frontend del ADMIN_ESCOLAR en el monolito Django, según los documentos entregados. El usuario delegó el diseño y autorizó implementación directa.

Arquitectura: plantillas en src/templates/escolar, CSS y módulos JavaScript en src/static/escolar; vistas HTML protegidas en apps/panel_escolar; fetch del mismo origen y sesión Django + CSRF. No tokens en almacenamiento del navegador. No nuevo frontend Next.js.

Diseño: framed-sheet, seed 1527466279. Marco gris verdoso, hoja blanca, tipografía IBM Plex Sans, acento verde petróleo y marca de puerta protegida. El inicio responde qué solicitudes requieren revisión y qué estudiantes carecen de representante. Cifras derivadas de la API, sin estadísticas de retiros inventadas.

## Tareas
- [ ] Pruebas de acceso HTML, CSRF, contraseña temporal y aislamiento de usuarios entre colegios; observar fallos antes de implementar.
- [ ] Rutas HTML, estructura compartida, login/TOTP/recuperación/cambio de clave y cliente API.
- [ ] Inicio, estudiantes, padres, guardias, asignaciones, cuidadores, cursos, puertas, institución, bitácora y notificaciones.
- [ ] Formularios, filtros, paginación, confirmaciones, estados vacíos/error/carga y WebSocket con reconexión limitada.
- [ ] Comprobar con Django, pruebas de contrato y navegador en escritorio/móvil. Documentar limitaciones y modo local explícito con datos ficticios.
- [ ] Revisar diff y preparar entrega. No usar BelkiErick para commits remotos; confirmar perfil ChristianPuchaicela antes de publicar.

## Riesgos a verificar
Sesión expirada durante una edición; errores de validación del servidor; solicitudes duplicadas; texto largo o contenido HTML en datos; colegios ajenos; modificación de bitácora; contraseña temporal mostrada solo en memoria.

Decisión: corregir el filtro de usuarios que usa un manager sin tenancy. Es necesario para consumir de forma segura el endpoint escolar; no alterar modelos ni migraciones de negocio.
Decisión: SQLite se usa exclusivamente en configuración de pruebas/vista previa, nunca sustituye SQL Server en producción.
