## Django RPC database backend

Предоставляет удаленный доступ к Django-моделям связанного микросервиса через Сelery.

### Quickstart

1. Запустить на сервере celery worker с приложением `django_rpc.celery.app.celery`
2. На клиентской части описать нужные модели, отнаследовавшись от `django_rpc.models.RpcModel`
3. Использовать Django-модели как обычно.

### Demo

```python 

# В Django-окружении:
from django.conf import settings

from django.db import models, connections
from django_rpc.models import RpcModel

settings.DATABASES['rpc'] = {
    'BROKER_URL': 'amqp://guest@localhost/',
    'DEFAULT_QUEUE_NAME': 'django_rpc',
    'PRIORITY_QUEUE_NAME': 'django_rpc',
    'RESULT_BACKEND': 'redis://localhost/'
}

# маршрутизация средствами Django
settings.DATABASE_ROUTERS = ['django_rpc.routers.RpcRouter']


# явно видно что модель RPC
class ClientModel(RpcModel):
    class Rpc:
        # по app_label и name можно получить модель на RPC-сервере
        app_label = 'rpc_server'
        name = 'ServerModel'
        # при использовании нескольких rpc-клиентов для каждой модели можно
        # указать к какому она относится
        database = 'rpc'
        # rest_framework-style список полей, возвращаемых сервером по-умолчанию
        # None - список определенных клиентом полей, остальное явно передается
        # сериалайзеру на сервере
        fields = None

    # определяются только необходимые поля
    some_field = models.CharField(max_length=32)
    other_field = models.IntegerField(default=0)

# QuerySet по-умолчанию записывает свои трансформации и в конце отправляет
# запрос на rpc-сервер, синхронно получает результат.
ClientModel.objects.filter(some_field='123').exclude(other_field=1).get()

# QuerySet переходит в асинхронный режим, где celery.task delay() и get()
# выполняются раздельно (поддержка конвейера rpc-запросов)


qs = ClientModel.objects.future().filter(some_field='123')
# QuerySet мутировал в отложенный
f1 = qs.submit()
# Запрос отправлен на сервер

# ... other code here

# Получаем результат из ResultBackend, по-сути это аналог fill_cache
result = f1.result(timeout=10)

# итерируемся по исполненному QuerySet, выполняем bool(qs) etc...
items = list(result)

# "Финальные" методы тоже могут возвращать future - объекты
f2 = ClientModel.objects.filter(some_field='123').future().first()

item = f2.result()

# отправка запросов пачками

result1, result2 = connections['rpc'].cursor().gather(f1, f2)

# h2. Delayed

# В celery_rpc есть поддержка pipe, когда результат выполнения одной rpc-команды
# передается на вход другой - явное конструирование графа вычислений.

# Вдохновляясь dask.delayed (ленивые вычисления), хочется научиться сделать
# аналог pipe путем передачи нужных аргументов.

d = ClientModel.objects.filter(some_field='123').values('pk').delayed()
# пока это delayed-объект, более-менее аналогичный future.

ids = d.compute()
# можно явно его вычислить.

other_items = ClientModel.objects.filter(pk__in=d)
# А можно передать в качестве аргумента, в результате чего на сервере должно
# выполниться следующее:
ClientModel.objects.filter(
    pk__in=ClientModel.objects.filter(some_field='123').values('pk'))

# Желательно с автоматической конвертацией в delayed.

result = ClientModel.objects.call('manager_function', 1, 2, a=3, b=4)
# У менеджера модели можно вызывать отдельные методы. Сферический RPC в вакууме
# разрешать не хочется в целях безопасности.

# Логирование
# Информация о клиенте (хост, процесс, время вызова)
# Wrap remote errors
# Строгий режим - список разрешенных моделей для работы
# Авторизация и права доступа
# API для PHP


# Всё то же самое но без Django.
