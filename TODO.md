TODO
====

QuerySet
--------

- [ ] Полное покрытие QuerySet API
- [x] Декораторы для финальных методов QuerySet API (возвращающих объекты)
- [ ] get_set etc... - расширение функционала QuerySet
- [ ] Future
- [ ] Delayed

Celery
------
- [x] Сериализация db-представимых объектов на уровне Celery (datetime etc...)
- [x] Поддержка Q-объектов
- [ ] Транспорт исключений (wrap remote errors)
- [ ] Рефереры, логи, авторизация

Django
------
- [x] Методы модели save, delete.
- [ ] Кэширование сериалайзеров
- [ ] Переопределение сериалайзера для запроса
- [ ] Поддержка своих кастомных методов
- [ ] rpc call

Тесты
-----
- [ ] Сигнатуры celery для NativeClient
- [ ] Сигнатуры celery для DjangoClient
- [ ] Тесты задач на серверной стороне
- [x] Тесты QuerySet API для NativeClient
- [x] Тесты QuerySet API для DjangoClient
- [x] Тесты RPCModel для выключенного RPC
- [x] Тесты с запущенной Celery.
- [ ] Покрытие всех поддерживаемых типов полей Django.

Интеграционное
--------------

- [ ] requirements.txt
- [ ] setup.py
- [ ] travis-ci.org
- [ ] readthedocs.org
- [ ] codecov.io
- [ ] pypi.org
- [ ] сетка тестов Py2.7-3.6 / Dj1.8-1.11 / RestFramework 3.x-3.6

FIXME
-----

* Десериализация списка datetime для вызова queryset.datetimes. Сложностей с 
JSONDecoder много, толку - мало. Требуется перенос на уровень итераторов.
* Использование сериалайзеров на клиентской стороне - возможно, это просто не 
нужно, NativeModel как-то обходится пока что.
