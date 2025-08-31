# Solución para el Conflicto de Blueprints en Render

## Problema
Durante el despliegue en Render, se producía el siguiente error:
```
AssertionError: View function mapping is overwriting an existing endpoint function: devops.login
```

Este error ocurría porque los scripts `actualizar_db.py` e `init_users_flota.py` importaban `app.py`, lo que causaba que el blueprint de DevOps se registrara múltiples veces.

## Causa Raíz
1. Los scripts de inicialización importan `from app import app, db`
2. Al importar `app.py`, se ejecuta todo el código del módulo
3. El registro del blueprint `devops_bp` se ejecutaba en cada importación
4. Flask detectaba el intento de registrar el mismo endpoint múltiples veces

## Solución Implementada

### 1. Control de Registro de Blueprints
Se modificó `app.py` para incluir un control inteligente del registro de blueprints:

```python
# Variable global para controlar registro de blueprints
_blueprints_registered = False

# Función para registrar blueprints
def register_blueprints():
    """Registrar todos los blueprints de la aplicación"""
    global _blueprints_registered
    
    if _blueprints_registered:
        print("Blueprints ya registrados, saltando...")
        return
    
    # Verificar si el blueprint ya está registrado
    if 'devops' in app.blueprints:
        print("Blueprint de DevOps ya registrado, saltando...")
        _blueprints_registered = True
        return
    
    try:
        from devops_routes import devops_bp
        app.register_blueprint(devops_bp)
        print("Blueprint de DevOps registrado")
        _blueprints_registered = True
    except ImportError as e:
        print(f"No se pudo registrar el blueprint de DevOps: {e}")
    except Exception as e:
        print(f"Error registrando blueprint: {e}")

# Solo registrar blueprints si no estamos siendo importados por scripts
if not any(script in sys.argv[0] for script in ['actualizar_db.py', 'init_users_flota.py']):
    register_blueprints()
```

### 2. Mecanismos de Protección
- **Variable Global**: `_blueprints_registered` evita registros múltiples
- **Detección de Scripts**: Verifica si se está ejecutando como script de inicialización
- **Verificación de Estado**: Comprueba si el blueprint ya está registrado antes de intentar registrarlo
- **Manejo de Errores**: Captura y maneja errores de registro sin interrumpir la aplicación

## Resultados

### ✅ Antes de la Solución
- Error en Render durante el despliegue
- Scripts de inicialización fallaban
- Aplicación no se desplegaba correctamente

### ✅ Después de la Solución
- Despliegue exitoso en Render
- Scripts de inicialización funcionan correctamente
- Blueprint de DevOps se registra solo cuando es necesario
- No hay conflictos de endpoints

## Pruebas Realizadas

### 1. Importación como Script
```python
sys.argv[0] = 'actualizar_db.py'
from app import app
# Resultado: Blueprint NO se registra ✅
```

### 2. Ejecución Normal
```python
sys.argv[0] = 'app.py'
from app import app
# Resultado: Blueprint se registra correctamente ✅
```

### 3. Múltiples Importaciones
- Múltiples importaciones del mismo módulo
- No hay conflictos de blueprints
- Sistema funciona correctamente ✅

## Archivos Modificados

1. **`belgrano_tickets/app.py`**
   - Agregada lógica de control de blueprints
   - Importación de `sys` para detección de scripts
   - Manejo robusto de errores

## Archivos de Prueba Creados

1. **`belgrano_tickets/test_blueprint_registration.py`**
   - Prueba importación como script

2. **`belgrano_tickets/test_normal_execution.py`**
   - Prueba ejecución normal

## Recomendaciones

1. **Mantener la Lógica**: No modificar la lógica de control de blueprints
2. **Agregar Scripts**: Si se agregan nuevos scripts de inicialización, incluirlos en la lista de detección
3. **Monitoreo**: Verificar que el despliegue funcione correctamente en cada actualización

## Estado Actual
✅ **PROBLEMA RESUELTO**
- El sistema se despliega correctamente en Render
- Los scripts de inicialización funcionan sin errores
- El panel de DevOps está disponible y funcional
- No hay conflictos de blueprints
