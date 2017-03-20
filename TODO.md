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
- [ ] Сериализация db-представимых объектов на уровне Celery (datetime etc...)
- [ ] Поддержка Q-объектов
- [ ] Транспорт исключений (wrap remote errors)
- [ ] Рефереры, логи, авторизация

Django
------
- [ ] Методы модели save, delete.
- [ ] Кэширование сериалайзеров
- [ ] Переопределение сериалайзера для запроса
- [ ] rpc call

Тесты
-----
- [ ] Сигнатуры celery для NativeClient
- [ ] Сигнатуры celery для DjangoClient
- [ ] Тесты задач на серверной стороне
- [ ] Тесты QuerySet API для NativeClient
- [ ] Тесты QuerySet API для DjangoClient
- [ ] Тесты RPCModel для выключенного RPC
- [ ] Тесты с запущенной Celery.
