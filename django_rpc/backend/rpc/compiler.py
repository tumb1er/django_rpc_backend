# coding: utf-8

from django.db.models.sql import compiler
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import MULTI, CURSOR
from rest_framework import serializers

from django_rpc.celery.client import RpcClient
from django_rpc.models.query import Trace

SINGLE_MODEL_UPDATE_SUPPORTED = "single model save only supported"
SINGLE_MODEL_DELETE_SUPPORTED = "single model delete only supported"


class RpcCursorStub(object):
    def __init__(self, rowcount=None):
        self.rowcount = rowcount


class RpcSQLCompiler(SQLCompiler):

    def __init__(self, query, connection, using):
        super(RpcSQLCompiler, self).__init__(query, connection, using)
        self.client = RpcClient.from_db(using)

    def execute_sql(self, result_type=MULTI, chunked_fetch=False):
        self.setup_query()
        # noinspection PyProtectedMember
        rpc = self.query.model.Rpc
        # noinspection PyProtectedMember
        opts = self.query.model._meta
        kwargs = {}
        lazy, defer = self.query.deferred_loading
        if lazy and not defer:  # only
            kwargs['fields'] = list(lazy | {rpc.pk.attname})
        elif lazy:  # defer
            all_fields = {f.attname for f in opts.get_fields()}
            kwargs['fields'] = list(set(all_fields) - lazy)
        results = self.client.fetch(
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

    # noinspection PyMethodOverriding
    def execute_sql(self, return_id=False):
        rpc = self.query.model.Rpc
        rpc_fields = [f.name for f in self.query.fields]

        class Serializer(serializers.ModelSerializer):
            class Meta:
                model = self.query.model
                fields = rpc_fields

        s = Serializer(many=True, instance=self.query.objs)
        rpc_data = s.data

        results = self.client.insert(
            rpc.app_label,
            rpc.name,
            rpc_data,
            return_id=return_id)
        return results


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, RpcSQLCompiler):

    # noinspection PyMethodOverriding
    def execute_sql(self, return_id=False):
        rpc = self.query.model.Rpc
        where = self.query.where
        assert len(where.children) == 1, SINGLE_MODEL_UPDATE_SUPPORTED
        lookup = where.children[0]
        assert lookup.lookup_name == 'exact', SINGLE_MODEL_UPDATE_SUPPORTED
        col, pk = lookup.lhs, lookup.rhs
        assert col.field.primary_key, SINGLE_MODEL_UPDATE_SUPPORTED

        values = {f.attname: v for f, _, v in self.query.values}

        trace = (Trace('filter', (), {'pk': pk}),)

        results = self.client.update(
            rpc.app_label,
            rpc.name,
            trace,
            values,
            single=True)
        return results


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, RpcSQLCompiler):

    # noinspection PyMethodOverriding
    def execute_sql(self, result_type=CURSOR):
        rpc = self.query.model.Rpc
        where = self.query.where
        assert len(where.children) == 1, SINGLE_MODEL_DELETE_SUPPORTED
        lookup = where.children[0]
        assert lookup.lookup_name == 'in', SINGLE_MODEL_DELETE_SUPPORTED
        col, pks = lookup.lhs, lookup.rhs
        assert col.field.primary_key, SINGLE_MODEL_DELETE_SUPPORTED
        assert isinstance(pks, list), SINGLE_MODEL_DELETE_SUPPORTED
        trace = (Trace('filter', (), {'pk__in': pks}),)

        results = self.client.delete(
            rpc.app_label,
            rpc.name,
            trace)
        if result_type == CURSOR:
            return RpcCursorStub(rowcount=results[0])
        return results
