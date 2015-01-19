#!/usr/bin/python

"""
The API component the JMP URL shortener

"""

from flask import Flask, redirect, request
import sqlite3, json

APP = Flask(__name__)


@APP.route("/")
def hello():
    """
    A simple Hello World route
    """
    return "Hello World!"

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

@APP.route("/forward/<shorty>") #TODO: have this wrap a plugin method
def forward(shorty):
    """
    A simple method to look up a shorty link's target longfellow
    """
    try:
        conn = sqlite3.connect('example.db')
        crsr = conn.cursor()
        crsr.execute(""" SELECT longfellow FROM links
                         WHERE shorty=? ORDER BY id """, (shorty,))
        ret = crsr.fetchall()

        conn.close()
        return json.dumps([{"success" : True,
                            "results" : ret}])
    except sqlite3.Error as exc:
        return json.dumps([{"success" : False,
                            "error" : exc.args}])


@APP.route("/reverse/<longfellow>") #TODO: have this wrap a plugin method
def reverse(longfellow):
    """
    A simple method to look up a longfellow link's shortys
    """
    try:
        conn = sqlite3.connect('example.db')
        crsr = conn.cursor()
        crsr.execute(""" SELECT shorty FROM links
                         WHERE longfellow=? ORDER BY id """, (longfellow,))
        ret = crsr.fetchall()

        conn.close()
        return json.dumps([{"success" : True,
                            "results" : ret}])
    except sqlite3.Error as exc:
        return json.dumps([{"success" : False,
                            "error" : exc.args}])

@APP.route("/query")
def lookup():
    longfellow = request.args.get("long", None)
    shorty = request.args.get("short", None)

    if shorty == None and longfellow == None:
        raise KeyError
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
    Initialize our database
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
