from django.contrib import admin

# Register your models here.

from .models import Booking
from .models import User

admin.site.register(Booking)
admin.site.register(User)
