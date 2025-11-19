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

## Deployment

# Local:
- Create and activate a virtual environment (using `venv` or `virtualenv`):

    # Using venv (Python 3.3+ recommended)
    python3 -m venv venv
    source venv/bin/activate

    # Or using virtualenv
    pip install virtualenv
    virtualenv venv
    source venv/bin/activate

- Install dependencies:
    pip install -r requirements/local.txt

- Set up your environment variables (see `.env.example` for reference)
- Apply database migrations:
    python manage.py migrate
- Run the development server:
    python manage.py runserver
    
# Production:
- Railway, more details soon
