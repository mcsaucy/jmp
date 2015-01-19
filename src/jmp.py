#!/usr/bin/python

"""
The API component the JMP URL shortener

"""

from flask import Flask, redirect, request
import sqlite3, json

APP = Flask(__name__)

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
    A method to add an entry to the links table
    """
    #XXX: AUTHENTICATE FOR THIS METHOD
    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)
    #owner = #TODO: ... however I get the user's identity ...
    try:
        conn = sqlite3.connect('example.db')
        crsr = conn.cursor()
        #TODO: also insert OWNER into the table... once we support that
        crsr.execute(""" INSERT INTO links (shorty, longfellow)
                         VALUES (?,?) """, (shorty, longfellow))

        ret = crsr.fetchall()

        conn.commit()
        conn.close()
        return json.dumps([{"success" : True,
                            "results" : ret}])
    except sqlite3.Error as exc:
        return json.dumps([{"success" : False,
                            "error" : exc.args}])

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

    if shorty == None and longfellow == None:
        raise KeyError

    return _lookup(shorty, longfellow)

def _lookup(shorty, longfellow):
    """
    The muscle behind the /query route and, by extension, the lookup method
    """
    try:
        conn = sqlite3.connect('example.db')
        crsr = conn.cursor()

        ret = ()

        if longfellow != None and shorty != None:
            crsr.execute(""" SELECT id FROM links
                             WHERE longfellow=? AND shorty=?
                             ORDER BY id """, (longfellow, shorty))
            tmp = crsr.fetchone()
            if tmp != None:
                ret = {"id" : tmp[0]}
        elif longfellow != None:
            crsr.execute(""" SELECT id, shorty FROM links
                             WHERE longfellow=?
                             ORDER BY id """, (longfellow,))
            tmp = crsr.fetchone()
            if tmp != None:
                ret = {"id" : tmp[0], "shorty" : tmp[1]}
        else:
            crsr.execute(""" SELECT id, longfellow FROM links
                             WHERE shorty=?
                             ORDER BY id """, (shorty,))
            tmp = crsr.fetchone()
            if tmp != None:
                ret = {"id" : tmp[0], "longfellow" : tmp[1]}

        conn.close()
        return json.dumps([{"success" : True,
                            "results" : ret}])
    except sqlite3.Error as exc:
        return json.dumps([{"success" : False,
                            "error" : exc.args}])

@APP.route("/q/<db_query>") #TODO: remove this route entirely
def query(db_query):
    """
    A completely insecure, totally poor practice DB debugging method
    """
    try:
        conn = sqlite3.connect('example.db')
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
        conn = sqlite3.connect('example.db')
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
