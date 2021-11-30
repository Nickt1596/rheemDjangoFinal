from django.core.management.base import BaseCommand, CommandError
from apps.home.models import *
from apps.home import trailerdata


class Command(BaseCommand):
    help = 'Updates the current trailer locations'

    def handle(self, *args, **options):
        updateTrailerLocations()
        return
