# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib.auth.models import User
from django.db import models
import uuid
from decimal import *
from datetime import *
from apps.home import trailerdata
from datetime import datetime
from prettytable import PrettyTable
import smtplib
import os
from email.message import EmailMessage
import csv
from geopy import distance


# Create your models here.

# This model will not change much. Only possible changes are when a new trailer is added or removed
class Trailer(models.Model):
    trailerNumber = models.CharField(max_length=200)
    trailerPlateState = models.CharField(max_length=30)
    trailerPlateNumber = models.CharField(max_length=30)
    trailerLeaseCompany = models.CharField(max_length=200)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.trailerNumber

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if TrailerLocation.objects.filter(trailer__trailerNumber=self.trailerNumber).exists() is False:
            createFirstTrailerLoc(self.id)
        if TrailerTrip.objects.filter(trailer__trailerNumber=self.trailerNumber).exists() is False:
            createFirstTrailerTrip(self.id)


class TrailerLocation(models.Model):
    trailer = models.OneToOneField(Trailer, on_delete=models.CASCADE)
    locationCity = models.CharField(max_length=70, null=True, blank=True)
    locationState = models.CharField(max_length=30, null=True, blank=True)
    locationCountry = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.CharField(max_length=200, null=True, blank=True)
    longitude = models.CharField(max_length=200, null=True, blank=True)
    statusCode = models.CharField(max_length=200, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.trailer.trailerNumber


class Shipment(models.Model):
    CARRIER_CHOICES = [
        ('GW', 'Greatwide'),
        ('BL', 'Brian Williams'),
    ]
    dateTendered = models.DateField(default=date.today)
    loadNumber = models.CharField(max_length=50)
    masterBolNumber = models.CharField(max_length=50)
    carrier = models.CharField(max_length=100, blank=True, choices=CARRIER_CHOICES, default='GW')
    destinationCity = models.CharField(max_length=70)
    destinationState = models.CharField(max_length=50)
    rateLineHaul = models.DecimalField(max_digits=15, decimal_places=2)
    rateFSC = models.DecimalField(max_digits=15, decimal_places=2)
    rateExtras = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    rateTotal = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, default=0.00)
    loadDelivered = models.BooleanField(default=False)
    customCarrierRate = models.BooleanField(default=False)
    deliveryDate = models.DateField(null=True, blank=True)
    deliveryTime = models.TimeField(null=True, blank=True)
    driverName = models.CharField(max_length=70, null=True, blank=True)
    driverCell = models.CharField(max_length=70, null=True, blank=True)
    rateTotalCarrier = models.DecimalField(max_digits=15, decimal_places=2, null=True, default=0)
    shipmentMargin = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    shipmentMarginPercentage = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    trailer = models.ForeignKey(Trailer, on_delete=models.PROTECT, blank=True, null=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.loadNumber + " " + self.destinationCity + " " + self.destinationState

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.customCarrierRate is False and self.rateTotalCarrier == 0.00:
            calcRate(self.id)
            calcShipmentMargin(self.id)
        if self.shipmentMargin is None:
            calcShipmentMargin(self.id)
        if self.trailer is not None and self.loadDelivered is False:
            updateTrailerTrip(self.id, self.trailer.id)


# For every shipment there will be a TrailerTrip entry that relates to it. Also a one to one relationship.
class TrailerTrip(models.Model):
    trailer = models.OneToOneField(Trailer, on_delete=models.CASCADE)
    shipment = models.OneToOneField(Shipment, on_delete=models.PROTECT, null=True, blank=True)
    dateYardEmpty = models.DateField(null=True, blank=True)
    dateDrayPickedUp = models.DateField(null=True, blank=True)
    dateDrayReturnedLoaded = models.DateField(null=True, blank=True)
    dateCarrierPickedUpLoaded = models.DateField(null=True, blank=True)
    dateCarrierDelivered = models.DateField(null=True, blank=True)
    dateCarrierReturnedEmpty = models.DateField(null=True, blank=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.trailer.trailerNumber

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.dateCarrierReturnedEmpty is not None:
            createTripReport(self.id, self.shipment.id, self.trailer.id)
            resetTrailerTrip(self.id)
        if self.dateCarrierDelivered is not None:
            shipment = Shipment.objects.get(id=self.shipment.id)
            shipment.loadDelivered = True
            shipment.save()


class TripReport(models.Model):
    trailer = models.ForeignKey(Trailer, on_delete=models.PROTECT)
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT)
    daysYardEmpToDrayPu = models.IntegerField(null=True, blank=True)
    daysDrayPuToYardLoad = models.IntegerField(null=True, blank=True)
    daysYardLoadToCarrPu = models.IntegerField(null=True, blank=True)
    daysCarrPuToDeliv = models.IntegerField(null=True, blank=True)
    daysDelivToRetEmp = models.IntegerField(null=True, blank=True)
    trailerDaysOwed = models.IntegerField(null=True, blank=True)
    totalDays = models.IntegerField(null=True, blank=True)
    startDate = models.DateField(null=True, blank=True)
    endDate = models.DateField(null=True, blank=True)
    totalTrailerCost = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    grossMargin = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    netMargin = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    netMarginAfterTrailer = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)

    def __str__(self):
        return self.trailer.trailerNumber + " " + self.shipment.loadNumber + " " + \
               str(self.startDate) + "-" + str(self.endDate)


def createRateTable():
    rateTable = {
        'CA': [2.95, 3.25, 3.05],
        'CO': [4.1, 4.25, 4.1],
        'CT': [3.7, 4.2, 3.85],
        'FL': [3.45, 3.85, 3.55],
        'IA': [3.2, 3.4, 3.2],
        'IL': [3.2, 3.4, 3.2],
        'IN': [3.2, 3.4, 3.2],
        'LA': [3.45, 5.75, 4.45],
        'MA': [3.7, 4.25, 3.95],
        'MD': [3.7, 3.95, 4.2],
        'MI': [2.7, 3.35, 3.0],
        'MN': [3.45, 3.55, 3.45],
        'MT': [4.2, 4.25, 4.2],
        'NC': [3.45, 3.55, 3.45],
        'ND': [3.7, 4.2, 3.85],
        'NE': [3.7, 4.2, 3.85],
        'NH': [3.7, 4.85, 4.15],
        'NJ': [3.7, 3.95, 4.2],
        'NV': [3.45, 3.85, 3.55],
        'NY': [3.7, 4.15, 3.85],
        'OH': [3.45, 3.65, 3.45],
        'OR': [3.2, 3.9, 3.4],
        'PA': [3.7, 3.85, 3.7],
        'SC': [3.45, 3.55, 3.45],
        'TN': [3.45, 3.55, 3.45],
        'UT': [3.45, 4.0, 3.6],
        'VA': [3.7, 3.9, 3.8],
        'WA': [3.2, 4.0, 3.4],
        'WV': [3.7, 3.85, 3.7]
    }
    return rateTable


def checkRate(state):
    rateTable = createRateTable()
    if state in rateTable:
        return getRateList(state, rateTable)
    else:
        return False


def getRateList(state, rateTable):
    return rateTable[state]


def getTrailerCost(trailerNum):
    if trailerNum == '528687' or '545823' or '536313':
        return Decimal(36.96)
    elif trailerNum == 'W00231' or 'P5191936' or 'P5193644':
        return Decimal(30.71)
    elif trailerNum == '546500':
        return Decimal(39.11)
    elif trailerNum == 'U969542':
        return Decimal(32.31)
    else:
        return Decimal(40.00)


def getLocDataList():
    locationData = trailerLocQuery()

    locationList = list(locationData)
    properList = []
    for i in range(len(locationList)):
        location = locationList[i]['trailerlocation__locationCity'] + "," + \
                   locationList[i]['trailerlocation__locationState'] + " " + \
                   locationList[i]['trailerlocation__locationCountry']

        destination = str(locationList[i]['trailertrip__shipment__destinationCity']) + "," + \
                      str(locationList[i]['trailertrip__shipment__destinationState'])

        dataList = [
            locationList[i]['trailerNumber'],
            location,
            locationList[i]['trailerlocation__statusCode'],
            locationList[i]['trailertrip__shipment__loadNumber'],
            destination,
            locationList[i]['trailertrip__shipment__carrier']
        ]
        properList.append(dataList)
    return properList


def getLocDataFields():
    fields = ['Trailer #', 'Location', 'Status', 'Load #', 'Destination', 'Carrier']
    return fields


def getEmailTable():
    locDataList = getLocDataList()
    fields = getLocDataFields()
    table = PrettyTable(fields)
    for i in range(len(locDataList)):
        table.add_row(locDataList[i])
    htmlTable = table.get_html_string(format=True)
    return htmlTable


def sendLocEmail():
    htmlTable = getEmailTable()
    msg = EmailMessage()
    msg['Subject'] = 'Trailer Locations '
    RHEEM_EMAIL = 'RheemTrailerUpdates@gmail.com'
    password = 'Smiley43!'
    tolist = ['Ntgw1596@gmail.com', 'michael.kiviat@shiprrexp.com ', 'freightpros1@gmail.com ']
    msg['From'] = RHEEM_EMAIL
    msg['To'] = tolist
    msg.add_alternative(htmlTable, subtype='html')
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(RHEEM_EMAIL, password)
        smtp.send_message(msg)


def getLocations():
    locDataDict = trailerdata.run()
    print(locDataDict)
    for key in locDataDict.keys():
        datalist = locDataDict[key]
        updateLocation(key, datalist)


def updateLocation(trailerNum, datalist):
    trailerLocation = TrailerLocation.objects.get(trailer__trailerNumber=trailerNum)
    trailerLocation.locationCity = datalist[2]
    trailerLocation.locationState = datalist[3]
    trailerLocation.locationCountry = datalist[4].upper()
    trailerLocation.latitude = datalist[0]
    trailerLocation.longitude = datalist[1]
    trailerLocation.save()


def createFirstTrailerLoc(trailerId):
    trailer = Trailer.objects.get(id=trailerId)
    trailerLocation = TrailerLocation(trailer=trailer)
    trailerLocation.save()


def createFirstTrailerTrip(trailerId):
    trailer = Trailer.objects.get(id=trailerId)
    trailerTrip = TrailerTrip(trailer=trailer)
    trailerTrip.save()


def calcRate(shipmentId):
    shipment = Shipment.objects.get(id=shipmentId)
    shipment.rateTotal = shipment.rateLineHaul + shipment.rateFSC + shipment.rateExtras
    if shipment.customCarrierRate is False:
        if checkRate(shipment.destinationState) is False:
            shipment.rateTotalCarrier = ((shipment.rateLineHaul * Decimal(
                0.8)) + shipment.rateFSC + shipment.rateExtras) - Decimal(250)
        else:
            rateList = checkRate(shipment.destinationState)
            miles = shipment.rateLineHaul / Decimal(rateList[1])
            linehaul = Decimal(miles) * Decimal(rateList[2])
            shipment.rateTotalCarrier = ((linehaul * Decimal(0.8)) + shipment.rateFSC + shipment.rateExtras) - Decimal(
                250)
    shipment.save()


def calcShipmentMargin(shipmentId):

    shipment = Shipment.objects.get(id=shipmentId)
    shipment.shipmentMargin = shipment.rateTotal - shipment.rateTotalCarrier
    shipment.shipmentMarginPercentage = (shipment.shipmentMargin / shipment.rateTotal) * 100
    shipment.save()


def updateTrailerTrip(shipmentId, trailer):
    shipment = Shipment.objects.get(id=shipmentId)
    trailerTrip = TrailerTrip.objects.get(trailer=trailer)
    trailerTrip.shipment = shipment
    trailerTrip.save()


def resetTrailerTrip(tripId):
    trailerTrip = TrailerTrip.objects.get(id=tripId)
    trailerTrip.dateYardEmpty = trailerTrip.dateCarrierReturnedEmpty
    trailerTrip.shipment = None
    trailerTrip.dateDrayPickedUp = None
    trailerTrip.dateDrayReturnedLoaded = None
    trailerTrip.dateCarrierPickedUpLoaded = None
    trailerTrip.dateCarrierDelivered = None
    trailerTrip.dateCarrierReturnedEmpty = None
    trailerTrip.save()


def createTripReport(tripId, shipmentId, trailerId):
    trailerTrip = TrailerTrip.objects.get(id=tripId)
    shipment = Shipment.objects.get(id=shipmentId)
    trailer = Trailer.objects.get(id=trailerId)
    daysYardEmpToDrayPu = trailerTrip.dateDrayPickedUp - trailerTrip.dateYardEmpty
    daysDrayPuToYardLoad = trailerTrip.dateDrayReturnedLoaded - trailerTrip.dateDrayPickedUp
    daysYardLoadToCarrPu = trailerTrip.dateCarrierPickedUpLoaded - trailerTrip.dateDrayReturnedLoaded
    daysCarrPuToDeliv = trailerTrip.dateCarrierDelivered - trailerTrip.dateCarrierPickedUpLoaded
    daysDelivToRetEmp = trailerTrip.dateCarrierReturnedEmpty - trailerTrip.dateCarrierDelivered

    trailerDaysOwed = calcTrailerDaysOwed(daysCarrPuToDeliv.days + daysDelivToRetEmp.days)
    totalDays = calcTotalDays(daysYardEmpToDrayPu, daysDrayPuToYardLoad, daysYardLoadToCarrPu,
                              daysCarrPuToDeliv, daysDelivToRetEmp)
    startDate = trailerTrip.dateYardEmpty
    endDate = trailerTrip.dateCarrierReturnedEmpty
    totalTrailerCost = Decimal(totalDays * getTrailerCost(trailer.trailerNumber))
    grossMargin = shipment.shipmentMargin
    netMargin = grossMargin - totalTrailerCost
    netMarginAfterTrailer = netMargin + (trailerDaysOwed * 30)
    tripReport = TripReport(trailer=trailer, shipment=shipment, daysYardEmpToDrayPu=daysYardEmpToDrayPu.days,
                            daysDrayPuToYardLoad=daysDrayPuToYardLoad.days,
                            daysYardLoadToCarrPu=daysYardLoadToCarrPu.days,
                            daysCarrPuToDeliv=daysCarrPuToDeliv.days, daysDelivToRetEmp=daysDelivToRetEmp.days,
                            trailerDaysOwed=trailerDaysOwed, totalDays=totalDays, startDate=startDate,
                            endDate=endDate, totalTrailerCost=totalTrailerCost, grossMargin=grossMargin,
                            netMargin=netMargin, netMarginAfterTrailer=netMarginAfterTrailer)
    tripReport.save()
    resetTrailerTrip(tripId)


def calcTrailerDaysOwed(days):
    if days < 8:
        return 0
    else:
        return days - 7


def calcTotalDays(days1, days2, days3, days4, days5):
    return days1.days + days2.days + days3.days + days4.days + days5.days


def getStatusCodes():
    trailerTrips = TrailerTrip.objects.all().values(
        'trailer__trailerNumber',
        'dateYardEmpty',
        'dateDrayPickedUp',
        'dateDrayReturnedLoaded',
        'dateCarrierPickedUpLoaded',
        'dateCarrierDelivered',
        'dateCarrierReturnedEmpty')

    for i in range(len(trailerTrips)):
        trailerNum = trailerTrips[i]['trailer__trailerNumber']
        updateStatusCode(trailerNum, trailerTrips[i])


def updateStatusCode(trailerNum, dataDict):
    trailerLocation = TrailerLocation.objects.get(trailer__trailerNumber=trailerNum)
    if dataDict['dateDrayPickedUp'] is None:
        trailerLocation.statusCode = "In Yard Empty Awaiting Dray Pickup"
    elif dataDict['dateDrayReturnedLoaded'] is None:
        trailerLocation.statusCode = "Currently Being Loaded in Mexico"
    elif dataDict['dateCarrierPickedUpLoaded'] is None:
        trailerLocation.statusCode = "In Yard Loaded Awaiting Carrier Pickup"
    elif dataDict['dateCarrierDelivered'] is None:
        trailerLocation.statusCode = "In Transit to receiver"
    elif dataDict['dateCarrierReturnedEmpty'] is None:
        trailerLocation.statusCode = "In Transit back to Yard"
    else:
        trailerLocation.statusCode = "Error"
    trailerLocation.save()


def updateTrailerLocations():
    getLocations()
    getStatusCodes()


def createCsv():
    locDataList = getLocDataList()
    fields = getLocDataFields()
    filename = 'trailer_locations.csv'
    with open(filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvwriter.writerows(locDataList)


# Various Queries To Go Below
def trailerLocQuery():
    trailers = Trailer.objects.all().values(
        'trailerNumber',
        'id',
        'trailerlocation__locationCity',
        'trailerlocation__locationState',
        'trailerlocation__locationCountry',
        'trailerlocation__statusCode',
        'trailertrip__shipment__loadNumber',
        'trailertrip__shipment__destinationCity',
        'trailertrip__shipment__destinationState',
        'trailerlocation__updated_at',
        'trailertrip__shipment__carrier',
        'shipment__id'
    )
        # .order_by('-trailerlocation__statusCode')
    return trailers


def tripReportQuery():
    tripreports = TripReport.objects.values(
        'shipment__loadNumber',
        'trailer__trailerNumber',
        'startDate',
        'endDate',
        'totalDays',
        'trailerDaysOwed',
        'totalTrailerCost',
        'grossMargin',
        'netMargin',
        'netMarginAfterTrailer',
        'shipment__destinationCity',
        'shipment__destinationState'
    ).order_by('-startDate')
    return tripreports


def shipmentAllQuery():
    shipments = Shipment.objects.values(
        'dateTendered',
        'loadNumber',
        'masterBolNumber',
        'carrier',
        'destinationCity',
        'destinationState',
        'rateTotal',
        'id',
        'trailer',
        'loadDelivered',
        'trailer__id',
        'rateTotalCarrier',
        'driverName',
        'shipmentMargin',
        'shipmentMarginPercentage',
        'trailer__trailerNumber',
        'trailer__trailertrip__shipment__id',
        'deliveryDate',
        'deliveryTime',
        'trailer__trailerlocation__locationCity',
        'trailertrip__dateYardEmpty',
        'trailertrip__dateDrayPickedUp',
        'trailertrip__dateDrayReturnedLoaded',
        'trailertrip__dateCarrierPickedUpLoaded',
        'trailertrip__dateCarrierDelivered',
        'trailertrip__dateCarrierReturnedEmpty',
        'trailer__trailerlocation__locationState'
    ).order_by('-dateTendered')
    return shipments


def shipmentDeliveredQuery():
    shipments = Shipment.objects.filter(loadDelivered=True).order_by('-dateTendered').values(
        'dateTendered',
        'loadNumber',
        'masterBolNumber',
        'carrier',
        'destinationCity',
        'destinationState',
        'rateTotal',
        'id',
        'trailer',
        'loadDelivered',
        'trailer__id',
        'rateTotalCarrier',
        'driverName',
        'shipmentMargin',
        'shipmentMarginPercentage',
        'trailer__trailerNumber',
        'trailer__trailertrip__shipment__id',
        'deliveryDate',
        'deliveryTime',
        'trailer__trailerlocation__locationCity',
        'trailertrip__dateYardEmpty',
        'trailertrip__dateDrayPickedUp',
        'trailertrip__dateDrayReturnedLoaded',
        'trailertrip__dateCarrierPickedUpLoaded',
        'trailertrip__dateCarrierDelivered',
        'trailertrip__dateCarrierReturnedEmpty',
        'trailer__trailerlocation__locationState'
    )
    return shipments


def shipmentTransitQuery():
    shipments = Shipment.objects.filter(loadDelivered=False).order_by('-dateTendered').values(
        'dateTendered',
        'loadNumber',
        'masterBolNumber',
        'carrier',
        'destinationCity',
        'destinationState',
        'rateTotal',
        'id',
        'trailer',
        'loadDelivered',
        'trailer__id',
        'rateTotalCarrier',
        'driverName',
        'shipmentMargin',
        'shipmentMarginPercentage',
        'trailer__trailerNumber',
        'trailer__trailertrip__shipment__id',
        'deliveryDate',
        'deliveryTime',
        'trailer__trailerlocation__locationCity',
        'trailertrip__dateYardEmpty',
        'trailertrip__dateDrayPickedUp',
        'trailertrip__dateDrayReturnedLoaded',
        'trailertrip__dateCarrierPickedUpLoaded',
        'trailertrip__dateCarrierDelivered',
        'trailertrip__dateCarrierReturnedEmpty',
        'trailer__trailerlocation__locationState'
    )
    return shipments
