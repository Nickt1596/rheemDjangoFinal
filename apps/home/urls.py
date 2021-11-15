# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),

    # # Matches any html file
    # re_path(r'^.*\.*', views.pages, name='pages'),

    path('trailers/', views.trailers, name="trailers"),
    path('add-trailer/', views.addTrailer, name="addTrailer"),
    path('update-trailer/<str:pk>', views.updateTrailer, name="updateTrailer"),
    path('delete-trailer/<str:pk>', views.deleteTrailer, name="deleteTrailer"),

    path('shipments/', views.shipments, name="shipments"),
    path('add-shipment/', views.addShipment, name="addShipment"),
    path('update-shipment/<str:pk>', views.updateShipment, name="updateShipment"),
    path('add-carrierrate/<str:pk>', views.updateCarrierRate, name="updateCarrierRate"),
    path('assign-trailer/<str:pk>', views.assignShipmentTrailer, name="assignShipmentTrailer"),
    path('assign-carrier/<str:pk>', views.assignCarrier, name="assignCarrier"),
    path('assign-driver/<str:pk>', views.assignDriver, name="assignDriver"),
    path('set-delivery/<str:pk>', views.setDeliveryAppt, name="setDeliveryAppt"),
    path('set-trailertrip/<str:pk>', views.setTrailerTrip, name="setTrailerTrip"),

    path('trailer-locations/', views.trailerLocations, name="trailerLocations"),
    path('tripreports/', views.tripReports, name="tripReports"),

    path('add-trailer-modal/', views.addTrailer, name="addTrailer"),

]
