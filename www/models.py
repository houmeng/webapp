#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = "meng hou"

from orm import Model, StringField, IntegerField, BooleanField, FloatField, TextField
import orm, asyncio, hashlib
import sys, time, uuid

def next_id():
    return "%015d%s000" % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = "users"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    name = StringField(ddl="varchar(50)")
    email = StringField(ddl="varchar(50)")
    passwd = StringField(ddl="varchar(50)")
    image = StringField(ddl="varchar(500)")
    admin = BooleanField()
    created_at = FloatField(default=time.time)

class Blog(Model):
    __table__ = "blogs"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    name = StringField(ddl="varchar(50)")
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    summary = StringField(ddl="varchar(200)")
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):
    __table__ = "comments"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    blog_id = StringField(ddl="varchar(50)")
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    content = TextField()
    created_at = FloatField(default=time.time)

def create_admin(name="admin", passwd="123456", email="admin@163.com"):
    admin = yield from User.findall("admin=?", [1])
    if len(admin) > 0:
        return
    uid = next_id()
    crypto_passwd = hashlib.sha1(("%s:%s" % (email, passwd)).encode("utf-8")).hexdigest()
    sha1_passwd = "%s:%s" % (uid, crypto_passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode("utf-8")).hexdigest(), image="http://www.gravatar.com/avatar/%s?d=mm&s=120" % hashlib.md5(email.encode("utf-8")).hexdigest(), admin=True)
    yield from user.save()

@asyncio.coroutine
def test(loop):
    yield from orm.create_db_pool(loop, user="root", password="root", db="webapp", charset="utf8")

    user = User(name="Bob", email="test01111111@neu.com", passwd="123456", image="about:blank")
    yield from user.save()
#    user.insert()
#    u = yield from user.find("123")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
#    loop.run_forever()

    loop.close()
    if loop.is_closed():
        sys.exit(0)
