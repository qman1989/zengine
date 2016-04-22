# -*-  coding: utf-8 -*-
"""
"""

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.
from pyoko import Model, field, ListNode
from pyoko.conf import settings
from pyoko.lib.utils import get_object_from_path

UserModel = get_object_from_path(settings.USER_MODEL)

NOTIFY_MSG_TYPES = (
    (1, "Info"), (11, "Error"), (111, "Success"), (2, "User Message"), (3, "Broadcast Message")
)



class NotificationMessage(Model):
    """
    Permission model
    """

    typ = field.Integer("Message Type", choices=NOTIFY_MSG_TYPES)
    msg_title = field.String("Title")
    body = field.String("Body")
    url = field.String("URL")
    sender = UserModel(reverse_name='sent_messages')
    receiver = UserModel(reverse_name='received_messages')

    def __unicode__(self):
        return "Msg %s" % self.title
