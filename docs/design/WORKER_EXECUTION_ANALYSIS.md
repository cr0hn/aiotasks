# Sistema de Ejecución de Workers - Análisis y Propuesta

## 📊 Estado Actual

### Implementación Actual

**Archivo:** `aiotasks/tasks/bases.py`

```python
# Línea 292: Semáforo para limitar concurrencia
self.task_concurrency_sem = asyncio.BoundedSemaphore(concurrency)

# Línea 485: Ejecución de tareas
task = asyncio.create_task(self._function_runner(local_task, task_id, *args, **kwargs))
```

### Características:

1. **Pool Type:** Solo corrutinas (`asyncio.create_task()`)
2. **Concurrency Control:** `asyncio.BoundedSemaphore` (default=5)
3. **Execution Model:** Todas las tareas se ejecutan como corrutinas en el event loop
4. **Task Validation:** Solo acepta `async def` (línea 347)

### Limitaciones:

❌ **Solo I/O-bound tasks**: No es óptimo para tareas CPU-intensive
❌ **GIL problem**: Tareas CPU-bound bloquean todo el worker
❌ **Sin opción de configuración**: No se puede elegir el tipo de pool
❌ **No acepta funciones síncronas**: Rechaza `def` (solo `async def`)

---

## 🔍 Comparación con Celery

### Celery Pool Options

```bash
celery -A app worker --pool=<pool_type>
```

| Pool Type | Descripción | Uso |
|-----------|-------------|-----|
| **prefork** (default) | Multiprocessing pool | CPU-bound, aislamiento total |
| **solo** | Sin pool, single process | Testing, debugging |
| **threads** | ThreadPoolExecutor | I/O-bound bloqueante |
| **gevent** | Greenlets (gevent) | I/O-bound async (green threads) |
| **eventlet** | Greenlets (eventlet) | I/O-bound async (green threads) |

### AioTasks Actual

```bash
aiotasks -A app worker -c 10  # Solo concurrency, no pool type
```

| Pool Type | Disponible | Descripción |
|-----------|------------|-------------|
| **asyncio** | ✅ Sí (único) | Coroutines pool (event loop) |
| **threads** | ❌ No | ThreadPoolExecutor |
| **processes** | ❌ No | ProcessPoolExecutor |

---

## 💡 Propuesta de Diseño

### Arquitectura Propuesta

```python
# Pool de Ejecución con múltiples estrategias
class ExecutionPool(Enum):
    ASYNC = "async"        # asyncio.create_task() - Default
    THREAD = "thread"      # ThreadPoolExecutor
    PROCESS = "process"    # ProcessPoolExecutor
```

### API Propuesta

#### 1. CLI

```bash
# Default: asyncio pool (coroutines)
aiotasks -A app worker -c 10

# Thread pool (para tareas I/O bloqueantes)
aiotasks -A app worker --pool=thread -c 20

# Process pool (para tareas CPU-intensive)
aiotasks -A app worker --pool=process -c 4
```

#### 2. Python API

```python
app = AioTasks(
    "myapp",
    broker="redis://localhost",
    pool="async",      # async | thread | process
    concurrency=10,    # Número de workers/tasks
)
```

#### 3. Decorador con tipo de pool

```python
# Opción A: Global pool type
@app.task()  # Usa el pool global (async)
async def io_task():
    await asyncio.sleep(1)

# Opción B: Per-task pool type (advanced)
@app.task(pool="thread")
def blocking_io_task():  # Acepta def, no solo async def
    import time
    time.sleep(1)  # Bloquea, pero OK en thread

@app.task(pool="process")
def cpu_task(n):  # CPU-intensive
    return sum(i*i for i in range(n))
```

---

## 🏗️ Implementación Recomendada

### Fase 1: Refactoring Mínimo (Recomendado para v2.2)

**Objetivo:** Mantener compatibilidad, agregar flexibilidad

1. **Mantener el sistema actual** (asyncio pool)
2. **Agregar parámetro `pool`** al constructor:
   ```python
   def __init__(
       self,
       prefix: str = "aiotasks",
       concurrency: int = 5,
       pool: str = "async",  # NUEVO: async | thread | process
       max_retries: int = 3,
       task_ttl: int = 3600,
   ):
   ```

3. **Crear ejecutor dinámico**:
   ```python
   def _create_executor(self):
       if self.pool == "async":
           return None  # usa asyncio.create_task()
       elif self.pool == "thread":
           return concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency)
       elif self.pool == "process":
           return concurrent.futures.ProcessPoolExecutor(max_workers=self.concurrency)
   ```

4. **Adaptar `_function_runner`**:
   ```python
   async def _function_runner(self, fn, task_id, *args, **kwargs):
       if self.pool == "async":
           # Actual: ejecutar coroutine directamente
           await fn(*args, **kwargs)
       else:
           # Nuevo: ejecutar en executor (thread/process)
           loop = asyncio.get_running_loop()
           await loop.run_in_executor(self.executor, fn, *args, **kwargs)
   ```

5. **Permitir `def` y `async def`**:
   ```python
   def task(self, name=None, pool=None):
       def real_decorator(f):
           # Validación flexible
           task_pool = pool or self.pool

           if task_pool == "async" and not asyncio.iscoroutinefunction(f):
               raise ValueError(f"{f.__name__} must be async def for async pool")

           if task_pool in ("thread", "process") and asyncio.iscoroutinefunction(f):
               log.warning(f"{f.__name__} is async def but will run in {task_pool} pool")
   ```

### Fase 2: Optimizaciones Avanzadas (v2.3+)

1. **Pool per task** (overrides global)
2. **Auto-detection** del tipo de tarea (sync/async)
3. **Híbrido** (múltiples pools simultáneos)
4. **Estadísticas** por pool type

---

## 🎯 Recomendaciones

### Para v2.2.0 (Actual)

**NO implementar ahora** porque:
- ✅ Es un cambio arquitectural grande
- ✅ Requiere testing extensivo
- ✅ Puede romper compatibilidad
- ✅ La mayoría de usuarios async/await no necesitan threads/processes

**Documentar en CHANGELOG:**
```markdown
## Known Limitations

- Worker execution uses asyncio coroutines only
- Not optimal for CPU-bound tasks (use separate process workers)
- Sync functions (def) not supported (use async def)
```

### Para v2.3.0 (Futuro)

**Implementar pool support:**

```python
# v2.3.0
app = AioTasks(
    "myapp",
    broker="redis://localhost",
    pool="async",      # NEW: async | thread | process
    concurrency=10,
)
```

**CLI:**
```bash
aiotasks -A app worker --pool=thread -c 20
```

---

## 📋 Decisión Recomendada

### Para AHORA (v2.2.0):

1. **✅ Mantener sistema actual** (solo asyncio pool)
2. **✅ Documentar limitaciones** claramente
3. **✅ Agregar issue en GitHub** para pool support en v2.3
4. **✅ No hacer cambios breaking** en v2.2.0

**Rationale:**
- Sistema actual funciona bien para async/await
- La mayoría de usuarios Python moderno usan async/await
- Para CPU-bound, pueden usar workers separados
- Cambio grande requiere más diseño y testing

### Para FUTURO (v2.3.0):

1. **Implementar pool support** completo
2. **Mantener backward compatibility**
3. **Default a "async"** (actual)
4. **Testing exhaustivo** de threads/processes

---

## 🔍 Verificación Necesaria

Antes de implementar pool support, verificar:

1. **Serialización**: ¿Funciona msgpack con ProcessPoolExecutor?
2. **Retry logic**: ¿Funciona con executor?
3. **ACK/NACK**: ¿Funciona cross-process?
4. **Callbacks**: ¿Funcionan en threads/processes?
5. **Memory**: ¿Impacto de procesos múltiples?

---

## 📚 Referencias

- [Celery Concurrency Documentation](https://docs.celeryq.dev/en/stable/userguide/workers.html#concurrency)
- [Python asyncio Executors](https://docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools)
- [concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)

