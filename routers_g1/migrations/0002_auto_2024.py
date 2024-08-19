from os import path, environ
from pathlib import Path
from dotenv import load_dotenv
from django.db import migrations

BASE_DIR = Path(__file__).resolve().parent.parent.parent
dotenv_file = path.join(BASE_DIR, ".env")
if path.isfile(dotenv_file):
    load_dotenv(dotenv_file)

class Migration(migrations.Migration):

    dependencies = [
        ('routers_g1', '0001_initial'),
    ]
    def generate_superuser(apps, schema_editor):
        from django.contrib.auth.models import User

        DJANGO_SU_NAME = environ['DJANGO_SU_NAME']
        DJANGO_SU_EMAIL = environ['DJANGO_SU_EMAIL']
        DJANGO_SU_PASSWORD = environ['DJANGO_SU_PASSWORD']

        superuser = User.objects.create_superuser(
            username=DJANGO_SU_NAME,
            email=DJANGO_SU_EMAIL,
            password=DJANGO_SU_PASSWORD)
        superuser.save()


    operations = [
        migrations.RunPython(generate_superuser),
    ]
