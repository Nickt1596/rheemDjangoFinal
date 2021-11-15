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


@login_required(login_url="/login/")
def index(request):
    # trailers = TrailerLocation.objects.all().values('trailer__trailerNumber', 'trailer__trailerPlateNumber',
    #                                                 'trailer__trailerPlateState', 'trailer__trailerLeaseCompany',
    #                                                 'locationCity', 'locationState', 'locationCountry', 'statusCode',
    #                                                 'trailer__id')
    context = {'segment': 'index'}

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


@login_required(login_url="/login/")
def trailers(request):
    trailers = Trailer.objects.all().values()
    context = {'trailers': trailers}
    if request.method == 'POST':
        if 'addtrailer' in request.POST:
            return redirect('addTrailer')
    return render(request, "home/trailer-list.html", context)


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


@login_required(login_url="/login/")
def deleteTrailer(request, pk):
    trailer = Trailer.objects.get(id=pk)
    if request.method == 'POST':
        trailer.delete()
        return redirect('trailers')
    context = {'object': trailer}
    return render(request, "home/delete-trailer.html", context)


@login_required(login_url="/login/")
def trailerLocations(request):
    trailers = trailerLocQuery()
    timestamp = trailers[0]['trailerlocation__updated_at']

    context = {'trailers': trailers, 'timestamp': timestamp}
    if request.method == 'POST':
        if 'refresh' in request.POST:
            updateTrailerLocations()
            return redirect('trailerLocations')
        if 'email' in request.POST:
            sendLocEmail()
            return redirect('trailerLocations')
        if 'csv' in request.POST:
            createCsv()
            return redirect('trailerLocations')
    return render(request, "home/trailer-location-list.html", context)


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


@login_required(login_url="/login/")
def assignShipmentTrailer(request, pk):
    shipment = Shipment.objects.get(id=pk)
    print(shipment)
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


@login_required(login_url="/login/")
def tripReports(request):
    tripreports = tripReportQuery()
    context = {'tripreports': tripreports}
    return render(request, "home/trip-report-list.html", context)
