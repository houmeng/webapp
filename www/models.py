#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = "meng hou"

from orm import Model, StringField, IntegerField, BooleanField, FloatField, TextField
import orm, asyncio
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
