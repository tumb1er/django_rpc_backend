import django
from django.utils.timezone import now

django.setup()

from rpc_client.models import ClientModel


print(ClientModel.objects.all())

c = ClientModel.objects.create(dt_field=now())