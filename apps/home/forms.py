from django.forms import *
from django import forms
from .models import *


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


class TrailerForm(ModelForm):
    class Meta:
        model = Trailer
        fields = ['trailerNumber', 'trailerPlateState', 'trailerPlateNumber', 'trailerLeaseCompany']
        labels = {
            'trailerNumber': 'Trailer Number',
            'trailerPlateState': 'Plate State',
            'trailerPlateNumber': 'Plate Number',
            'trailerLeaseCompany': 'Lease Company'
        }

    def __init__(self, *args, **kwargs):
        super(TrailerForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


# Add in Carrier Choice Field
class ShipmentForm(ModelForm):
    class Meta:
        model = Shipment
        fields = ['dateTendered', 'loadNumber', 'masterBolNumber', 'destinationCity', 'destinationState',
                  'rateLineHaul', 'rateFSC', 'rateExtras', 'trailer', 'customCarrierRate']
        labels = {
            'dateTendered': 'Date Tendered',
            'loadNumber': 'Load Number',
            'masterBolNumber': 'BOL Number',
            'destinationCity': 'Delivery City',
            'destinationState': 'Delivery State',
            'rateLineHaul': 'Line Haul',
            'rateFSC': 'FSC',
            'rateExtras': 'Extras',
            'customCarrierRate': 'Use Custom Carrier Rate'
        }

        widgets = {'dateTendered': DateInput()}

    def __init__(self, *args, **kwargs):
        super(ShipmentForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if name != 'customCarrierRate':
                field.widget.attrs.update({'class': 'form-control'})

        self.fields['dateTendered'].widget.attrs.update({'placeholder': 'test', 'type': 'date'})
        self.fields['customCarrierRate'].widget.attrs.update({'class': 'form-check-input', 'type': 'checkbox'})
        self.fields['trailer'].widget.attrs['class'] = 'form-control bg-dark'


class CarrierRateForm(ModelForm):
    class Meta:
        model = Shipment
        fields = ['rateTotalCarrier']
        labels = {'rateTotalCarrier': 'Carrier Rate'}

    def __init__(self, *args, **kwargs):
        super(CarrierRateForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class ShipmentDeliveryForm(ModelForm):
    class Meta:
        model = Shipment
        fields = ['deliveryDate', 'deliveryTime']
        labels = {'deliveryDate': 'Date', 'deliveryTime': 'Time'}

        widgets = {
            'deliveryDate': DateInput(),
            'deliveryTime': TimeInput()
        }

    def __init__(self, *args, **kwargs):
        super(ShipmentDeliveryForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class AssignTrailerForm(ModelForm):
    class Meta:
        model = Shipment
        fields = ['trailer']
        labels = {'trailer': 'Trailer'}

        widgets = {'trailer': Select}

    def __init__(self, *args, **kwargs):
        super(AssignTrailerForm, self).__init__(*args, **kwargs)
        self.fields['trailer'].widget.attrs['class'] = 'form-control bg-dark'
    #
    #     for name, field in self.fields.items():
    #         field.widget.attrs.update({'class': 'form-control bg-dark"'})


class AssignCarrierForm(ModelForm):
    class Meta:
        model = Shipment
        fields = ['carrier']
        labels = {'carrier': 'Carrier'}

    def __init__(self, *args, **kwargs):
        super(AssignCarrierForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class AssignDriverForm(ModelForm):
    class Meta:
        model = Shipment
        fields = ['driverName', 'driverCell']
        labels = {'driverName': 'Driver Name', 'driverCell': 'Driver Cell'}

    def __init__(self, *args, **kwargs):
        super(AssignDriverForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class TrailerTripForm(ModelForm):
    class Meta:
        model = TrailerTrip
        fields = ['dateDrayPickedUp', 'dateDrayReturnedLoaded', 'dateCarrierPickedUpLoaded',
                  'dateCarrierDelivered', 'dateCarrierReturnedEmpty']
        labels = {
            'dateDrayPickedUp': 'Date Dray Picked Up',
            'dateDrayReturnedLoaded': 'Date Dray Returned Loaded',
            'dateCarrierPickedUpLoaded': 'Date Carrier Picked Up Loaded',
            'dateCarrierDelivered': 'Date Carrier Delivered',
            'dateCarrierReturnedEmpty': 'Date Carrier Returned Empty'
        }
        widgets = {
            'dateDrayPickedUp': DateInput(),
            'dateDrayReturnedLoaded': DateInput(),
            'dateCarrierPickedUpLoaded': DateInput(),
            'dateCarrierDelivered': DateInput(),
            'dateCarrierReturnedEmpty': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super(TrailerTripForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class EmailForm(forms.Form):
    emailChoices = [
        ('LOC', 'Location Updates'),
        ('ST', 'Shipments and Current Location'),
        ('DPU', 'Trailers available for pickup')
    ]
    # If Location Updates, then another field is generated with a dropdown to select which Trailers you want
    # Updates for. All is selected by default, if something besides All is selected, unselect All.

    # If Shipments and Current Locations, a field is generated with a dropdown of all Shipments where
    # Load Delivered is False. Default selection is All, if something besides All is selected, unselect All.

    # Repeat above for Trailer Available for Pickup
    locChoices = getLocChoices()
    stChoices = getStChoices()
    dpuChoices = getDpuChoices()

    emailType = ChoiceField(choices=emailChoices)
    # Location Updates Select menu Logic
    # If all, we just use the getEmailTable function we currently have
    # If not, we take the list with this choices, iterate over that list and get the data for each trailer in that
    # list, and then create a table and send.
    locSelect = MultipleChoiceField(choices=locChoices)
    stSelect = MultipleChoiceField(choices=stChoices)
    dpuSelect = MultipleChoiceField(choices=dpuChoices)
    recipient = EmailField(required=True)

    widgets = {'emailChoices': Select}




