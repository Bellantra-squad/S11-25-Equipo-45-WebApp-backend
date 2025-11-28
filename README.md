# S11-25-Equipo-45-WebApp-backend

# CRM

CRM webapp

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: MIT

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    $ mypy crm

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

#### Running tests with pytest

    $ pytest

### Mock Data

# Basic usage - uses default values

python manage.py generate_mock_data

# Customize the amount of data

python manage.py generate_mock_data \
    --leads 50 \
    --contacts-per-lead 3 \
    --activities 100 \
    --tasks 50

# Clear existing data before generating

python manage.py generate_mock_data --clear

# Full customization

python manage.py generate_mock_data \
    --categories 10 \
    --tags 20 \
    --users 10 \
    --leads 50 \
    --contacts-per-lead 3 \
    --activities 100 \
    --tasks 50 \
    --conversations 40 \
    --messages-per-conversation 10 \
    --email-templates 8 \
    --saved-filters 15 \
    --api-credentials 3 \
    --clear

## Desarrollo Local

### Requisitos Previos

- Python 3.11 o superior
- PostgreSQL 12 o superior
- pip (gestor de paquetes de Python)
- (Opcional) Redis para caché (no es obligatorio para desarrollo local)

### Pasos para Configurar el Proyecto

#### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd backend
```

#### 2. Crear y Activar un Entorno Virtual

**Usando venv (recomendado para Python 3.3+):**

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

**O usando virtualenv:**

```bash
pip install virtualenv
virtualenv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

#### 3. Instalar Dependencias

```bash
pip install -r requirements/local.txt
```

#### 4. Configurar Base de Datos PostgreSQL

Asegúrate de tener PostgreSQL corriendo y crea una base de datos:

```bash
# Conectarse a PostgreSQL
psql -U postgres

# Crear la base de datos
CREATE DATABASE crm;

# Salir de psql
\q
```

#### 5. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto (opcional, el proyecto tiene valores por defecto):

```bash
# .env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=tu-secret-key-aqui
DATABASE_URL=postgres://postgres:2323@localhost:5432/crm
DJANGO_READ_DOT_ENV_FILE=True
```

**Nota:** Si no creas el archivo `.env`, el proyecto usará valores por defecto:
- `DATABASE_URL`: `postgres://postgres:2323@localhost:5432/crm`
- `DJANGO_SECRET_KEY`: Se genera automáticamente para desarrollo local
- `DJANGO_DEBUG`: `True` en modo local

#### 6. Aplicar Migraciones

```bash
python manage.py migrate
```

#### 7. Crear un Superusuario (Opcional)

```bash
python manage.py createsuperuser
```

#### 8. Generar Datos de Prueba (Opcional)

```bash
# Generar datos con valores por defecto
python manage.py generate_mock_data

# O personalizar la cantidad de datos
python manage.py generate_mock_data \
    --leads 50 \
    --contacts-per-lead 3 \
    --activities 100 \
    --tasks 50
```

#### 9. Ejecutar el Servidor de Desarrollo

```bash
python manage.py runserver
```

El servidor estará disponible en: `http://localhost:8000`

### Acceder a la Documentación de la API

Una vez que el servidor esté corriendo, puedes acceder a:

- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`
- **Schema JSON**: `http://localhost:8000/api/schema/`

### Comandos Útiles

```bash
# Ejecutar tests
pytest

# Verificar tipos con mypy
mypy crm

# Ejecutar linter
ruff check .

# Formatear código
ruff format .

# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Recolectar archivos estáticos
python manage.py collectstatic
```

### Solución de Problemas

**Error de conexión a la base de datos:**
- Verifica que PostgreSQL esté corriendo: `sudo service postgresql status`
- Verifica las credenciales en `DATABASE_URL`
- Asegúrate de que la base de datos `crm` exista

**Error de dependencias:**
- Asegúrate de estar en el entorno virtual activado
- Reinstala las dependencias: `pip install -r requirements/local.txt --upgrade`

**Error de migraciones:**
- Si hay conflictos, puedes resetear las migraciones (¡cuidado en producción!):
  ```bash
  python manage.py migrate --run-syncdb
  ```

## Deployment

### Producción:
- Railway, más detalles próximamente
