#!/usr/bin/python

"""
The API component of the JMP URL shortener

"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from flask import Flask, redirect, request
import sqlite3, json

BASE = declarative_base()

class Link(BASE):
    """
    A simple schema for a Link table
    """

    __tablename__ = "links"
    link_id = Column(Integer, primary_key=True, autoincrement=True)
    shorty = Column(String(256), nullable=False, unique=True)
    longfellow = Column(String(2048), nullable=False)

APP = Flask(__name__)
ENGINE = create_engine("sqlite:///jmp.db")
BASE.metadata.create_all(ENGINE)

DBSESSION = sessionmaker(bind=ENGINE)

DB_NAME = "jmp.db"


@APP.route("/redir/<target>")
def redir(target):
    """
    A simple redirection route
    """
    return redirect("http://{0}".format(target), code=302)

#@APP.route("/cookie_dump") #XXX: nuke this function when it's no longer useful
#def cookie_dump():
#    """
#    Take a look into the cookie jar. None of this is saved.
#    """
#    return str(request.cookies.items())

@APP.route("/new")
def add_link():
    """
    A method to add an entry to the links table.

    If shorty and longfellow aren't provided, throw a KeyError because why not?
    """
    #XXX: AUTHENTICATE FOR THIS METHOD
    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)
    #owner = #TODO: ... however I get the user's identity ...
    if shorty == None or longfellow == None:
        raise KeyError

    try:
        session = DBSESSION()
        new_link = Link(shorty=shorty, longfellow=longfellow)
        session.add(new_link)
        session.commit()

        return json.dumps([{"success" : True}])
    except exc.IntegrityError as exception:
        return json.dumps([{"success" : False,
            "error" : exception.args}])

@APP.route("/delete")
def rm_link():
    """
    A method to remove an entry from the links table.

    If shorty and longfellow aren't provided, throw a KeyError because why not?
    """
    #XXX: AUTHENTICATE FOR THIS METHOD
    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)
    #user = #TODO: ... however I get the user's identity ...
    if shorty == None or longfellow == None:
        raise KeyError

    try:
        session = DBSESSION()
        #TODO: verify that the user owns this link
        #    : ... this may be possible by simply including the username
        #    :     in the schema and querying based on that

        matching_links = session.query(Link).filter_by(
                shorty=shorty, longfellow=longfellow)

        for link in matching_links:
            session.delete(link)

        session.commit()
        return json.dumps([{"success" : True}])

    except sqlite3.Error as exception:
        return json.dumps([{"success" : False,
            "error" : exception.args}])

@APP.route("/query")
def lookup():
    """
    A generalized lookup wrapper method for entries in the links table based on
    request arguments.

    Looks up a row in the links tables and returns the columns in the following
    manner:

    If given 'short' and 'long', then return an ID.

    If just given 'short', then return a longfellow and an ID.

    If just given 'long', then return a shorty and an ID.

    If given nothing, explode with a key error.
    """

    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)

    return json.dumps(_lookup(shorty, longfellow))

def _lookup(shorty, longfellow):
    """
    The muscle behind the /query route and, by extension, the lookup method
    """

    if shorty == None and longfellow == None: #TODO: throw bad request
        raise KeyError

    try:
        conn = sqlite3.connect(DB_NAME)
        crsr = conn.cursor()

        ret = ()

        if longfellow != None and shorty != None: #look up an ID
            crsr.execute(""" SELECT id FROM links
                             WHERE longfellow=? AND shorty=?
                             ORDER BY id """, (longfellow, shorty))
            tmp = crsr.fetchone()
            if tmp != None:
                ret = {"id" : tmp[0]}
        elif longfellow != None: #look up an ID, shorty
            crsr.execute(""" SELECT id, shorty FROM links
                             WHERE longfellow=?
                             ORDER BY id """, (longfellow,))
            tmp = crsr.fetchone()
            if tmp != None:
                ret = {"id" : tmp[0], "shorty" : tmp[1]}
        else: #look up an ID, longfellow
            crsr.execute(""" SELECT id, longfellow FROM links
                             WHERE shorty=?
                             ORDER BY id """, (shorty,))
            tmp = crsr.fetchone()
            if tmp != None:
                ret = {"id" : tmp[0], "longfellow" : tmp[1]}

        conn.close()
        return [{"success" : True,
                 "results" : ret}]
    except sqlite3.Error as exc:
        return [{"success" : False,
                 "error" : exc.args}]

@APP.route("/q/<db_query>") #TODO: remove this route entirely
def query(db_query):
    """
    A completely insecure, totally poor practice DB debugging method
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        crsr = conn.cursor()
        crsr.execute(db_query) #XXX: HOLY SHITBALLS THIS IS INSECURE
        conn.commit()

        ret = crsr.fetchall()

        conn.close()
        return json.dumps([{"success" : True,
                            "results" : ret}])
    except sqlite3.Error as exc:
        return json.dumps([{"success" : False,
                            "error" : exc.args}])

@APP.route("/q_init") #TODO: kill this route with fire
def db_init():
    """
    Initialize our database.

    This shouldn't really exist, but it does for dev purposes
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        crsr = conn.cursor()
        crsr.execute("""CREATE TABLE links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shorty TEXT, longfellow TEXT )""")
        conn.close()
        return json.dumps([{"success" : True}])
    except sqlite3.Error as exc:
        return json.dumps([{"success" : False,
                            "error" : exc.args}])

if __name__ == "__main__":
    APP.run(debug=True)
