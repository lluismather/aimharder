import os
import django
from django.conf import settings
from bookings import job

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()
settings.DEBUG = False

job.run()