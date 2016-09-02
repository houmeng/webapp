#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
url handlers.
'''

__author__ = "Meng Hou"

from framework import *
import asyncio
from models import User

@get("/")
def index(request):
    users = yield from User.findall()

    return {
        "__template__": "test.html",
        "users": users
    }
