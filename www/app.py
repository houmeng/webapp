#!/usr/bin/env python
# -*- coding:utf-8 -*-


import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, time, json, jinja2
import orm

from jinja2 import Environment, FileSystemLoader
from framework import *
from middlewares import *
from datetime import datetime

from aiohttp import web

#响应/的请求
def index0(request):
    return web.Response(body="<h1>你好</h1>".encode("utf-8"),\
                        headers={"Content-Type": "text/html;charset=utf-8"})

def init_jinja2(app, **kw):
    logging.info("init jinja2...")
    options = dict(
        autoescape = kw.get("autoescapt", True),
        block_start_string = kw.get("block_start_string", "{%"),
        block_end_string = kw.get("block_end_string", "%}"),
        variable_start_string = kw.get("variable_start_string", "{{"),
        variable_end_string = kw.get("variable_end_string", "}}"),
        auto_reload = kw.get("auto_reload", True)
    )
    path = kw.get("path", None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    logging.info("set jinja2 template path: %s" % path)

    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get("filters", None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app["__templating__"] = env

def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u"1分钟前"
    if delta < 3600:
        return u"%s分钟前" % (delta // 60)
    if delta < 86400:
        return u"%s小时前" % (delta // 3600)
    if delta < 604800:
        return u"%s天前" % (delta // 86400)

    dt = datetime.fromtimestamp(t)
    return u"%s年%s月%s日" % (dt.year, dt.month, dt.day)

@asyncio.coroutine
def init(loop):
    server_addr = "127.0.0.1"
    server_port = 9000
    sql_port = 3306
    yield from orm.create_db_pool(loop=loop, host=server_addr, port=sql_port,
                               user="root", password="root", db="webapp")
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, response_factory
    ])

    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_static(app)
    add_routes(app, "handlers")
#    app.router.add_route("GET", "/a/", index0)
    srv = yield from loop.create_server(app.make_handler(), server_addr, server_port)
    logging.info("server started at http://%s:%d..." % (server_addr, server_port))
    return srv

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()
