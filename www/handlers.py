#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
url handlers.
'''

__author__ = "Meng Hou"

from framework import *
import asyncio
from models import User,Blog

@get("/")
def index(request):
    summary = "this is for test"
    blogs = [
        Blog(id="1", name="Test Blog", summary=summary, created_at=time.time() - 120),
        Blog(id="2", name="Test Blog2", summary=summary, created_at=time.time() - 3600),
        Blog(id="3", name="Test Blog3", summary=summary, created_at=time.time() - 7200),
    ]

    return {
        "__template__": "blogs.html",
        "blogs": blogs
    }
