# -*-  coding: utf-8 -*-
"""
"""


# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.
from riak.client import binary_json_decoder
from riak.util import bytes_to_str
from six import text_type

from zengine.lib.cache import ClearCache


class Ping(object):
    """
    Simple ping view for health checks
    """

    def __init__(self, current):
        """
        GET method handler
        Args:
            req: Request object.
            resp: Response object.
        """

        current.output = {
            'response': 'OK',
            'http_headers': (('Content-Type', 'text/plain'),),
        }


class DBStats(object):
    """
    various stats
    """

    def __init__(self, current):
        import sys
        """
        GET method handler
        Args:
            req: Request object.
            resp: Response object.
        """

        read_existing = set(sys.PYOKO_LOGS['read']) - set(sys.PYOKO_LOGS['new'])

        current.output = {
            'response': "DB Access Stats: {}".format(str(sys.PYOKO_STAT_COUNTER),
                                                     str(read_existing)),
            'http_headers': (('Content-Type', 'text/plain'),),
        }

        sys.PYOKO_LOGS = {
            "save": 0,
            "update": 0,
            "read": 0,
            "count": 0,
            "search": 0,
        }


class SessionFixture(object):
    """
    Export read keys
    """

    def __init__(self, current):
        import sys
        from pyoko.modelmeta import model_registry
        """
        GET method handler
        Args:
            req: Request object.
            resp: Response object.
        """
        out = []
        for mdl_name in sys.PYOKO_LOGS.copy():
            try:
                mdl = model_registry.get_model(mdl_name)
            except KeyError:
                continue
            bucket_name = mdl.objects.bucket.name
            mdl.objects.bucket.set_decoder('application/json', lambda a: bytes_to_str(a))
            for k in set(sys.PYOKO_LOGS[mdl_name]):
                if k not in sys.PYOKO_LOGS['new']:
                    out.append("{}/|{}/|{}".format(
                        bucket_name, k, mdl.objects.data().get(k)[0]))
                    # print(str(mdl.objects.get(k).name))
            sys.PYOKO_LOGS[mdl_name] = []
            mdl.objects.bucket.set_decoder('application/json', binary_json_decoder)
        sys.PYOKO_LOGS['new'] = []
        current.output = {
            'response': "\n".join(out),
            'http_headers': (('Content-Type', 'text/plain; charset=utf-8'),
                             ),
        }


class ResetCache(object):
    """
    Clears all cache entries
    """

    def __init__(self, current):
        """
        GET method handler
        Args:
            req: Request object.
            resp: Response object.
        """
        current.output = {
            'response': "Following cache entries are removed!\n\n" + text_type("\n").join(ClearCache().flush()),
            'http_headers': (('Content-Type', 'text/plain'),),
        }
