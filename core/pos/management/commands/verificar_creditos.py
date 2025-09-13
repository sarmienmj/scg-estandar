from django.core.management.base import BaseCommand, CommandError

from pos.models import Credito

class Command(BaseCommand):

    def handle(self, *args, **options):
        help = "Verifica Estatus de los Creditos"
        creditos = Credito.objects.all()
        for credito in creditos:
            credito.verificar_vencimiento()
            
        self.stdout.write(self.style.SUCCESS('Credito verificado'))