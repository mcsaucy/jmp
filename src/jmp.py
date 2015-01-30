#!/usr/bin/python

"""
The API component of the JMP URL shortener

"""

from functools import wraps
from hashlib import sha256

from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from flask import Flask, redirect, request
import json

from re import match

BASE = declarative_base()

class Link(BASE):
    """
    A simple schema for a Link table
    """

    __tablename__ = "links"
    link_id = Column(Integer, primary_key=True, autoincrement=True)
    shorty = Column(String(256), nullable=False, unique=True)
    longfellow = Column(String(2048), nullable=False)
    owner = Column(String(len(sha256("").hexdigest())), nullable=False)

APP = Flask(__name__)

ENGINE = create_engine("sqlite:///jmp.db") #read this in from config
BASE.metadata.create_all(ENGINE)

ALLOWED_PROTOCOLS = ("http://", "https://", "ftp://",)
RESERVED_SHORTS = ("api",)
SUPPORTED_SHORT_RE = r"^\w+$"
MAX_LONGFELLOW_SIZE = 2048
MAX_SHORT_SIZE = 140

ENTRY_UUID_HASH = "LOLMIGHTYSALTYINHERE!" #TODO: move this to a protected conf

DBSESSION = sessionmaker(bind=ENGINE)

def req_auth_api(func):
    """
    A simple auth wrapper for API calls
    """
    @wraps(func)
    def auth_decor(*args, **kwargs):
        """
        Pull in entry UUID and username from webauth. If either isn't provided,
        bail out.
        """

        entry_uuid = request.environ.get("X-WEBAUTH-ENTRYUUID", None)
        username = request.environ.get("X-WEBAUTH-USERNAME", None)

        if entry_uuid == None or username == None:
            return json.dumps([{"success" : False,
                "error" : "Authentication required"}])
        return func(*args, **kwargs)
    return auth_decor

def hash_and_salt(plain, salt=ENTRY_UUID_HASH):
    """
    Designed to be used for entry-uuid hashing, return a sha256 hash of 'plain'
    after applying 'salt'
    """

    return sha256("{0}|{1}".format(plain, salt)).hexdigest()

def _verify_long(longfellow):
    """
    Verify a longfellow (URL) to be valid and of a supported protocol
    """

    if len(longfellow) > MAX_LONGFELLOW_SIZE:
        return False

    supported_proto = False

    for proto in ALLOWED_PROTOCOLS:
        if longfellow.startswith(proto):
            supported_proto = True
            break

    if not supported_proto:
        return False

    return True

def _verify_short(shorty):
    """
    Verify a short (JMP extension, effectively) to be valid
    """

    if len(shorty) > MAX_SHORT_SIZE:
        return False

    if match(SUPPORTED_SHORT_RE, shorty) == None:
        return False

    if shorty in RESERVED_SHORTS: #It'd be awkward if we stomped on /api...
        return False

    return True


@APP.route("/<short>")
def redir(short):
    """
    Redirect the user to a longfellow given a shorty
    """
    rows = _lookup(shorty=short, longfellow=None)
    if rows[0]["success"] == False or len(rows[0]["results"]) == 0:
        return json.dumps([{"success" : False,
            "error" : "Nonexistent short. You should create it!"}])

    longfellow = rows[0]["results"][0][2] #TODO: this is fugly. fix it.
    return redirect(longfellow, code=302)

#@APP.route("/cookie_dump") #XXX: nuke this function when it's no longer useful
#def cookie_dump():
#    """
#    Take a look into the cookie jar. None of this is saved.
#    """
#    return str(request.cookies.items())

@APP.route("/api/new")
@req_auth_api
def add_link():
    """
    A method to add an entry to the links table.
    """

    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)
    entry_uuid = request.environ.get("X-WEBAUTH-ENTRYUUID", None)

    if entry_uuid == None:
        return json.dumps([{"success" : False,
            "error" : "That's weird. You lack an entry-uuid..."}])

    owner = hash_and_salt(entry_uuid)

    if not _verify_short(shorty):
        return json.dumps([{"success" : False,
            "error" : "Invalid short"}])

    if not _verify_long(longfellow):
        return json.dumps([{"success" : False,
            "error" : "Invalid URL"}])

    if shorty == None or longfellow == None:
        return json.dumps([{"success" : False,
            "error" : "Incomplete request"}])

    try:
        session = DBSESSION()
        new_link = Link(shorty=shorty, longfellow=longfellow, owner=owner)
        session.add(new_link)
        session.commit()

        return json.dumps([{"success" : True}])
    except exc.IntegrityError as exception:
        return json.dumps([{"success" : False,
            "error" : exception.args}])

@APP.route("/api/delete")
@req_auth_api
def rm_link():
    """
    A method to remove an entry from the links table.
    """

    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)

    if shorty == None or longfellow == None:
        return json.dumps([{"success" : False,
            "error" : "Incomplete request"}])

    entry_uuid = request.environ.get("X-WEBAUTH-ENTRYUUID", None)

    if entry_uuid == None:
        return json.dumps([{"success" : False,
            "error" : "That's weird. You lack an entry-uuid..."}])

    owner = hash_and_salt(entry_uuid)

    try:
        session = DBSESSION()

        matching_links = session.query(Link).filter_by(
                shorty=shorty, longfellow=longfellow)

        link_deleted = False
        at_least_one_link = False

        for link in matching_links:
            at_least_one_link = True
            if link.owner == owner: #TODO: also check if user is admin
                session.delete(link)
                link_deleted = True

        if not at_least_one_link:
            #Just in case we ever want to extend the schema to allow separation
            #of privately and publicly shared links
            return json.dumps([{"success" : False,
                "error" : "Link not found"}])

        if not link_deleted:
            return json.dumps([{"success" : False,
                "error" : "Keep your hands to yourself"}])

        session.commit()
        return json.dumps([{"success" : True}])

    except exc.SQLAlchemyError as exception:
        return json.dumps([{"success" : False,
            "error" : exception.args}])

@APP.route("/api/query")
def lookup():
    """
    A generalized lookup wrapper method for entries in the links table
    """

    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)

    return json.dumps(_lookup(shorty, longfellow))

def _lookup(shorty, longfellow):
    """
    The muscle behind the /query route and, by extension, the lookup method
    """

    if shorty == None and longfellow == None:
        return [{"success" : False,
            "error" : "Incomplete request"}]

    try:
        session = DBSESSION()
        ret = ()

        if longfellow != None and shorty != None:
            ret = session.query(Link).filter_by(
                    shorty=shorty, longfellow=longfellow).all()

        elif longfellow != None:
            ret = session.query(Link).filter_by(
                    longfellow=longfellow).all()

        elif shorty != None:
            ret = session.query(Link).filter_by(
                    shorty=shorty).all()

        serializable_ret = [(link.link_id,
                             link.shorty,
                             link.longfellow
                            ) for link in ret]

        return [{"success" : True,
                 "results" : serializable_ret}]
    except exc.SQLAlchemyError as exception:
        return [{"success" : False,
            "error" : exception.args}]

@APP.route("/api/dump") #TODO: remove this route entirely
def dump():
    """
    Dump the DB contents. Not really a great thing to have in prod...
    """
    try:
        session = DBSESSION()
        ret = session.query(Link).all()

        serializable_ret = [(link.link_id,
                             link.shorty,
                             link.longfellow
                            ) for link in ret]

        return json.dumps([{"success" : True,
                 "results" : serializable_ret}])
    except exc.SQLAlchemyError as exception:
        return json.dumps([{"success" : False,
            "error" : exception.args}])

if __name__ == "__main__":
    APP.run(debug=True)
