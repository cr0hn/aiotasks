# Publishing to PyPI

Este proyecto tiene dos workflows de publicación. Elige el que prefieras:

## 🔐 Opción 1: Trusted Publishing (OIDC) - **RECOMENDADO**

**Workflow:** `.github/workflows/publish.yml`

### Ventajas
- ✅ Más seguro (sin tokens que puedan filtrarse)
- ✅ No necesitas gestionar secretos en GitHub
- ✅ Recomendado oficialmente por PyPI
- ✅ Rotación automática de credenciales

### Configuración

#### 1. Configura PyPI

Ve a: https://pypi.org/manage/account/publishing/

Añade un nuevo publisher con:
- **Project name**: `aiotasks`
- **Owner**: `cr0hn` (tu usuario de GitHub)
- **Repository name**: `aiotasks`
- **Workflow filename**: `publish.yml`
- **Environment name**: `pypi`

#### 2. (Opcional) Configura TestPyPI

Ve a: https://test.pypi.org/manage/account/publishing/

Añade un nuevo publisher con:
- **Project name**: `aiotasks`
- **Owner**: `cr0hn`
- **Repository name**: `aiotasks`
- **Workflow filename**: `publish.yml`
- **Environment name**: `testpypi`

#### 3. Configura GitHub Environment

1. Ve a: `Settings` → `Environments` en tu repositorio
2. Crea un environment llamado `pypi`
3. (Opcional) Añade protection rules si quieres aprobación manual
4. (Opcional) Crea otro environment `testpypi` para testing

#### 4. Publica

```bash
# Ve a GitHub → Actions → Publish to PyPI
# Click "Run workflow"
# Introduce:
#   - version: 2.2.0
#   - tag: v2.2.0
#   - test_pypi: false (o true para testing)
```

---

## 🔑 Opción 2: API Token

**Workflow:** `.github/workflows/publish-token.yml`

### Ventajas
- ✅ Más simple de configurar
- ✅ Funciona en todos los entornos

### Configuración

#### 1. Genera API Tokens en PyPI

**Para producción:**
1. Ve a: https://pypi.org/manage/account/token/
2. Click "Add API token"
3. **Token name**: `GitHub Actions - aiotasks`
4. **Scope**: Limita al proyecto `aiotasks` (recomendado)
5. **Copia el token** (empieza con `pypi-...`)

**Para testing (opcional):**
1. Ve a: https://test.pypi.org/manage/account/token/
2. Repite el proceso
3. Copia el token

#### 2. Añade Secretos en GitHub

1. Ve a: `Settings` → `Secrets and variables` → `Actions` en tu repo
2. Click `New repository secret`

**Para producción:**
- Name: `PYPI_API_TOKEN`
- Secret: Pega el token de PyPI

**Para testing (opcional):**
- Name: `TEST_PYPI_API_TOKEN`
- Secret: Pega el token de TestPyPI

#### 3. Publica

```bash
# Ve a GitHub → Actions → Publish to PyPI (API Token)
# Click "Run workflow"
# Introduce:
#   - version: 2.2.0
#   - tag: v2.2.0
#   - test_pypi: false (o true para testing)
```

---

## 📋 Comparación

| Característica | OIDC (Recomendado) | API Token |
|---------------|-------------------|-----------|
| Seguridad | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Configuración | Media | Simple |
| Secretos en GitHub | 0 | 1-2 |
| Recomendado por PyPI | ✅ Sí | ❌ No |
| Rotación automática | ✅ Sí | ❌ No |

---

## 🚀 Proceso de Publicación

Independientemente del método que uses:

1. **Pre-requisitos:**
   - CHANGELOG.md actualizado
   - Todos los tests pasando
   - Documentación actualizada

2. **Ejecuta el workflow:**
   - GitHub → Actions → Elige el workflow
   - Run workflow
   - Introduce versión y tag

3. **El workflow automáticamente:**
   - ✅ Actualiza `pyproject.toml` con la nueva versión
   - ✅ Crea commit con el cambio de versión
   - ✅ Crea y pushea el tag de Git
   - ✅ Construye el paquete (wheel + sdist)
   - ✅ Valida el paquete con twine
   - ✅ Publica a PyPI/TestPyPI
   - ✅ Crea GitHub Release

---

## 🐛 Troubleshooting

### Error: "No environment named 'pypi' found"

**Solución:** Crea el environment en GitHub:
1. Settings → Environments → New environment
2. Name: `pypi`

### Error: "Invalid or non-existent authentication information"

**Opción OIDC:**
- Verifica que configuraste Trusted Publishing en PyPI
- Verifica que el environment name coincide (`pypi`)
- Verifica que el workflow filename es correcto (`publish.yml`)

**Opción Token:**
- Verifica que el secreto `PYPI_API_TOKEN` existe
- Verifica que el token es válido
- Regenera el token si es necesario

### Error: "Filename already exists"

**Causa:** Intentas publicar una versión que ya existe

**Solución:**
- PyPI no permite sobrescribir versiones
- Incrementa la versión (ej: 2.2.0 → 2.2.1)
- O usa TestPyPI para testing

---

## 📚 Referencias

- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions PyPI Publish](https://github.com/marketplace/actions/pypi-publish)
- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
