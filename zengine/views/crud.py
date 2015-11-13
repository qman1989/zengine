# -*-  coding: utf-8 -*-
"""Base view classes"""
# -
# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.
import datetime
import falcon
from falcon import HTTPNotFound
import six
from pyoko import form
from pyoko.conf import settings
from pyoko.model import Model, model_registry
from zengine.auth.permissions import NO_PERM_TASKS_TYPES
from zengine.lib.forms import JsonForm
from zengine.log import log
from zengine.views.base import BaseView

# GENERIC_COMMANDS = ['edit', 'add', 'update', 'list', 'delete', 'do', 'show', 'save']


# class CRUDRegistry(type):
#     registry = {}
#
#     def __init__(mcs, name, bases, attrs):
#         CRUDRegistry.registry[mcs.__name__] = mcs
#
#     @classmethod
#     def _get_permission_names(cls):
#         perms = []
#         for kls_name, kls in cls.registry.items():
#             for method_name in cls.__dict__.keys():
#                 if method_name.endswith('_view'):
#                     perms.append("%s.%s" % (kls_name, method_name))
#         return perms

class CrudForm(JsonForm):
    save_list = form.Button("Kaydet ve Listele", cmd="save::list")
    save_edit = form.Button("Kaydet ve Devam Et", cmd="save::edit")


# @six.add_metaclass(CRUDRegistry)
class CrudView(BaseView):
    """
    A base class for "Create List Show Update Delete" type of views.



    :type object: Model | None
    """
    def __init__(self, current=None):
        super(CrudView, self).__init__(current)
        if current:
            self.__call__(current)

    MODEL = None



    def __call__(self, current):
        current.log.info("CRUD CALL")
        self.current = current
        self.set_current(current)
        self.create_object()
        self.create_form()
        if not self.cmd:
            self.cmd = 'list'
            current.task_data['cmd'] = self.cmd
        self.check_for_permission()
        current.log.info('Calling %s_view of %s' % ((self.cmd or 'list'),
                                                    self.object.__class__.__name__))
        getattr(self, '%s_view' % self.cmd)()
        if self.next_cmd:
            self.current.task_data['cmd'] = self.next_cmd

    def check_for_permission(self):
        permission = "%s.%s" % (self.object.__class__.__name__, self.cmd)
        log.debug("CHECK CRUD PERM: %s" % permission)
        if (self.current.task_type in NO_PERM_TASKS_TYPES or
                    permission in settings.ANONYMOUS_WORKFLOWS):
            return
        if not self.current.has_permission(permission):
            raise falcon.HTTPForbidden("Permission denied",
                                       "You don't have required model permission: %s" % permission)

    def create_form(self):
        self.form = CrudForm(self.object, current=self.current)

    def get_model_class(self):
        model = self.MODEL if self.MODEL else self.current.input['model']
        if isinstance(model, Model):
            return model
        else:
            return model_registry.get_model(model)

    def create_object(self):
        model_class = self.get_model_class()
        object_id = self.input.get('object_id')  # or self.current.task_data.get('object_id')
        if object_id:
            try:
                self.object = model_class(self.current).objects.get(object_id)
                if self.object.deleted:
                    raise HTTPNotFound()
            except:
                raise HTTPNotFound()
        else:
            self.object = model_class(self.current)

    # def list_models(self):
    #     self.output["models"] = [(m.Meta.verbose_name_plural, m.__name__)
    #                              for m in model_registry.get_base_models()]
    #
    #     self.output["app_models"] = [(app, [(m.Meta.verbose_name_plural, m.__name__)
    #                                         for m in models])
    #                                  for app, models in model_registry.get_models_by_apps()]

    def show_view(self):
        self.output['object'] = self.form.serialize()['model']
        self.output['object']['key'] = self.object.key
        self.output['client_cmd'] = 'show_object'

    def _get_list_obj(self, mdl):
        if self.brief:
            return [mdl.key, unicode(mdl) if six.PY2 else mdl]
        else:
            result = [mdl.key]
            for f in self.object.Meta.list_fields:
                field = getattr(mdl, f)
                if callable(field):
                    result.append(field())
                elif isinstance(field, (datetime.date, datetime.datetime)):
                    result.append(mdl._fields[f].clean_value(field))
                else:
                    result.append(field)
            return result

    def _make_list_header(self):
        if not self.brief:  # add list headers
            list_headers = []
            for f in self.object.Meta.list_fields:
                if callable(getattr(self.object, f)):
                    list_headers.append(getattr(self.object, f).title)
                else:
                    list_headers.append(self.object._fields[f].title)
            self.output['nobjects'].append(list_headers)
        else:
            self.output['nobjects'].append('-1')

    def _process_list_filters(self, query):
        if self.current.request.params:
            return query.filter(**self.current.request.params)
        if 'filters' in self.input:
            return query.filter(**self.input['filters'])
        return query

    def _process_list_search(self, query):
        if 'query' in self.input:
            query_string = self.input['query']
            search_string = ' OR '.join(
                ['%s:*%s*' % (f, query_string) for f in self.object.Meta.list_fields])
            return query.raw(search_string)
        return query

    def list_view(self):
        # TODO: add pagination
        self.brief = 'brief' in self.input or not self.object.Meta.list_fields
        query = self.object.objects.filter()
        query = self._process_list_filters(query)
        query = self._process_list_search(query)
        self.output['client_cmd'] = 'list_objects'
        self.output['nobjects'] = []
        self._make_list_header()
        for obj in query:
            if self._just_deleted_object(obj):
                continue
            self.output['nobjects'].append(self._get_list_obj(obj))
        self._just_created_object(self.output['nobjects'])

    def _just_deleted_object(self, obj):
        # compensate riak~solr sync delay
        if ('deleted_obj' in self.current.task_data and
                    self.current.task_data['deleted_obj'] == obj.key):
            del self.current.task_data['deleted_obj']
            return True

    def _just_created_object(self, objects):
        # compensate riak~solr sync delay
        if 'added_obj' in self.current.task_data:
            key = self.current.task_data['added_obj']
            if not any([o[0] == key for o in objects]):
                obj = self.object.objects.get(key)
                self.output['nobjects'].insert(1, self._get_list_obj(obj))
                del self.current.task_data['added_obj']

    def edit_view(self):
        self.output['forms'] = self.form.serialize()
        self.output['client_cmd'] = 'edit_object'

    def add_view(self):
        self.output['forms'] = self.form.serialize()
        self.output['client_cmd'] = 'add_object'

    def save_view(self):
        self.object = self.form.deserialize(self.current.input['form'])
        obj_is_new = self.object.is_in_db()
        self.object.save()
        if self.next_cmd and obj_is_new:
            self.current.task_data['added_obj'] = self.object.key
            # self.current.task_data['object_id'] = self.object.key

    def delete_view(self):
        # TODO: add confirmation dialog
        if self.subcmd:  # to overcome 1s riak-solr delay
            self.current.task_data['deleted_obj'] = self.object.key
        self.object.delete()
        del self.current.input['object_id']
        # del self.current.task_data['object_id']
