#!/usr/bin/env python
# -*- coding:utf-8 -*-


import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, time, json
from datetime import datetime

from aiohttp import web

#响应/的请求
def index(request):
    return web.Response(body="<h1>你好</h1>".encode("utf-8"),\
                        headers={"Content-Type": "text/html;charset=utf-8"})

@asyncio.coroutine
def init(loop):
    server_addr = "127.0.0.1"
    server_port = 9000
    app = web.Application(loop=loop)
    app.router.add_route("GET", "/", index)
    srv = yield from loop.create_server(app.make_handler(), server_addr, server_port)
    logging.info("server started at http://%s:%d..." % (server_addr, server_port))
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
