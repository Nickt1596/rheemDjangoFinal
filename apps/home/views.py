# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse
from .models import *
from .forms import *
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
import time


# Index Page, currently has nothing of importance on it.
@login_required(login_url="/login/")
def index(request):
    # trailers = TrailerLocation.objects.all().values('trailer__trailerNumber', 'trailer__trailerPlateNumber',
    #                                                 'trailer__trailerPlateState', 'trailer__trailerLeaseCompany',
    #                                                 'locationCity', 'locationState', 'locationCountry', 'statusCode',
    #                                                 'trailer__id')
    trailers = trailerLocQuery()
    rheemcharges = rheemChargeQuery()
    carriercharges = carrierChargeQuery()
    shipments = shipmentAllQuery()
    context = {'segment': 'index', 'trailers': trailers, 'carriercharges': carriercharges, 'rheemcharges': rheemcharges,
               'shipments': shipments}

    html_template = loader.get_template('home/index.html')
    return HttpResponse(html_template.render(context, request))


# @login_required(login_url="/login/")
# def pages(request):
#     context = {}
#     # All resource paths end in .html.
#     # Pick out the html file name from the url. And load that template.
#     try:
#
#         load_template = request.path.split('/')[-1]
#
#         if load_template == 'admin':
#             return HttpResponseRedirect(reverse('admin:index'))
#         context['segment'] = load_template
#
#         html_template = loader.get_template('home/' + load_template)
#         return HttpResponse(html_template.render(context, request))
#
#     except template.TemplateDoesNotExist:
#
#         html_template = loader.get_template('home/page-404.html')
#         return HttpResponse(html_template.render(context, request))
#
#     except:
#         html_template = loader.get_template('home/page-500.html')
#         return HttpResponse(html_template.render(context, request))


# Handles the trailer table which displays only the Trailer Information
@login_required(login_url="/login/")
def trailers(request):
    trailers = Trailer.objects.all().values()
    context = {'trailers': trailers}
    if request.method == 'POST':
        if 'addtrailer' in request.POST:
            return redirect('addTrailer')
    return render(request, "home/trailer-list.html", context)


# TODO New Email Form for sending custom e-mails
@login_required(login_url="/login/")
def emailForm(request):
    form = EmailForm()
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            emailType = form.cleaned_data['emailType']
            if emailType == 'LOC':
                trailers = form.cleaned_data['locSelect']
                recipient = form.cleaned_data['recipient']
                subject = 'Trailer Locations'
                message = ''
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [recipient]
                send_mail(subject, message, email_from, recipient_list, html_message=trailerLocEmail(trailers))
            elif emailType == 'ST':
                shipments = form.cleaned_data['stSelect']
                recipient = form.cleaned_data['recipient']
                subject = 'In Transit Shipment Trailer Locations'
                message = ''
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [recipient]
                send_mail(subject, message, email_from, recipient_list, html_message=shipmentTransitEmail(shipments))
            elif emailType == 'DPU':
                trailers = form.cleaned_data['dpuSelect']
                recipient = form.cleaned_data['recipient']
                subject = 'Trailers Available For Pickup'
                message = trailerDrayEmail(trailers)
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [recipient]
                send_mail(subject, message, email_from, recipient_list)
        return redirect('trailerLocations')
    context = {'form': form}
    return render(request, "home/email-form.html", context)


# Form used for adding a new trailer
@login_required(login_url="/login/")
def addTrailer(request):
    form = TrailerForm()
    if request.method == 'POST':
        form = TrailerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('trailers')
    context = {'form': form}
    return render(request, "home/add-trailer.html", context)


# Form for updating an existing trailer
@login_required(login_url="/login/")
def updateTrailer(request, pk):
    trailer = Trailer.objects.get(id=pk)
    form = TrailerForm(instance=trailer)

    if request.method == 'POST':
        form = TrailerForm(request.POST, instance=trailer)
        if form.is_valid():
            form.save()
            return redirect('trailers')
    context = {'form': form}
    return render(request, "home/add-trailer.html", context)


# User for Deleting a trailer
@login_required(login_url="/login/")
def deleteTrailer(request, pk):
    trailer = Trailer.objects.get(id=pk)
    if request.method == 'POST':
        trailer.delete()
        return redirect('trailers')
    context = {'object': trailer}
    return render(request, "home/delete-trailer.html", context)


# Displays Trailer Locations
# TODO See if we can speed this up to avoid timeout errors
# TODO Fix .CSV
@login_required(login_url="/login/")
def trailerLocations(request):
    trailers = trailerLocQuery()
    timestamp = trailers[0]['trailer__trailerlocation__updated_at']

    context = {'trailers': trailers, 'timestamp': timestamp}
    if request.method == 'POST':
        if 'refresh' in request.POST:
            updateTrailerLocations()
            return redirect('trailerLocations')
        if 'email' in request.POST:
            return redirect('emailForm')
        if 'csv' in request.POST:
            # createCsv()
            return redirect('trailerLocations')
    return render(request, "home/trailer-location-list.html", context)


# Displays our shipments
@login_required(login_url="/login/")
def shipments(request):
    context = {'shipments': shipmentAllQuery()}
    if request.method == 'POST':
        if 'all' in request.POST:
            return render(request, "home/shipment-list.html", context)
        if 'delivered' in request.POST:
            context = {'shipments': shipmentDeliveredQuery()}
            return render(request, "home/shipment-list.html", context)
        if 'intransit' in request.POST:
            context = {'shipments': shipmentTransitQuery()}
            return render(request, "home/shipment-list.html", context)
        if 'addshipment' in request.POST:
            return redirect('addShipment')
    return render(request, "home/shipment-list.html", context)


# Form used for adding a shipment
@login_required(login_url="/login/")
def addShipment(request):
    form = ShipmentForm()
    if request.method == 'POST':
        form = ShipmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('shipments')
    context = {'form': form}
    return render(request, "home/add-shipment.html", context)


# Form used for changing a shipment
@login_required(login_url="/login/")
def updateShipment(request, pk):
    shipment = Shipment.objects.get(id=pk)
    form = ShipmentForm(instance=shipment)

    if request.method == 'POST':
        form = ShipmentForm(request.POST, instance=shipment)
        if form.is_valid():
            form.save()
            return redirect('shipments')

    context = {'form': form}
    return render(request, "home/add-shipment.html", context)


# Form used to update the carrier Rate
@login_required(login_url="/login/")
def updateCarrierRate(request, pk):
    carrierRate = Shipment.objects.get(id=pk)
    form = CarrierRateForm(instance=carrierRate)

    if request.method == 'POST':
        form = CarrierRateForm(request.POST, instance=carrierRate)
        if form.is_valid():
            form.save()
            return redirect('shipments')
        else:
            print(form.errors)

    context = {'form': form}
    return render(request, "home/add-carrierrate.html", context)


# Form used to assign a trailer to a shipment
@login_required(login_url="/login/")
def assignShipmentTrailer(request, pk):
    shipment = Shipment.objects.get(id=pk)
    form = AssignTrailerForm(instance=shipment)

    if request.method == 'POST':
        form = AssignTrailerForm(request.POST, instance=shipment)
        if form.is_valid():
            print("Form is valid")
            form.save()
            return redirect('shipments')
        else:
            print("Form is not valid")
            print(form.errors)
    context = {'form': form}
    return render(request, "home/assign-trailer.html", context)


# Form used to assign a carrier
@login_required(login_url="/login/")
def assignCarrier(request, pk):
    shipment = Shipment.objects.get(id=pk)
    form = AssignCarrierForm(instance=shipment)

    if request.method == 'POST':
        form = AssignCarrierForm(request.POST, instance=shipment)
        if form.is_valid():
            form.save()
            return redirect('shipments')

    context = {'form': form}
    return render(request, "home/assign-carrier.html", context)


# Form used to set a delivery appointment
@login_required(login_url="/login/")
def setDeliveryAppt(request, pk):
    shipmentDelivery = Shipment.objects.get(id=pk)
    form = ShipmentDeliveryForm(instance=shipmentDelivery)

    if request.method == 'POST':
        form = ShipmentDeliveryForm(request.POST, instance=shipmentDelivery)
        if form.is_valid():
            form.save()
            return redirect('shipments')

    context = {'form': form}
    return render(request, "home/set-delivery.html", context)


# Form used to update the action dates
@login_required(login_url="/login/")
def setTrailerTrip(request, pk):
    trailerTrip = TrailerTrip.objects.get(trailer=pk)
    form = TrailerTripForm(instance=trailerTrip)

    if request.method == 'POST':
        form = TrailerTripForm(request.POST, instance=trailerTrip)
        if form.is_valid():
            form.save()
            return redirect('shipments')

    context = {'form': form}
    return render(request, "home/set-trailertrip.html", context)


# Form used to assign driver
@login_required(login_url="/login/")
def assignDriver(request, pk):
    shipment = Shipment.objects.get(id=pk)
    form = AssignDriverForm(instance=shipment)

    if request.method == 'POST':
        form = AssignDriverForm(request.POST, instance=shipment)
        if form.is_valid():
            form.save()
            return redirect('shipments')

    context = {'form': form}
    return render(request, "home/assign-driver.html", context)


# Displays our Trip Reports
@login_required(login_url="/login/")
def tripReports(request):
    tripreports = tripReportQuery()
    context = {'tripreports': tripreports}
    return render(request, "home/trip-report-list.html", context)


# # Displays our Carrier Charges
# @login_required(login_url="/login/")
# def carrierCharges(request):
#     carriercharges = carrierChargeQuery()
#     context = {'carriercharges': carriercharges}
#     return render(request, "home/carrier-charge-list.html", context)


# # Displays our Rheem Charges
# @login_required(login_url="/login/")
# def rheemCharges(request):
#     rheemcharges = rheemChargeQuery()
#     context = {'rheemcharges': rheemcharges}
#     return render(request, "home/rheem-charge-list.html", context)
