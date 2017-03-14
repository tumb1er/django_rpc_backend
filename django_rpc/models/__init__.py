# coding: utf-8

try:
    from .django import *
except Exception as e:
    pass

from .base import RpcModel
from .query import RpcQuerySet
from .manager import RpcManager

__all__ = ['RpcModel', 'RpcManager', 'RpcQuerySet'] + django.__all__
