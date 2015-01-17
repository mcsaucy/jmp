#!/usr/bin/python

"""
The API component the JMP URL shortener

Database tables needed:
    - links table
        + link ID -- primary, autoinc
        + short link
        + full link
        + owner ID
    - owner table
        + owner ID -- primary, autoinc
        + owner entry UUID
        + count of existing links (for quota purposes)

TODO:
    - add config file reader (also, define config schema; something simple)
        + consider OLC
    - detach database logic to allow for SQL database plugins
        + create sqlite plugin
    - auto-create database tables if they don't exist
    - require webauth login
"""

from flask import Flask, redirect
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

@APP.route("/q/<db_query>")
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

@APP.route("/q_init")
def db_init():
    """
    Initialize our database
    """
    try:
        conn = sqlite3.connect('example.db')
        crsr = conn.cursor()
        crsr.execute("""CREATE TABLE links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        short TEXT, target TEXT )""")
        conn.close()
        return json.dumps([{"success" : True}])
    except sqlite3.Error as exc:
        return json.dumps([{"success" : False,
                            "error" : exc.args}])

if __name__ == "__main__":
    APP.run(debug=True)
