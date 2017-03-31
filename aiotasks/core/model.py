# -*- coding: utf-8 -*-

from booby import *


class SharedConfig(Model):
    verbosity = Integer(default=0)
    timeout = Integer(default=10)
    debug = Boolean(default=False)
