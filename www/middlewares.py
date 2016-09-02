#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
Define middleware functions.
'''

__author__ = "Meng Hou"

import asyncio,logging
from aiohttp import web

@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        logging.info("Request: %s %s" % (request.method, request.path))
        return (yield from handler(request))
    return logger

@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info("response_factory process.")
        r = yield from handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = "application/octet-stream"
            return resp
        if isinstance(r, str):
            if r.startswith("redirect:"):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode("utf-8"))
            resp.content_type = "text/html;charset=utf-8"
            return resp
        if isinstance(r, dict):
            template = r.get("__template__")
            if template is None:
                resp = web.Response(body=join.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode("utf-8"))
                resp.content_type = "application/json;charset=utf-8"
                return resp
            else:
                resp = web.Response(body=app["__templating__"].get_template(template).render(**r).encode("utf-8"))
                resp.content_type = "text/html;charset=utf-8"
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))

        resp = web.Response(body=str(r).encode("utf-8"))
        resp.content_type = "text/plain;charset=utf-8"
        return resp

    return response
