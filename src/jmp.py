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

from flask import Flask, redirect, request, jsonify

from ConfigParser import RawConfigParser

from re import match

APP = Flask(__name__)

DEFAULT_CONFIG_VALUES = {
        "HOSTNAME" : "localhost",
        "ENGINE_URL" : "sqlite:///jmp.db",
        "ALLOWED_PROTOCOLS" : "http://,https://,ftp://",
        "RESERVED_SHORTS" : "api",
        "SUPPORTED_SHORT_RE" : r"^\w+$",
        "MAX_LONGFELLOW_SIZE" : 2048,
        "MAX_SHORT_SIZE" : 140,
        "USER_ID" : "X-JMP-USER-ID",
        "USER_DISPLAY_NAME" : "X-EMAIL-ADDR",
        "SALT" : "LOLMIGHTYSALTYINHERE!"
        }


CONFIG = RawConfigParser(DEFAULT_CONFIG_VALUES)

#TODO: ensure jmp.secure.cfg is actually secure
#TODO; have better mechanism for locating config
CONFIG.read(["jmp.cfg", "../jmp.cfg", "jmp.secure.cfg", "../jmp.secure.cfg"])

HOSTNAME = CONFIG.get("GENERAL", "HOSTNAME")
ALLOWED_PROTOCOLS = CONFIG.get("RESTRICTIONS", "ALLOWED_PROTOCOLS").split(",")
RESERVED_SHORTS = CONFIG.get("RESTRICTIONS", "RESERVED_SHORTS").split(",")
SUPPORTED_SHORT_RE = CONFIG.get("RESTRICTIONS", "SUPPORTED_SHORT_RE")
MAX_LONGFELLOW_SIZE = CONFIG.getint("RESTRICTIONS", "MAX_LONGFELLOW_SIZE")
MAX_SHORT_SIZE = CONFIG.getint("RESTRICTIONS", "MAX_SHORT_SIZE")

ENGINE_URL = CONFIG.get("DATABASE", "ENGINE_URL")
USER_ID = CONFIG.get("AUTH", "USER_ID")
USER_DISPLAY_NAME = CONFIG.get("AUTH", "USER_DISPLAY_NAME")
SALT = CONFIG.get("AUTH", "SALT")

BASE = declarative_base()
ENGINE = create_engine(ENGINE_URL)

class Link(BASE):
    """
    A simple schema for a Link table
    """

    __tablename__ = "links"
    link_id = Column(Integer, primary_key=True, autoincrement=True)
    shorty = Column(String(256), nullable=False, unique=True)
    longfellow = Column(String(2048), nullable=False)
    owner = Column(String(len(sha256("").hexdigest())), nullable=False)

BASE.metadata.create_all(ENGINE)
DBSESSION = sessionmaker(bind=ENGINE)

def _get_user_id(req_env):
    """
    Fish the configured user ID argument from request headers
    """
    return "EC865197-2C49-443A-8CB0-9A8870905C3C" #XXX
    return req_env.get(USER_ID, None)

def _get_user_dn(req_env):
    """
    Fish the configured user display name argument from request headers
    """
    return "jeid64" #XXX
    return req_env.get(USER_DISPLAY_NAME, None)

def req_auth_api(func):
    """
    A simple auth wrapper for API calls
    """
    @wraps(func)
    def auth_decor(*args, **kwargs):
        """
        Pull in user id and user display name from headers.
        If either isn't provided, bail out.
        """

        user_id = _get_user_id(request.environ)
        user_dn = _get_user_dn(request.environ)

        if user_id == None or user_dn == None:
            return jsonify(success=False,
                error="Authentication required"), 401
        return func(*args, **kwargs)
    return auth_decor

def hash_and_salt(user, resource, salt=SALT):
    """
    Designed to be used for resource owner identifiers, returns a SHA-256 hash
    """

    return sha256("{0}{1}{2}".format(
        sha256(user).digest(),
        sha256(resource).digest(),
        sha256(salt).digest())
        ).hexdigest()

def _verify_long(longfellow):
    """
    Verify a longfellow (URL) to be valid and of a supported protocol
    """

    if longfellow == None:
        return False

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

    if shorty == None:
        return False

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
    if rows["success"] == False or len(rows["results"]) == 0:
        return jsonify(success=False,
            error="Nonexistent short. You should create it!"), 404

    longfellow = rows["results"][0][2] #TODO: this is fugly. fix it.
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
    user_id = _get_user_id(request.environ)

    if user_id == None:
        return jsonify(success=False,
            error="BUG! Someone horked the auth decorator..."), 418

    if shorty == None or longfellow == None:
        return jsonify(success=False,
            error="Incomplete request"), 400
    owner = hash_and_salt(user_id, shorty)


    if not _verify_short(shorty):
        return jsonify(success=False,
            error="Invalid short"), 400

    if not _verify_long(longfellow):
        return jsonify(success=False,
            error="Invalid URL"), 400

    try:
        session = DBSESSION()
        new_link = Link(shorty=shorty, longfellow=longfellow, owner=owner)
        session.add(new_link)
        session.commit()

        return jsonify(success=True)
    except exc.IntegrityError:
        return jsonify(success=False,
            error="short already exists"), 400

@APP.route("/api/delete")
@req_auth_api
def rm_link():
    """
    A method to remove an entry from the links table.
    """

    shorty = request.args.get("short", None)

    if shorty == None:
        return jsonify(success=False,
            error="Incomplete request"), 400

    user_id = _get_user_id(request.environ)

    if user_id == None:
        return jsonify(success=False,
            error="BUG! Someone horked the auth decorator..."), 418

    owner = hash_and_salt(user_id, shorty)

    try:
        session = DBSESSION()

        matching_links = session.query(Link).filter_by(shorty=shorty)

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
            return jsonify(success=False,
                error="Link not found"), 404

        if not link_deleted:
            return jsonify(success=False,
                error="Keep your hands to yourself"), 403

        session.commit()
        return jsonify(success=True)

    except exc.SQLAlchemyError as exception:
        return jsonify(success=False,
            error=exception.args), 500

@APP.route("/api/query")
def lookup():
    """
    A generalized lookup wrapper method for entries in the links table
    """

    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)

    return jsonify(**_lookup(shorty, longfellow))

def _lookup(shorty, longfellow):
    """
    The muscle behind the /query route and, by extension, the lookup method
    """

    if shorty == None and longfellow == None:
        return {"success" : False,
            "error" : "Incomplete request"}

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

        return {"success" : True,
            "results" : serializable_ret}
    except exc.SQLAlchemyError as exception:
        return {"success" : False,
            "error" : exception.args}

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
                             link.longfellow,
                             link.owner
                            ) for link in ret]

        return jsonify(success=True,
            results=serializable_ret)
    except exc.SQLAlchemyError as exception:
        return jsonify(success=False,
            error=exception.args), 500

if __name__ == "__main__":
    APP.run(debug=True)
