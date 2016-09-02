#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, aiomysql

def log(sql, args=()):
    logging.info("SQL: %s" % sql)

@asyncio.coroutine
def create_db_pool(loop, **kw):
    logging.info("create database connection pool...")
    global __db_pool
    __db_pool = yield from aiomysql.create_pool(
        host=kw.get("host", "localhost"),
        port=kw.get("port", 3306),
        user=kw["user"],
        password=kw["password"],
        db=kw["db"],
        charset=kw.get("charset", "utf8"),
        autocommit=kw.get("autocommit", True),
        maxsize=kw.get("maxsize", 10),
        minsize=kw.get("minsize", 1),
        loop=loop
    )
    if __db_pool is None:
        logging.info("create database connection pool failed.")
    else:
        logging.info("database connection pool create successed.")
        logging.info("conn: %s" % __db_pool.get())

@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __db_pool
    with (yield from __db_pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace("?", "%s"), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info("rows returned: %s" % len(rs))
        return rs

@asyncio.coroutine
def execute(sql, args):
    log(sql)
    global __db_pool
    with (yield from __db_pool) as conn:
        try:
            logging.info("use database connection: %s" % conn)
            cur = yield from conn.cursor()
            logging.info("use ucr: %s" % cur)
            yield from cur.execute(sql.replace("?", "%s"), args)
            affected = cur.rowcount
            logging.info("save %d rows to database." % affected)
            yield from cur.close()
        except BaseException as e:
            raise
        return affected
    logging.warn("sql %s %s execute failed." % (sql, args))

class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return "<%s, %s:%s>" % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl="varchar(100)"):
        super().__init__(name, ddl, primary_key, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=None):
        print("%s init." % self.__class__.__name__)
        super().__init__(name, "bigint", primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, "boolean", False, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, "real", primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, "text", False, default)

def create_args_string(num):
    L = []
    for n in range(num):
        L.append("?")
    return ", ".join(L)

class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        # 排除Model类本身
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称
        tableName = attrs.get("__table__", None) or name
        logging.info("found model: %s (table: %s)" % (name, tableName))
        # 获取所有的Field和主键名
        mappings = dict()
        fields = []
        primary_key = None
        for k, v in attrs.items():
            logging.info("attrs : %s, %s" % (k, v))
            if isinstance(v, Field):
                logging.info("  found mapping: %s ==> %s" % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primary_key:
                        raise RuntimeError("Duplicate primary key for field: %s" % k)
                    primary_key = k
                else:
                    fields.append(k)

        if not primary_key:
            raise RuntimeError("Primary key not found.")

        # 删除Field类型的k，即列名。以便通过属性的形式直接访问。
        # 例：u = User(id=111, name="Bob")
        # 如果不删除，u.id 指向IntegerField的一个实例
        # 如果删除，由于u没有属性id，就会调用User.__getattr__()方法
        # 而User.__getattr__()的实现是u["id"]，达到与dict访问方式一致的目的
        for k in mappings.keys():
            attrs.pop(k)

        escaped_fields = list(map(lambda f: "`%s`" % f, fields))
        attrs["__mappings__"] = mappings
        attrs["__table__"] = tableName
        attrs["__primary_key__"] = primary_key
        attrs["__fields__"] = fields
        attrs["__select__"] = "select `%s`, %s from `%s`" % (primary_key, ", ".join(escaped_fields), tableName)
        attrs["__insert__"] = "insert into `%s` (%s, `%s`) value (%s)" % (tableName, ", ".join(escaped_fields), primary_key, create_args_string(len(escaped_fields) + 1))
        attrs["__update__"] = "update `%s` set %s where `%s`=?" % (tableName, ", ".join(map(lambda f: "`%s`=?" % (mappings.get(f).name or f), fields)), primary_key)
        attrs["__delete__"] = "delete from `%s` where `%s`=?" % (tableName, primary_key)
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):

    #子类未实现__init__时,调用基类的__init__
    def __init__(self, **kw):
        print("%s init." % self.__class__.__name__)
        for k, v in kw.items():
            print(" %s : %s" % (k, v))

        #调用Model的基类进行构造
        super(Model, self).__init__(**kw)

    #当所访问的类的属性或函数不存在时，调用__getattr__获取
    #由于Model继承自dict类，因此使用obj.key与obj["key"]能达到相同的效果
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    #当所设定的类属性或函数不存在时，调用__setattr__进行设定
    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug("using default value for %s: %s" % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    @asyncio.coroutine
    def find(cls, pk):
        "find object by primary key"
        rs = yield from select("%s where `%s`=?" % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @classmethod
    @asyncio.coroutine
    def findall(cls):
        rs = yield from select(cls.__select__, None)
        if len(rs) == 0:
            return None
        return [cls(**u) for u in rs]

#    @classmethod
    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        logging.info("save to database: %s" % args)
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warn("failed to insert record: affected rows: %s" % rows)
