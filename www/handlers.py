#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
url handlers.
'''

__author__ = "Meng Hou"

from framework import get,post
import asyncio, re, time, logging
from models import User,Blog
from config import configs

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

@get("/api/users0")
def api_get_users():
    users = yield from User.findall(orderBy="created_at desc")
    for u in users:
        u.passwd = "******"
    return dict(users=users)

_RE_EMAIL = re.compile(r"^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$")
_RE_SHA1 = re.compile(r"^[0-9a-f]{40}$")
COOKIE_NAME = "webappsession"
_COOKIE_KEY = configs.session.secret

@post("/api/users")
def api_register_user(*, email, name, passwd):
    logging.info("register info:%s, %s" % (name, email))
    if not name or not name.strip():
        raise APIValueError("name")
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError("email")
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError("passwd")
    users = yield from User.findall("email=?", [email])
    if len(users) > 0:
        raise APIError("register:failed", "email", "Email already in use.")
    uid = next_id()
    sha1_passwd = "%s:%s" % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode("utf-8")).hexdigest(), image="http://www.gravatar.com/avatar/%s?d=mm&s=120" % hashlib.md5(email.encode("utf-8")).hexdigest())
    yield from user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = "******"
    r.content_type = "application/json"
    r.body = json.dumps(user, ensure_ascii=False).encode("utf-8")
    return r

@get("/register")
def register():
    return {
        "__template__": "register.html"
    }

@post("/api/authenticate")
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError("email", "Invalid email.")
    if not passwd:
        raise APIValueError("passwd", "Invalid password.")
    users = yield from User.findall("email=?", [email])
    if len(users) == 0:
        raise APIValueError("email", "Email not exist.")
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode("utf-8"))
    sha1.update(b":")
    sha1.update(passwd.encode("utf-8"))
    if user.passwd != sha1.hexdigest():
        raise APIValueError("passwd", "Invalid password.")
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = "******"
    r.content_type = "application/json"
    r.body = json.dumps(user, ensure_ascii=False).encode("utf-8")
    return r

def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    s = "%s-%s-%s-%s" % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode("utf-8")).hexgiest()]
    return "-".join(L)

@asyncio.coroutine
def cookie2user(cookie_str):
    """
    Parse cookie and load user if cookie is valid.
    """
    if not cookie_str:
        return None
    try:
        L = cookie_str.split("-")
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = "%s-%s-%s-%s" % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode("utf-8")).hexgiest():
            logging.info("invalid sha1")
            return None
        user.passwd = "******"
        return user
    except Exception as e:
        logging.exception(e)
        return None
