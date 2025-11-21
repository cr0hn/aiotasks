# AioTasks

**Cola de tareas asíncrona moderna para Python 3.11+** - Un gestor de tareas similar a Celery que distribuye corrutinas de asyncio.

[![Versión PyPI](https://badge.fury.io/py/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![Versiones Python](https://img.shields.io/pypi/pyversions/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![Licencia](https://img.shields.io/badge/license-BSD-blue.svg)](https://github.com/cr0hn/aiotasks/blob/main/LICENSE)
[![Estado CI](https://github.com/cr0hn/aiotasks/workflows/CI%2FCD/badge.svg)](https://github.com/cr0hn/aiotasks/actions)

## ¿Qué es AioTasks?

AioTasks es una cola de tareas moderna y de alto rendimiento construida sobre asyncio de Python. Si estás familiarizado con Celery, te sentirás como en casa - AioTasks proporciona una API similar pero diseñada específicamente para flujos de trabajo async/await.

## Características Principales

- ✨ **API tipo Celery**: Interfaz familiar para desarrolladores Python
- 🚀 **AsyncIO Nativo**: Construido desde cero para async/await
- 🔄 **Múltiples Backends**: Memory, Redis, RabbitMQ (AMQP), ZeroMQ
- 🔁 **Lógica de Reintentos Inteligente**: Retroceso exponencial con tenacity
- 📊 **Confirmación de Tareas**: Soporte ACK/NACK para procesamiento confiable
- ⏱️ **Soporte TTL**: Expiración automática de tareas
- 🎯 **Type Safe**: Type hints completos con sintaxis moderna de Python
- 🐍 **Python 3.11+**: Usa las últimas características de Python (match/case, StrEnum, PEP 604)

## Ejemplo Rápido

```python
import asyncio
from aiotasks import AioTasks

# Crear app (¡igual que Celery!)
app = AioTasks("myapp", broker="redis://localhost:6379/0")

# Definir tareas
@app.task()
async def enviar_email(para: str, asunto: str, cuerpo: str):
    await asyncio.sleep(1)  # Simular envío de email
    print(f"Email enviado a {para}")

# Usar tareas
async def main():
    app.run()
    await enviar_email.delay("usuario@ejemplo.com", "Hola", "Mundo")
    await app.wait(timeout=10, exit_on_finish=True)
    app.stop()

asyncio.run(main())
```

## ¿Por qué AioTasks?

### vs Celery

- **Async Nativo**: No necesita procesos worker, todo son corrutinas
- **Python Moderno**: Usa características de Python 3.11+ como pattern matching
- **Más Simple**: No necesita procesos broker separados en desarrollo (backend memory)
- **Type Safe**: Type hints completos en todo el código

### vs TaskIQ/ARQ

- **API compatible con Celery**: Migración más fácil para proyectos existentes
- **Más Backends**: Soporte para Memory, Redis, AMQP, ZMQ
- **Retry Integrado**: Lógica sofisticada de reintentos con retroceso exponencial

## Instalación

```bash
# Instalación básica
pip install aiotasks

# Con soporte Redis
pip install aiotasks[redis]

# Con soporte RabbitMQ
pip install aiotasks[amqp]

# Con todas las características
pip install aiotasks[all]
```

## Próximos Pasos

- [Guía de Instalación](getting-started/installation.md)
- [Tutorial de Inicio Rápido](getting-started/quickstart.md)
- [Guía de Usuario](guide/celery-style.md)
- [Ejemplos](examples/basic.md)
- [Referencia API](api/aiotasks.md)

## Licencia

AioTasks se distribuye bajo la licencia BSD-3-Clause. Consulta [LICENSE](https://github.com/cr0hn/aiotasks/blob/main/LICENSE) para más información.
