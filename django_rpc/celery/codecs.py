import datetime
import decimal
import json
import re
import uuid

import jsonpickle
import pytz
import six
from kombu.utils.encoding import bytes_t

try:
    # Django support
    from django.utils.functional import Promise
    from django.utils.encoding import smart_str
    from django.db.models import Q, Aggregate

    has_django = True
except ImportError:
    has_django = False
    smart_str = Promise = Q = Aggregate = None


class RpcJsonEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time/timedelta,
    decimal types, Q-objects and generators.

    Originated from
    https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/utils/encoders.py

    """

    # noinspection PyArgumentList
    def _default(self, o):
        # For Date Time string spec, see ECMA 262
        # http://ecma-international.org/ecma-262/5.1/#sec-15.9.1.15
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, datetime.timedelta):
            return str(o.total_seconds())
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, uuid.UUID):
            return o.hex
        elif hasattr(o, 'tolist'):
            return o.tolist()
        elif hasattr(o, '__iter__'):
            return [i for i in o]
        return super(RpcJsonEncoder, self).default(o)

    if has_django:
        # Handling django-specific classes only if django package is installed
        def default(self, o):
            if isinstance(o, Promise):
                return smart_str(o)
            elif isinstance(o, Q):
                return {'_': jsonpickle.encode(o)}
            elif isinstance(o, Aggregate):
                return {'_': jsonpickle.encode(o)}
            else:
                return self._default(o)
    else:
        default = _default


class RpcJsonDecoder(json.JSONDecoder):
    """ Add support for Django Q-objects in dicts
    """
    Q_OBJECT_SIGNATURE = re.compile(
        r'"py/object": "django\.db\.models\.query_utils\.Q"')

    DT_SIGNATURE = re.compile(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z')

    D_SIGNATURE = re.compile(
        r'\d{4}-\d{2}-\d{2}')

    AGGREGATE_SIGNATURE = re.compile(
        r'"py/object": "django\.db\.models\.aggregates\.'
        r'(Aggregate|Avg|Count|Max|Min|StdDev|Sum|Variance)"')

    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = self._object_hook
        super(RpcJsonDecoder, self).__init__(*args, **kwargs)

    def _object_hook(self, val):
        """ Iterate through dict for additional conversion.
        """
        if tuple(val.keys()) == ('_',):
            return self._parse_type(val['_'])
        for k, v in six.iteritems(val):
            new = self._parse_type(v)
            if new is NotImplemented:
                continue
            val[k] = new
        return val

    def _parse_type(self, v):
        if not isinstance(v, six.string_types):
            return NotImplemented
        if re.search(self.Q_OBJECT_SIGNATURE, v):
            return jsonpickle.decode(v)
        if re.search(self.AGGREGATE_SIGNATURE, v):
            return jsonpickle.decode(v)
        m = re.match(self.DT_SIGNATURE, v)
        if m:
            if m.group(1):
                dt = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                dt = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')
            return datetime.datetime(*dt.timetuple()[:6],
                                     microsecond=dt.microsecond,
                                     tzinfo=pytz.utc)
        m = re.match(self.D_SIGNATURE, v)
        if m:
            dt = datetime.datetime.strptime(v, '%Y-%m-%d')
            return dt.date()
        return NotImplemented


def x_rpc_json_dumps(obj):
    return json.dumps(obj, cls=RpcJsonEncoder)


def x_rpc_json_loads(s):
    if isinstance(s, bytes_t):
        s = s.decode()
    return json.loads(s, cls=RpcJsonDecoder)


def register_codecs():
    from kombu.serialization import registry
    registry.register('x-rpc-json', x_rpc_json_dumps, x_rpc_json_loads,
                      'application/json+django-rpc-backend:v1', 'utf-8')
