# coding: utf-8

from copy import copy
from django.conf import settings
from django.db.models.sql import compiler
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import MULTI
from rest_framework import serializers

from django_rpc.celery.client import RpcClient


class RpcSQLCompiler(SQLCompiler):

    def __init__(self, query, connection, using):
        super(RpcSQLCompiler, self).__init__(query, connection, using)
        self.client = RpcClient.from_db(using)

    def execute_sql(self, result_type=MULTI):
        self.setup_query()
        # noinspection PyProtectedMember
        rpc = self.query.model.Rpc
        kwargs = {}
        lazy, defer = self.query.deferred_loading
        if lazy and not defer:  # only
            kwargs['fields'] = list(lazy | {rpc.pk.attname})
        elif lazy:  # defer
            all = {f.attname for f in self.query.model._meta.get_fields()}
            kwargs['fields'] = list(set(all) - lazy)
        results = self.client.execute(
            rpc.app_label,
            rpc.name,
            self.query.rpc_trace,
            **kwargs)
        return [results] if result_type == MULTI else results

    def results_iter(self, results=None):
        # noinspection PyProtectedMember
        opts = self.query.model._meta

        fields = [s[0] for s in self.select[0:self.col_count]]
        init_list = [f.target.attname for f in fields]
        # if self.query.serializer_fields != '__all__':
        #     init_list = self.query.serializer_fields

        class Serializer(serializers.ModelSerializer):
            class Meta:
                model = self.query.model
                fields = init_list

        s = Serializer(many=True)
        s.child.fields[opts.pk.attname].read_only = False
        for row in s.to_internal_value(results[0]):
            yield [row[f] for f in init_list]


SQLCompiler = RpcSQLCompiler


class SQLInsertCompiler(compiler.SQLInsertCompiler, RpcSQLCompiler):
    def execute_sql(self, return_id=False):
        # noinspection PyProtectedMember
        opts = self.query.model._meta
        results = self.client.fetch.delay(
            opts.rpc_module,
            opts.rpc_name,
            self.query.queryset_trace).get()
