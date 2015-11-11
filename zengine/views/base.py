# -*-  coding: utf-8 -*-
"""Base view classes"""


# -
# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.

NEXT_CMD_SPLITTER = '::'

class BaseView(object):
    """
    this class constitute a base for all view classes.
    """

    def __init__(self, current=None):
        if current:
            self.set_current(current)

    def set_current(self, current):
        self.current = current
        self.input = current.input
        self.output = current.output
        if current.input.get('cmd'):
            self.cmd = current.input.get('cmd')
            del current.input['cmd']
        else:
            if hasattr(current, 'task_data'):
                self.cmd = current.task_data.get('cmd')
            else:
                self.cmd = None
        if self.cmd and NEXT_CMD_SPLITTER in self.cmd:
            self.cmd, self.next_cmd = self.cmd.split(NEXT_CMD_SPLITTER)
        else:
            self.next_cmd = None


class SimpleView(BaseView):
    """
    simple form based views can be build  up on this class.
    we call self.%s_view() method with %s substituted with self.input['cmd']
    self.show_view() will be called if client doesn't give any cmd
    """
    DEFAULT_VIEW = ''
    def __init__(self, current):
        super(SimpleView, self).__init__(current)
        view = "%s_view" % (self.cmd or self.DEFAULT_VIEW or 'show')
        if view in self.__class__.__dict__:
            self.__class__.__dict__[view](self)
