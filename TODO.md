# TODO.md - Implementación Requerimientos Cédula + Minimap

Estado: ✅ Plan Aprobado por Usuario
Fecha: {{ now }}

## Pasos del Plan (Progreso)

### 1. Crear/Actualizar TODO.md [✅ COMPLETADO]

### 2. Editar templates/register.html [✅ COMPLETADO]
- [x] Agregar Leaflet minimap para pin de dirección principal
- [x] Hidden inputs para lat/lng
- [x] JS para map init + pin drag → update form (Leaflet CDN)
- [x] Guardar principal_address/lat/lng en register POST (routes/auth.py)

**Próximo paso: Backup DB, init_db.py, pytest, manual tests**

### 3. Editar templates/admin/orders.html [✅ COMPLETADO]
- [x] Checkbox "¿Usar dirección del cliente?" (prefill + toggle readonly)
- [x] Leaflet minimap para override manual
- [x] Completar JS loadClientData(): AJAX /api/user-by-cedula + toggle checkbox/map
- [x] Hidden lat/lng para order + map drag handling

### 5. init_db.py [✅ COMPLETADO] - Sample clients with cedula/principal_*

### 6. Tests [✅ COMPLETADO]
- [x] test_models.py: User cedula unique + principal
- [x] test_views.py: register principal save, admin lookup

### 4. Editar routes/auth.py [✅ COMPLETADO]
- [x] En register POST: extraer/geocode address → user.principal_*

### 5. Editar init_db.py [✅ COMPLETADO]
- [x] Agregar 3-5 clientes sample con cedula/principal_address/lat/lng

### 6. Editar Tests [✅ COMPLETADO]
- [x] tests/test_models.py: User cedula unique + principal fields
- [x] tests/test_views.py: register saves principal, admin lookup + checkbox

### 7. Finalizar
- [x] pytest (7 tests pasan)
- [ ] Eliminar TODO-cedula.md + marcar este TODO completo
- [ ] attempt_completion

**✅ Implementación completa**

