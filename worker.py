import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aimharder.settings')
django.setup()
settings.DEBUG = False

from bookings import job
job.run()
