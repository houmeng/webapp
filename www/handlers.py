#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
url handlers.
'''

__author__ = "Meng Hou"

from framework import get,post
import asyncio, re, time, logging, hashlib, json
from models import User, Blog, Comment, next_id
from config import configs
from aiohttp import web
from apis import APIValueError, APIResourceNotFoundError, Page
import markdown2
from markdown2 import Markdown
import markdown
import os, sys

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def text2html(text):
    lines = map(lambda s: "<p>%s</p>" % s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), filter(lambda s: s.strip != "", text.split("\n")))
    return "".join(lines)

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

@get("/")
def index(*, page="1"):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber("count(id)")
    page = Page(num, page_index)

    if num == 0:
        blogs = []
    else:
        # 获取所有博客，并使用模板制作html
        blogs = yield from Blog.findall(orderBy="created_at desc", limit=(page.offset, page.limit))
    return {
        "__template__": "blogs.html",
        "blogs": blogs,
        "page": page
    }

class MarkdownEx(Markdown):
    def preprocess(self, text):
        print('in preprocess.')
#        print(text.encode('ascii'))
#        if text.encode('ascii').find(b'\n') >= 0:
 #           print('find.')
        if text.find('\n') >= 0:
            text = text.replace('\n', '<br>')
        return text

    def postprocess(self, text):
        print('in postprocess')
        return text


@get("/blog/{id}")
def get_blog(id):
    blog = yield from Blog.find(id)
    comments = yield from Comment.findall("blog_id=?", [id], orderBy="created_at desc")
    for c in comments:
        c.html_content = c.content#text2html(c.content)
    blog.html_content = blog.content#markdown.markdown(blog.content)
#    blog.html_content = MarkdownEx().convert(blog.content)
    return {
        "__template__": "blog.html",
        "blog": blog,
        "comments": comments
    }

@get("/api/users")
def api_get_users(request, *, page='1'):
    check_admin(request)
    page_index = get_page_index(page)
    num = yield from User.findNumber("count(id)")
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())

    users = yield from User.findall(orderBy="created_at desc", limit=(p.offset, p.limit))
    for u in users:
        u.passwd = "******"
    return dict(page=p, users=users)

@get("/manage/users")
def get_users(request, *, page='1'):
    check_admin(request)
    return {
        '__template__' : 'manage_users.html',
        "page_index": get_page_index(page)
    }

_RE_EMAIL = re.compile(r"^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$")
_RE_SHA1 = re.compile(r"^[0-9a-f]{40}$")
COOKIE_NAME = "webappsession"
_COOKIE_KEY = configs.session.secret

@post("/api/users")
def api_register_user(*, email, name, passwd):
    logging.info("register info:%s, %s, %s" % (name, email, passwd))
    if not name or not name.strip():
        raise APIValueError("name")
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError("email")
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError("passwd")
    users = yield from User.findall("email=?", [email])
    if users and len(users) > 0:
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

@get("/api/blogs/{id}")
def api_get_blog(*, id):
    blog = yield from Blog.find(id)

    comments = yield from Comment.findall("blog_id=?", [id], orderBy="created_at desc")
    for c in comments:
        c.html_content = c.content#text2html(c.content)
    blog.html_content = blog.content#markdown2.markdown(blog.content)
    return {
        "__template__": "blog.html",
        "blog": blog,
        "comments": comments
    }

@get("/api/blogs")
def api_blogs(*, page="1"):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber("count(id)")
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())

    blogs = yield from Blog.findall(orderBy="created_at desc", limit=(p.offset, p.limit))

    return dict(page=p, blogs=blogs)

@get("/api/blogs/{id}")
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResouceNotFoundError("Blog (%s) was not found." % str(id))

    return blog

@get("/manage/blogs")
def manage_blogs(*, page="1"):
    return {
        "__template__": "manage_blogs.html",
        "page_index": get_page_index(page)
    }

@post("/api/blogs")
def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError("name", "name cannot be empty.")
    if not summary or not summary.strip():
        raise APIValueError("summary", "summary cannot be empty.")
    if not content or not content.strip():
        raise APIValueError("cotent", "content cannot be empty.")

    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    yield from blog.save()
    return blog

@post("/api/blogs/{id}/delete")
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    if len(blog) == 0:
        raise APIValueError("id", "blog (%s) was not found." % id)
    yield from blog.remove()
    return dict(id=id)

@post("/api/blogs/{id}/comments")
def api_commit_comment(request, *, id, content):
    user = request.__user__
    if user is None:
        APIPermissionError("Please signin first.")
    if not id or not id.strip():
        raise APIValueError("id", "id cannot be empty.")
    if not content or not content.strip():
        raise APIValueError("content", "content of comment cannot be empty.")

    comment = Comment(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, blog_id=id, content=content.strip())
    yield from comment.save()
    return comment

@get("/register")
def register():
    return {
        "__template__": "register.html"
    }

@get("/signin")
def signin():
    return {
        "__template__": "signin.html"
    }
@get("/signout")
def signout(request):
    referer = request.headers.get("Referer")
    r = web.HTTPFound(referer or "/")
    r.set_cookie(COOKIE_NAME, "-deleted-", max_age=0, httponly=True)
    logging.info("user signed out.")
    return r

@get("/manage/blogs/create")
def manage_create_blog():
    return {
        "__template__": "manage_blog_edit.html",
        "id": "",
        "action": "/api/blogs"
    }

@get("/manage/blogs/edit")
def manage_edit_blog(request, *, id):
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError("blog was not found.")

    return {
        "__template__": "manage_blog_edit.html",
        "id" : id,
        "action": "/manage/blogs/" + id + "/edit"
    }

@post("/manage/blogs/{id}/edit")
def manage_update_blog(request, *, id, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError("name", "name cannot be empty.")
    if not summary or not summary.strip():
        raise APIValueError("summary", "summary cannot be empty.")
    if not content or not content.strip():
        raise APIValueError("cotent", "content cannot be empty.")

    blog = yield from Blog.find(id)
    if len(blog) == 0:
        blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    blog.name = name
    blog.summary = summary
    blog.content = content
    yield from blog.update()
    return blog

def get_cur_dir():
    print("file: %s" % __file__)
    print("realpath: %s" % os.path.realpath(__file__))
    return os.path.split(os.path.realpath(__file__))[0]
    path = sys.path[0]
    if os.path.isdir(path):
        return path
    elif os.path.isfile(path):
        return os.path.dirname(path)

@post("/api/image/upload")
def image_upload(request, *, upfile):
    check_admin(request)
    print("filename:%s" % upfile.filename)
    f = upfile.file
    save_name = next_id() + os.path.splitext(upfile.filename)[1]
    url = save_name
    store_path = os.path.join(get_cur_dir(), 'static\\umeditor\\images\\' + save_name)
    print("cur dir:%s, store path:%s" % (get_cur_dir(), store_path))
    if f:
        image = open(store_path, "w+b")
        image.write(f.read())
        image.close()
        
    return {
        'state' : 'SUCCESS',
        'url' : url
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
    L = [user.id, expires, hashlib.sha1(s.encode("utf-8")).hexdigest()]
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
        if sha1 != hashlib.sha1(s.encode("utf-8")).hexdigest():
            logging.info("invalid sha1")
            return None
        user.passwd = "******"
        return user
    except Exception as e:
        logging.exception(e)
        return None
