from __future__ import print_function

import os
import time
import traceback

from flask import request
from jinja2 import Template

from util import ActionInvocationException, ConfigurationException


def _safe_import():
    class SafeImportContext(object):
        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is ImportError:
                error_file = traceback.extract_tb(exc_tb)[1][0]
                name, _ = os.path.splitext(os.path.basename(error_file))

                if name.startswith('action_'):
                    name = name[len('action_'):].replace('_', '-')

                print('The "%s" action is not available' % name)

                return True

    return SafeImportContext()


def _register_available_actions():
    from action_log import LogAction
    from action_execute import ExecuteAction

    with _safe_import():
        from action_http import HttpAction
    with _safe_import():
        from action_docker import DockerAction
    with _safe_import():
        from action_docker_compose import DockerComposeAction


class Action(object):
    _registered_actions = dict()

    def run(self):
        try:
            return self._run()

        except Exception as ex:
            raise ActionInvocationException('Failed to invoke %s.run:\n'
                                            '  Reason (%s): %s' %
                                            (type(self).__name__, type(ex).__name__, ex))

    def _run(self):
        raise ActionInvocationException('%s.run not implemented' % type(self).__name__)

    @staticmethod
    def _render_with_template(template, **kwargs):
        template = Template(template)
        return template.render(request=request, timestamp=time.time(), datetime=time.ctime(), **kwargs)

    @classmethod
    def register(cls, name, action_type):
        cls._registered_actions[name] = action_type

    @classmethod
    def create(cls, name, **settings):
        if name not in cls._registered_actions:
            raise ConfigurationException('Unkown action: %s (registered: %s)' %
                                         (name, cls._registered_actions.keys()))

        try:
            return cls._registered_actions[name](**settings)

        except Exception as ex:
            raise ConfigurationException('Failed to create action: %s (settings = %s)\n'
                                         '  Reason (%s): %s' %
                                         (name, settings, type(ex).__name__, ex))


def action(name):
    def invoke(cls):
        cls.action_name = name

        Action.register(name, cls)

        return cls

    return invoke


_register_available_actions()
