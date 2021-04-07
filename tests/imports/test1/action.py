from __future__ import print_function

from actions import Action, action


@action("test1")
class CustomAction(Action):
    def __init__(self, **kwargs):
        self.params = kwargs

    def _run(self):
        print("\n".join("%s=%s" % (key, value) for key, value in self.params.items()))
