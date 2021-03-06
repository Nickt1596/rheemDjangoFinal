# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import dateutil.tz
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
from django.conf import settings
from django.core.mail import send_mail
import csv
from geopy import distance
from geopy.geocoders import Nominatim


# Create your models here.

# This model will not change much. Only possible changes are when a new trailer is added or removed
class Trailer(models.Model):
    trailerNumber = models.CharField(max_length=200, unique=True)
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

    def save(self, *args, **kwargs):
        yard_cords = (27.650904, -99.623088)
        created = self._state.adding is True
        if created:
            super().save(*args, **kwargs)
        else:
            # TODO Reworking this Ideas
            # Every Iteration of if Uses trailerTrip
            dateNow = date.today()
            oldLocation = TrailerLocation.objects.get(id=self.id)
            trailerTrip = TrailerTrip.objects.get(trailer=self.trailer)
            # Checks if Dray Picked up
            if oldLocation.statusCode == "In Yard Empty Awaiting Dray Pickup":
                if oldLocation.locationCountry == 'US' and self.locationCountry == 'MX':
                    trailerTrip.dateDrayPickedUp = dateNow
                    trailerTrip.save()
                    self.statusCode = "Currently Being Loaded in Mexico"
                    sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, None)

            # Checks if Dray Returned Loaded
            if oldLocation.statusCode == "Currently Being Loaded in Mexico":
                if oldLocation.locationCountry == 'MX' and self.locationCountry == 'US':
                    trailerTrip.dateDrayReturnedLoaded = dateNow
                    trailerTrip.save()
                    self.statusCode = "In Yard Loaded Awaiting Carrier Pickup"
                    sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, None)

            # Checks if Carrier Picked up Loaded
            if oldLocation.statusCode == "In Yard Loaded Awaiting Carrier Pickup":
                current_cords = (self.latitude, self.longitude)
                distanceBetween = distance.distance(yard_cords, current_cords).miles
                if distanceBetween > 1.0:
                    trailerTrip.dateCarrierPickedUpLoaded = dateNow
                    trailerTrip.save()
                    self.statusCode = "In Transit to receiver"
                    sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, None)

            # TODO FINISH THIS - IDEA Add More Status Codes
            # Checks if Carrier Arrived at Delivery
            if oldLocation.statusCode == "In Transit to receiver":
                trailerShipment = TrailerTrip.objects.get(trailer=self.trailer)
                loadNumber = trailerShipment.shipment.loadNumber
                # Checks if within range of Destination
                if self.checkIfAtDeliv():
                    if dateNow == trailerShipment.shipment.deliveryDate:
                        trailerTrip.dateCarrierDelivered = dateNow
                        trailerTrip.save()
                        self.statusCode = "Driver is at delivery location on delivery day"
                        sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, loadNumber)
                    else:
                        self.statusCode = "Driver arrived to the destination city"
                        sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, loadNumber)

            # Checks if Driver has delivered
            if oldLocation.statusCode == "Driver is at delivery location on delivery day":
                trailerShipment = TrailerTrip.objects.get(trailer=self.trailer)
                loadNumber = trailerShipment.shipment.loadNumber
                if self.checkIfAtDeliv() is False:
                    self.statusCode = "In Transit back to Yard"
                    sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, loadNumber)

            # Checks if today is delivery day now
            if oldLocation.statusCode == "Driver arrived to the destination city":
                trailerShipment = TrailerTrip.objects.get(trailer=self.trailer)
                loadNumber = trailerShipment.shipment.loadNumber
                if dateNow == trailerShipment.shipment.deliveryDate:
                    trailerTrip.dateCarrierDelivered = dateNow
                    trailerTrip.save()
                    self.statusCode = "Driver is at delivery location on delivery day"
                    sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, loadNumber)

            # Checks if Carrier Returned Empty
            if oldLocation.statusCode == "In Transit back to Yard":
                current_cords = (self.latitude, self.longitude)
                distanceBetween = distance.distance(yard_cords, current_cords).miles
                if distanceBetween < 1.0:
                    # trailerTrip = TrailerTrip.objects.get(trailer=self.trailer)
                    trailerTrip.dateCarrierReturnedEmpty = dateNow
                    trailerTrip.save()
                    self.statusCode = "In Yard Empty Awaiting Dray Pickup"
                    sendStatusEmail(self.trailer.trailerNumber, self.statusCode, dateNow, None)
        super().save(*args, **kwargs)

    def checkIfAtDeliv(self):
        trailerShipment = TrailerTrip.objects.get(trailer=self.trailer)
        if trailerShipment.shipment.destBottomLat <= float(
                self.latitude) <= trailerShipment.shipment.destTopLat and trailerShipment.shipment.destRightLong <= float(
            self.longitude) <= trailerShipment.shipment.destLeftLong:
            return True
        else:
            return False


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

    destBottomLat = models.FloatField(null=True, blank=True)
    destTopLat = models.FloatField(null=True, blank=True)
    destRightLong = models.FloatField(null=True, blank=True)
    destLeftLong = models.FloatField(null=True, blank=True)

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
        created = self._state.adding is True
        if created:
            self.calcRate()
            if self.customCarrierRate is False:
                self.calcShipmentMargin()
            if self.trailer is not None:
                super().save(*args, **kwargs)
                self.updateTrailerTrip()
        else:
            oldShipment = Shipment.objects.get(id=self.id)
            if self.rateTotalCarrier != oldShipment.rateTotalCarrier:
                self.customCarrierRate = True
                self.calcShipmentMargin()
            if self.trailer != oldShipment.trailer:
                oldTrailerTrip = TrailerTrip.objects.get(shipment=oldShipment.id)
                oldTrailerTrip.shipment = None
                oldTrailerTrip.save()
                self.updateTrailerTrip()
            newRateTotal = self.rateLineHaul + self.rateFSC + self.rateExtras
            if oldShipment.rateTotal != newRateTotal:
                self.calcRate()
                self.calcShipmentMargin()
        super().save(*args, **kwargs)
        if self.destTopLat is None:
            self.getBoundingBox()
            super().save(*args, **kwargs)

    def calcRate(self):
        self.rateTotal = self.rateLineHaul + self.rateFSC + self.rateExtras
        if self.customCarrierRate is False:
            if checkRate(self.destinationState) is False:
                self.rateTotalCarrier = ((self.rateLineHaul * Decimal(0.8)) + self.rateFSC + self.rateExtras) \
                                        - Decimal(250)
            else:
                rateList = checkRate(self.destinationState)
                miles = self.rateLineHaul / Decimal(rateList[1])
                linehaul = Decimal(miles) * Decimal(rateList[2])
                self.rateTotalCarrier = ((linehaul * Decimal(0.8)) + self.rateFSC + self.rateExtras) - Decimal(250)

    def calcShipmentMargin(self):
        self.shipmentMargin = self.rateTotal - self.rateTotalCarrier
        self.shipmentMarginPercentage = (self.shipmentMargin / self.rateTotal) * 100

    def updateTrailerTrip(self):
        trailerTrip = TrailerTrip.objects.get(trailer=self.trailer)
        trailerTrip.shipment = self
        trailerTrip.save()

    def getBoundingBox(self):
        destination = self.destinationCity + ', ' + self.destinationState
        geoLocator = Nominatim(user_agent="geoapiExercises")
        location = geoLocator.geocode(destination)
        locationDict = location.raw
        boundingBox = locationDict["boundingbox"]
        self.destBottomLat = float(boundingBox[0])
        self.destTopLat = float(boundingBox[1])
        self.destRightLong = float(boundingBox[2])
        self.destLeftLong = float(boundingBox[3])


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
        if self.dateCarrierDelivered is not None:
            shipment = Shipment.objects.get(id=self.shipment.id)
            shipment.loadDelivered = True
            shipment.save()
        if self.dateDrayReturnedLoaded is not None:
            daysWithDray = (self.dateDrayReturnedLoaded - self.dateDrayPickedUp).days
            if daysWithDray > 3:
                # TODO VERIFICATION HERE
                if RheemCharge.objects.filter(shipment=self.shipment).exists() is False:
                    rheemCharge = RheemCharge(trailer=self.trailer, shipment=self.shipment, chargeType='STOR',
                                              daysOwed=daysWithDray - 3, startDate=self.dateDrayPickedUp,
                                              endDate=self.dateDrayReturnedLoaded)
                    rheemCharge.save()
        if self.dateCarrierReturnedEmpty is not None:
            self.createTripReport()
        super().save(*args, **kwargs)

    def createTripReport(self):
        newTripReport = TripReport(trailer=self.trailer, shipment=self.shipment)
        newTripReport.daysYardEmpToDrayPu = (self.dateDrayPickedUp - self.dateYardEmpty).days
        newTripReport.daysDrayPuToYardLoad = (self.dateDrayReturnedLoaded - self.dateDrayPickedUp).days
        newTripReport.daysYardLoadToCarrPu = (self.dateCarrierPickedUpLoaded - self.dateDrayReturnedLoaded).days
        newTripReport.daysCarrPuToDeliv = (self.dateCarrierDelivered - self.dateCarrierPickedUpLoaded).days
        newTripReport.daysDelivToRetEmp = (self.dateCarrierReturnedEmpty - self.dateCarrierDelivered).days
        newTripReport.trailerDaysOwed = calcTrailerDaysOwed(newTripReport.daysCarrPuToDeliv +
                                                            newTripReport.daysDelivToRetEmp)
        newTripReport.totalDays = (newTripReport.daysYardEmpToDrayPu + newTripReport.daysDrayPuToYardLoad +
                                   newTripReport.daysYardLoadToCarrPu + newTripReport.daysCarrPuToDeliv +
                                   newTripReport.daysDelivToRetEmp)
        newTripReport.startDate = self.dateYardEmpty
        newTripReport.endDate = self.dateCarrierReturnedEmpty
        newTripReport.totalTrailerCost = Decimal(newTripReport.totalDays * getTrailerCost(self.trailer.trailerNumber))
        newTripReport.grossMargin = self.shipment.shipmentMargin
        newTripReport.netMargin = newTripReport.grossMargin - newTripReport.totalTrailerCost
        newTripReport.netMarginAfterTrailer = newTripReport.netMargin + (newTripReport.trailerDaysOwed * 30)
        newTripReport.save()
        self.resetTrailerTrip()

    def resetTrailerTrip(self):
        self.dateYardEmpty = self.dateCarrierReturnedEmpty
        self.shipment = None
        self.dateDrayPickedUp = None
        self.dateDrayReturnedLoaded = None
        self.dateCarrierPickedUpLoaded = None
        self.dateCarrierDelivered = None
        self.dateCarrierReturnedEmpty = None


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.trailerDaysOwed > 0:
            carrierCharge = CarrierCharge(tripReport=self, shipment=self.shipment, daysOwed=self.trailerDaysOwed)
            carrierCharge.save()


# class Expense(models.Model):
#     PAYMENT_TERMS = [
#         ('LUMP', 'Lump-Sum'),
#         ('WEEK', 'Weekly'),
#         ('MONTH', 'Monthly'),
#     ]
#     trailer = models.ForeignKey(Trailer, on_delete=models.PROTECT, blank=True, null=True)
#     shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, blank=True, null=True)
#     amountOwed = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
#     paymentTerms = models.CharField(max_length=100, blank=True, choices=PAYMENT_TERMS, default='LUMP')
#     expenseType = models.CharField(max_length=100, blank=True, null=True)
#     carrier = models.CharField(max_length=100, blank=True, null=True)
#     driver = models.CharField(max_length=100, blank=True, null=True)
#     id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

class CarrierCharge(models.Model):
    tripReport = models.ForeignKey(TripReport, on_delete=models.PROTECT, blank=True, null=True)
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, blank=True, null=True)
    daysOwed = models.IntegerField(null=True, blank=True)
    amountOwed = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    paid = models.BooleanField(default=False)
    dateOccurred = models.DateTimeField(auto_now=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.tripReport.trailer.trailerNumber + " " + self.shipment.loadNumber

    def save(self, *args, **kwargs):
        self.amountOwed = self.daysOwed * Decimal(30)
        created = self._state.adding is True
        if created:
            super().save(*args, **kwargs)
            emailTripReport = self.tripReport
            emailShipment = self.shipment
            emailCarrierCharge = CarrierCharge.objects.get(id=self.id)
            sendCarrierChargeEmail(emailTripReport, emailShipment, emailCarrierCharge)
        super().save(*args, **kwargs)


class RheemCharge(models.Model):
    ACCESSORIAL_TYPE = [
        ('DET', 'Detention'),
        ('REC', 'Reconsignment'),
        ('ASST', 'Driver-Assist'),
        ('TONU', 'TONU'),
        ('STOR', 'Storage Fee'),
        ('OTH', 'Other'),
    ]
    trailer = models.ForeignKey(Trailer, on_delete=models.PROTECT, blank=True, null=True)
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, blank=True, null=True)
    chargeType = models.CharField(max_length=100, blank=True, choices=ACCESSORIAL_TYPE, default='OTH')
    daysOwed = models.IntegerField(null=True, blank=True)
    amountOwed = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    startDate = models.DateField(null=True, blank=True)
    endDate = models.DateField(null=True, blank=True)
    paid = models.BooleanField(default=False)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.trailer.trailerNumber + " " + self.shipment.loadNumber

    def save(self, *args, **kwargs):
        if self.chargeType == 'STOR':
            self.amountOwed = self.daysOwed * Decimal(50)
        created = self._state.adding is True
        if created:
            super().save(*args, **kwargs)
            dateStamp = date.today()
            emailShipment = self.shipment
            emailRheemCharge = RheemCharge.objects.get(id=self.id)
            sendRheemChargeEmail(dateStamp, emailShipment, emailRheemCharge)
        super().save(*args, **kwargs)


################################
# Model Helper Functions Below #
################################

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
        'MD': [3.7, 3.95, 3.70],
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


def getLocations():
    locDataDict = trailerdata.run()
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


# Used by Trailer Model
def createFirstTrailerLoc(trailerId):
    trailer = Trailer.objects.get(id=trailerId)
    trailerLocation = TrailerLocation(trailer=trailer)
    trailerLocation.save()


# Used by Trailer Model
def createFirstTrailerTrip(trailerId):
    trailer = Trailer.objects.get(id=trailerId)
    trailerTrip = TrailerTrip(trailer=trailer)
    trailerTrip.save()


# Helper for createTripReport
def calcTrailerDaysOwed(days):
    if days < 8:
        return 0
    else:
        return days - 7


# Helper for createTripReport
def calcTotalDays(days1, days2, days3, days4, days5):
    return days1.days + days2.days + days3.days + days4.days + days5.days


# Helper for updateTrailerLocations
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


# Helper for updateTrailerLocations
def updateStatusCode(trailerNum, dataDict):
    trailerLocation = TrailerLocation.objects.get(trailer__trailerNumber=trailerNum)
    if dataDict['dateDrayPickedUp'] is None:
        trailerLocation.statusCode = "In Yard Empty Awaiting Dray Pickup"
    elif dataDict['dateDrayReturnedLoaded'] is None:
        trailerLocation.statusCode = "Currently Being Loaded in Mexico"
    elif dataDict['dateCarrierPickedUpLoaded'] is None:
        trailerLocation.statusCode = "In Yard Loaded Awaiting Carrier Pickup"
    elif dataDict['dateCarrierDelivered'] is None:
        if trailerLocation.statusCode != "Driver is at delivery location on delivery day" and trailerLocation.statusCode != "Driver arrived to the destination city" and trailerLocation.statusCode != "Driver is not in Delivery City on Delivery Day":
            trailerLocation.statusCode = "In Transit to receiver"
    elif dataDict['dateCarrierReturnedEmpty'] is None:
        trailerLocation.statusCode = "In Transit back to Yard"
    else:
        trailerLocation.statusCode = "Error"
    trailerLocation.save()


# Helper function to update the trailer locations
def updateTrailerLocations():
    getLocations()
    getStatusCodes()


# def createCsv():
#     locDataList = getLocDataList()
#     fields = getLocDataFields()
#     filename = 'trailer_locations.csv'
#     with open(filename, 'w', newline='') as csvfile:
#         csvwriter = csv.writer(csvfile)
#         csvwriter.writerow(fields)
#         csvwriter.writerows(locDataList)


#####################################################
# Implementing New Functions to handle e-mails here #
#####################################################
def trailerLocEmail(trailerList):
    if 'ALL' in trailerList:
        locationData = trailerLocEmailQuery()
        locationList = list(locationData)
        dataList = formatLocData(locationList)
    else:
        locationData = trailerLocEmailNotAll(trailerList)
        locationList = list(locationData)
        dataList = formatLocData(locationList)
    return trailerLocTable(dataList)


def formatLocData(locationList):
    properList = []
    for i in range(len(locationList)):
        location = locationList[i]['trailer__trailerlocation__locationCity'] + "," + \
                   locationList[i]['trailer__trailerlocation__locationState'] + " " + \
                   locationList[i]['trailer__trailerlocation__locationCountry']

        destination = str(locationList[i]['shipment__destinationCity']) + "," + \
                      str(locationList[i]['shipment__destinationState'])

        dataList = [
            locationList[i]['trailer__trailerNumber'],
            location,
            locationList[i]['trailer__trailerlocation__statusCode'],
            locationList[i]['shipment__loadNumber'],
            destination,
            locationList[i]['shipment__carrier']
        ]
        properList.append(dataList)
    return properList


def trailerLocTable(dataList):
    fields = trailerLocFields()
    table = PrettyTable(fields)
    for i in range(len(dataList)):
        table.add_row(dataList[i])
    htmlTable = table.get_html_string(format=True)
    return htmlTable


def trailerLocFields():
    fields = ['Trailer #', 'Location', 'Status', 'Load #', 'Destination', 'Carrier']
    return fields


def shipmentTransitEmail(shipmentList):
    if 'ALL' in shipmentList:
        shipmentData = shipmentTransitQuery()
        shipmentList = list(shipmentData)
        dataList = formatShipmentTransData(shipmentList)
    else:
        shipmentData = shipmentTransitQueryNotAll(shipmentList)
        shipmentList = list(shipmentData)
        dataList = formatShipmentTransData(shipmentList)
    return shipmentTransTable(dataList)


def formatShipmentTransData(shipmentList):
    properList = []
    for i in range(len(shipmentList)):
        shipmentDest = shipmentList[i]['destinationCity'] + ', ' + shipmentList[i]['destinationState']
        trailerLoc = shipmentList[i]['trailer__trailerlocation__locationCity'] + ', ' + \
                     shipmentList[i]['trailer__trailerlocation__locationState']
        dataList = [
            shipmentList[i]['loadNumber'],
            shipmentDest,
            shipmentList[i]['trailer__trailerNumber'],
            trailerLoc
        ]
        properList.append(dataList)
    return properList


def shipmentTransTable(dataList):
    fields = shipmentTransFields()
    table = PrettyTable(fields)
    for i in range(len(dataList)):
        table.add_row(dataList[i])
    htmlTable = table.get_html_string(format=True)
    return htmlTable


def shipmentTransFields():
    fields = ['Load #', 'Destination', 'Trailer #', 'Trailer Location']
    return fields


def trailerDrayEmail(trailerList):
    if 'ALL' in trailerList:
        trailerData = trailerDrayQuery()
        drayTrailerList = list(trailerData)
    else:
        trailerData = trailerDrayNotAllQuery(trailerList)
        drayTrailerList = list(trailerData)
    numTrailers = str(len(drayTrailerList))
    message = "Hello, \n \n We have " + numTrailers + " Trailers Available for pickup. \n \n"
    for i in range(len(drayTrailerList)):
        trailerNum = drayTrailerList[i]['trailer__trailerNumber']
        trailerPlateNum = drayTrailerList[i]['trailer__trailerPlateNumber']
        trailerPlateState = drayTrailerList[i]['trailer__trailerPlateState']
        trailerString = str(trailerNum) + " " + str(trailerPlateNum) + " " + str(trailerPlateState) + "\n"
        message = message + trailerString
    return message


# Function below used to send e-mails to advice of Status Code changes
def sendStatusEmail(trailerNumber, statusCode, date, loadNumber):
    recipient_list = ['freightpros1@shiprrexp.com ', 'nicholas.tallarico@shiprrexp.com']
    email_from = 'logistics@freightprostracking.com'
    subject = getEmailSubject(statusCode, trailerNumber, loadNumber)
    message = getEmailMessage(statusCode, trailerNumber, date, loadNumber)
    send_mail(subject, message, email_from, recipient_list, fail_silently=False)


def getEmailSubject(statusCode, trailerNumber, loadNumber):
    if statusCode == "Currently Being Loaded in Mexico":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: Dray has picked up'
    elif statusCode == "In Yard Loaded Awaiting Carrier Pickup":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: In yard loaded'
    elif statusCode == "In Transit to receiver":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: Carrier Picked Up'
    elif statusCode == "In Yard Empty Awaiting Dray Pickup":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: Carrier Returned Empty Trailer'
    elif statusCode == "Driver is at delivery location on delivery day":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: Driver is at Delivery Location'
    elif statusCode == "Driver arrived to the destination city":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: Driver is in Destination City'
    elif statusCode == "Driver is not in Delivery City on Delivery Day":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: Driver is not at Delivery Location'
    elif statusCode == "In Transit back to Yard":
        subject = 'Trailer ' + str(trailerNumber) + ' Notification: Driver In Transit back to yard'
    else:
        subject = 'Error'
    return subject


def getEmailMessage(statusCode, trailerNumber, date, loadNumber):
    if statusCode == "Currently Being Loaded in Mexico":
        message = 'Trailer ' + str(trailerNumber) + ' Has been picked by dray on ' + str(date)
    elif statusCode == "In Yard Loaded Awaiting Carrier Pickup":
        message = 'Trailer ' + str(trailerNumber) + ' Has been returned loaded by Dray on ' + str(date)
    elif statusCode == "In Transit to receiver":
        message = 'Trailer ' + str(trailerNumber) + ' Has been picked by the carrier on ' + str(date)
    elif statusCode == "In Yard Empty Awaiting Dray Pickup":
        message = 'Trailer ' + str(trailerNumber) + ' Has been returned empty by the carrier on ' + str(date)
    elif statusCode == "Driver is at delivery location on delivery day":
        message = 'Trailer ' + str(trailerNumber) + ' Driver is currently at the delivery location.'
    elif statusCode == "Driver arrived to the destination city":
        message = 'Trailer ' + str(trailerNumber) + ' Driver is currently in the delivery city.'
    elif statusCode == "Driver is not in Delivery City on Delivery Day":
        message = 'Trailer ' + str(trailerNumber) + ' Driver is not at the delivery location on delivery day.'
    elif statusCode == "In Transit back to Yard":
        message = 'Trailer ' + str(trailerNumber) + ' Driver is in transit back to the yard.'
    else:
        message = 'Error'
    return message


# Function below used to send Carrier Charge Notif Email
def sendCarrierChargeEmail(tripReport, shipment, carrierCharge):
    recipient_list = ['freightpros1@shiprrexp.com ', 'nicholas.tallarico@shiprrexp.com']
    email_from = 'logistics@freightprostracking.com'
    subject = 'New Carrier Charge Notification ' + str(tripReport.trailer.trailerNumber)
    driverName = str(shipment.driverName)
    carrier = str(shipment.carrier)
    trailerNumber = str(tripReport.trailer.trailerNumber)
    shipmentNumber = str(shipment.loadNumber)
    mBol = str(shipment.masterBolNumber)
    daysWithTrailer = str(tripReport.daysCarrPuToDeliv + tripReport.daysDelivToRetEmp)
    daysOwed = str(tripReport.trailerDaysOwed)
    amountOwed = str(tripReport.trailerDaysOwed * 30)

    message = 'Driver Name: ' + driverName + '\n' \
              + 'Carrier: ' + carrier + '\n' \
              + 'Trailer #: ' + trailerNumber + '\n' \
              + 'Shipment #: ' + shipmentNumber + '\n' \
              + 'MBOL #: ' + mBol + '\n' \
              + 'Days With Trailer: ' + daysWithTrailer + '\n' \
              + 'Days Owed: ' + daysOwed + '\n' \
              + 'Amount Owed: $' + amountOwed
    send_mail(subject, message, email_from, recipient_list, fail_silently=False)


def sendRheemChargeEmail(date, shipment, rheemCharge):
    recipient_list = ['freightpros1@shiprrexp.com ', 'nicholas.tallarico@shiprrexp.com']
    email_from = 'logistics@freightprostracking.com'
    subject = 'New Rheem Charge Notification ' + str(shipment.loadNumber)
    dateOfRequest = str(date)
    bolNum = str(shipment.masterBolNumber)
    if rheemCharge.chargeType == 'STOR':
        accessorial = 'Storage'
    else:
        accessorial = 'Unknown'
    charge = str(rheemCharge.amountOwed)
    consignee = str(shipment.destinationCity) + ', ' + str(shipment.destinationState)

    message = 'Date of Request: ' + dateOfRequest + '\n' \
              + 'Carrier: ' + 'GT WorldWide Transport' + '\n' \
              + 'Contact Name: ' + 'Nick Tallarico' + '\n' \
              + 'Contact Phone: ' + '5163179038' + '\n' \
              + 'Contact Email: ' + 'nicholas.tallarico@shiprrexp.com' + '\n' \
              + 'BOL #: ' + bolNum + '\n' \
              + 'Accessorial: ' + accessorial + '\n' \
              + 'Charge: ' + '$' + charge + '\n' \
              + 'Consignee: ' + consignee + '\n' \
              + 'Ship Date: ' + dateOfRequest + '\n' \
              + 'MBOL #: ' + bolNum + '\n' \
              + 'Appt Date/Time: ' + 'N/A' + '\n' \
              + 'Reason For Request: ' + 'Trailer was in Mexico for ' + str(
        rheemCharge.daysOwed + 3) + ' Which leaves ' + str(rheemCharge.daysOwed) + ' days worth of Storage Fees.'
    send_mail(subject, message, email_from, recipient_list, fail_silently=False)


###################
# Query Functions #
###################
def trailerLocQuery():
    trailers = TrailerTrip.objects.all().values(
        'trailer__trailerNumber',
        'trailer__id',
        'trailer__trailerlocation__locationCity',
        'trailer__trailerlocation__locationState',
        'trailer__trailerlocation__locationCountry',
        'trailer__trailerlocation__statusCode',
        'trailer__trailerlocation__updated_at',
        'shipment__loadNumber',
        'shipment__destinationCity',
        'shipment__destinationState',
        'shipment__carrier',
        'shipment__id',
        'shipment__driverName',
        'shipment__driverCell'
    ).order_by('-trailer__trailerlocation__statusCode')
    return trailers


def trailerLocEmailQuery():
    trailers = TrailerTrip.objects.all().values(
        'trailer__trailerNumber',
        'trailer__id',
        'trailer__trailerlocation__locationCity',
        'trailer__trailerlocation__locationState',
        'trailer__trailerlocation__locationCountry',
        'trailer__trailerlocation__statusCode',
        'shipment__loadNumber',
        'shipment__destinationCity',
        'shipment__destinationState',
        'shipment__carrier'
    ).order_by('-trailer__trailerlocation__statusCode')
    return trailers


def trailerLocEmailNotAll(trailerList):
    trailer = TrailerTrip.objects.filter(trailer__id__in=trailerList).values(
        'trailer__trailerNumber',
        'trailer__trailerlocation__locationCity',
        'trailer__trailerlocation__locationState',
        'trailer__trailerlocation__locationCountry',
        'trailer__trailerlocation__statusCode',
        'shipment__loadNumber',
        'shipment__destinationCity',
        'shipment__destinationState',
        'shipment__carrier'
    )
    return trailer


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


def shipmentTransitQueryNotAll(shipmentList):
    shipments = Shipment.objects.filter(id__in=shipmentList, loadDelivered=False).order_by('-dateTendered').values(
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


def trailerDrayQuery():
    trailers = TrailerLocation.objects.filter(statusCode='In Yard Empty Awaiting Dray Pickup').values(
        'trailer__trailerNumber',
        'trailer__trailerPlateNumber',
        'trailer__trailerPlateState'
    )
    return trailers


def trailerDrayNotAllQuery(trailerList):
    trailers = TrailerLocation.objects.filter(trailer__id__in=trailerList,
                                              statusCode='In Yard Empty Awaiting Dray Pickup').values(
        'trailer__trailerNumber',
        'trailer__trailerPlateNumber',
        'trailer__trailerPlateState'
    )
    return trailers


def rheemChargeQuery():
    rheemCharges = RheemCharge.objects.values(
        'trailer__trailerNumber',
        'shipment__loadNumber',
        'startDate',
        'endDate',
        'chargeType',
        'amountOwed',
        'paid'
    ).order_by('-startDate')
    return rheemCharges


def carrierChargeQuery():
    carrierCharges = CarrierCharge.objects.values(
        'paid',
        'dateOccurred',
        'tripReport__trailer__trailerNumber',
        'shipment__loadNumber',
        'shipment__carrier',
        'shipment__driverName',
        'daysOwed',
        'amountOwed'
    ).order_by('-dateOccurred')
    return carrierCharges


########################################
# Functions Below Used for Email Forms #
########################################
def getLocChoices():
    locChoices = [
        ('ALL', 'All')
    ]
    locationData = trailerLocQuery()
    locationList = list(locationData)
    for i in range(len(locationList)):
        trailerTuple = (locationList[i]['trailer__id'], locationList[i]['trailer__trailerNumber'])
        locChoices.append(trailerTuple)
    return locChoices


def getStChoices():
    stChoices = [
        ('ALL', 'All')
    ]
    shipmentData = shipmentTransitQuery()
    shipmentList = list(shipmentData)
    for i in range(len(shipmentList)):
        shipmentId = shipmentList[i]['id']
        shipmentLoadNum = shipmentList[i]['loadNumber']
        shipmentDestCity = shipmentList[i]['destinationCity']
        shipmentDestState = shipmentList[i]['destinationState']
        shipmentString = str(shipmentLoadNum) + " " + str(shipmentDestCity) + ", " + str(shipmentDestState)
        shipmentTuple = (shipmentId, shipmentString)
        stChoices.append(shipmentTuple)
    return stChoices


def getDpuChoices():
    dpuChoices = [
        ('ALL', 'All')
    ]
    locationData = trailerLocQuery()
    locationList = list(locationData)
    for i in range(len(locationList)):
        if locationList[i]['trailer__trailerlocation__statusCode'] == 'In Yard Empty Awaiting Dray Pickup':
            trailerTuple = (locationList[i]['trailer__id'], locationList[i]['trailer__trailerNumber'])
            dpuChoices.append(trailerTuple)
    return dpuChoices
