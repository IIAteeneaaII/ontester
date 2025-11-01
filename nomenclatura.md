COMMITS

Estructura:

<tipo>(<área>): <descripción corta>

Commits 

Tipo	Cuándo usarlo	Ejemplo
feat	Cuando agregas una nueva funcionalidad	feat(frontend): agregar componente de login
fix	Para corregir errores o bugs	fix(backend): corregir validación de token JWT
refactor	Cuando reestructuras código sin cambiar el comportamiento	refactor(frontend): simplificar función de renderizado
style	Cambios solo visuales o de formato	style(frontend): ajustar colores del navbar
chore	Tareas menores o mantenimiento (sin afectar lógica)	chore: actualizar dependencias de npm
docs	Cambios en documentación	docs: agregar guía de instalación al README
test	Agregar o modificar pruebas	test(backend): agregar pruebas unitarias para controlador de usuarios
build	Cambios que afectan el sistema de build o dependencias	build: configurar Dockerfile para producción
perf	Mejoras de rendimiento	perf(backend): optimizar consulta SQL en endpoint de reportes


Ejemplos 

Frontend:

feat(frontend): agregar vista de registro de usuario
fix(frontend): corregir error en validación de formulario
style(frontend): mejorar espaciado en el footer

Backend:

feat(backend): crear endpoint para registrar usuarios
fix(backend): corregir respuesta 500 en ruta /login
refactor(backend): mover lógica de autenticación a middleware

General o multiplataforma: ( SIMOD ejemplo ) No creo que aplique tanto a ont 

chore: actualizar dependencias de proyecto
docs: agregar instrucciones para desplegar con Docker


