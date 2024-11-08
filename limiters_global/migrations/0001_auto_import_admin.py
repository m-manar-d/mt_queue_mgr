""" Import default super-admin from .env to DB """

from os import path, environ
from pathlib import Path
from dotenv import load_dotenv
from django.db import migrations

BASE_DIR = Path(__file__).resolve().parent.parent.parent
dotenv_file = path.join(BASE_DIR, ".env")
if path.isfile(dotenv_file):
    load_dotenv(dotenv_file)

class Migration(migrations.Migration):
    """ Import default super-admin from .env """
    initial = True
    dependencies = [
    ]
    def generate_superuser(apps, schema_editor):
        """ Import default super-admin from .env """
        from django.contrib.auth.models import User
        django_su_name = environ['DJANGO_SU_NAME']
        django_su_email = environ['DJANGO_SU_EMAIL']
        django_su_password = environ['DJANGO_SU_PASSWORD']
        superuser = User.objects.create_superuser(
            username=django_su_name,
            email=django_su_email,
            password=django_su_password)
        superuser.save()
    operations = [
    ]
