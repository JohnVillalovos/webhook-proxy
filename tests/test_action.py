from __future__ import print_function

import os
import unittest

import docker_helper
from unittest_helper import ActionTestBase, capture_stream

from actions import Action, action
from server import ConfigurationException


class ActionTest(ActionTestBase):
    def test_simple_log(self):
        actions = [{"log": {"message": "Hello there!"}}]
        output = self._invoke(actions)

        self.assertEqual(output, "Hello there!")

    def test_log_with_variable(self):
        actions = [{"log": {"message": "HTTP {{ request.method }} {{ request.path }}"}}]

        output = self._invoke(actions)

        self.assertEqual(output, "HTTP POST /testing")

    def test_evaluate(self):
        actions = [
            {
                "execute": {
                    "command": 'echo -n "Hello"',
                    "output": '{% set _ = context.set("message", result) %}',
                }
            },
            {"eval": {"block": "Hello=={{ context.message }}"}},
        ]

        output = self._invoke(actions)

        self.assertEqual(output, "Hello==Hello")

    def test_custom_action(self):
        @action("for-test")
        class TestAction(Action):
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def _run(self):
                print(*("%s=%s" % (key, value) for key, value in self.kwargs.items()))

        actions = [{"for-test": {"string": "Hello", "number": 12, "bool": True}}]

        output = self._invoke(actions)

        self.assertIn("string=Hello", output.split())
        self.assertIn("number=12", output.split())
        self.assertIn("bool=True", output.split())

    def test_raising_error(self):
        actions = [
            {
                "log": {
                    "message": "{% if request.json.fail %}\n"
                    '  {{ error("Failing with : %s"|format(request.json.fail)) }}\n'
                    "{% else %}\n"
                    "  All good\n"
                    "{% endif %}"
                }
            }
        ]

        output = self._invoke(actions)

        self.assertIn("All good", output)

        with capture_stream("stderr", echo=True) as output:
            self._invoke(
                actions, expected_status_code=500, body={"fail": "test-failure"}
            )

            output = output.dumps()

        self.assertIn("Failing with : test-failure", output)

    @unittest.skipUnless(
        os.path.exists("/proc/1/cgroup"), "Test is not running in a container"
    )
    def test_log_with_docker_helper(self):
        actions = [
            {
                "log": {
                    "message": "Running in {{ own_container_id }} "
                    'with environment: {{ read_config("TESTING_ENV") }}'
                }
            }
        ]

        os.environ["TESTING_ENV"] = "webhook-proxy-testing"

        output = self._invoke(actions)

        expected = (
            "Running in %s with environment: webhook-proxy-testing"
            % docker_helper.get_current_container_id()
        )

        self.assertEqual(output, expected)

    def test_invalid_action(self):
        actions = [{"invalid": {"Should": "not work"}}]

        self.assertRaises(ConfigurationException, self._invoke, actions)

    def test_wrong_configuration(self):
        actions = [{"log": {"unknown_argument": 1}}]

        self.assertRaises(ConfigurationException, self._invoke, actions)
