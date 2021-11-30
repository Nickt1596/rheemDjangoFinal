# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin

# Register your models here.
from .models import *


admin.site.register(Trailer)
admin.site.register(TrailerTrip)
admin.site.register(TrailerLocation)
admin.site.register(TripReport)
admin.site.register(Shipment)
admin.site.register(CarrierCharge)
admin.site.register(RheemCharge)