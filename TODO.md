TODO
====

QuerySet
--------

- [ ] Полное покрытие QuerySet API
- [ ] Декораторы для финальных методов QuerySet API (возвращающих объекты)
- [ ] get_set, create_or_update и подобное расширение функционала QuerySet
- [ ] Future
- [ ] Delayed

Celery
------
- [ ] Сериализация db-представимых объектов на уровне Celery (datetime etc...)
- [ ] Поддержка Q-объектов
- [ ] Транспорт исключений (wrap remote errors)
- [ ] Рефереры, логи, авторизация

Тесты
-----
- [ ] Сигнатуры celery для NativeClient
- [ ] Сигнатуры celery для DjangoClient
- [ ] Тесты задач на серверной стороне
- [ ] Тесты QuerySet API для NativeClient
- [ ] Тесты QuerySet API для DjangoClient
- [ ] Тесты RPCModel для выключенного RPC
