#!/usr/bin/env python

import cgitb; cgitb.enable()

import cgi
import datetime
import json
import os
from string import Template
import sys
import urllib

import MySQLdb
from wikitools import wiki
from wikitools import api

TOOL_DIR = "/data/project/apersonbot/public_html/candidate-search/"
SQL_TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"

def main():
    page_template = None
    try:
        with open(os.path.join(TOOL_DIR, "template.txt")) as template_file:
            page_template = Template(template_file.read())
    except IOError as error:
        print("<h1>Search Error!</h1><p>I couldn't read the web template.<br /><small>Details: " + str(error) + "</small>")
        sys.exit(0)

    def error_and_exit(error):
        print(page_template.substitute(content="<p class='error'>{}</p>".format(error)))
        sys.exit(0)

    form = cgi.FieldStorage()
    try:
        parsed_count = int(form["count"].value)
    except:
        try:
	    error_and_exit("Invalid count specified: {}".format(form["count"].value))
        except KeyError:
	    error_and_exit("No count specified.")

    if "tenure" in form and not form["tenure"].value.replace(".", "").isdigit():
        error_and_exit("Invalid tenure specified: {}".format(form["tenure"].value))
    elif "tenure" not in form:
        tenure = 2
    else:
        tenure = float(form["tenure"].value)

    if "last-activity" in form and not form["last-activity"].value.replace(".", "").isdigit():
        error_and_exit("Invalid number of edits last activity specified: {}".format(form["last-activity"].value))
    elif "last-activity" not in form:
        last_activity = 2.0
    else:
        last_activity = float(form["last-activity"].value)

    SORT_BY_LOOKUP = {"registration": "user_registration", "count": "user_editcount"}
    if "sort-by" not in form or form["sort-by"].value not in SORT_BY_LOOKUP:
        error_and_exit("Invalid sorting method specified: " + form["sort-by"].value)
    else:
        sort_by = SORT_BY_LOOKUP[form["sort-by"].value]

    if "sort-order" not in form or form["sort-order"].value.upper() not in ("ASC", "DESC"):
        sort_order = "DESC"
    else:
        sort_order = form["sort-order"].value.upper()

    # Query db
    db = MySQLdb.connect(db='enwiki_p', host="enwiki.labsdb", read_default_file=os.path.expanduser("~/replica.my.cnf"))
    cursor = db.cursor()

    with open(os.path.join(TOOL_DIR, "query.txt")) as query_file:
        query_template = Template(query_file.read())

    # Calculate start time for query
    parsed_starttime = (datetime.datetime.now() - datetime.timedelta(days=tenure * 365.0)).strftime(SQL_TIMESTAMP_FORMAT)

    # Calculate active time for query
    parsed_activetime = (datetime.datetime.now() - datetime.timedelta(days=last_activity * 30.0)).strftime(SQL_TIMESTAMP_FORMAT)

    cursor.execute(query_template.substitute(count=parsed_count,
        starttime=parsed_starttime, activetime=parsed_activetime,
        sortby=sort_by, sortorder=sort_order))
    results = cursor.fetchall()

    # Define display helpers
    display_timestamp = lambda timestamp: datetime.datetime.strptime(timestamp, SQL_TIMESTAMP_FORMAT).strftime("%d %B %Y") 

    # Display results
    content = "<table>"
    content += "<tr><th>Name</th><th>Edit count</th><th>Registration</th><th>Last edit</th></tr>"
    for result in results:
        content += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(wikilink("User:" + result[0]),
            edit_counter_link(result[0], "{:,d}".format(int(result[1]))),
            display_timestamp(result[2]),
            wikilink("Special:Contributions/" + result[0], display_timestamp(result[3])))
    content += "</table>"

    print(page_template.substitute(content=content))

def edit_counter_link(user_name, link_title):
    return "<a href='https://tools.wmflabs.org/supercount/index.php?user={}&project=en.wikipedia.org&toplimit=10'>{}</a>".format(user_name, link_title)

def wikilink(page_name, link_title=None):
    if not link_title:
        link_title = page_name
    return "<a href='https://en.wikipedia.org/wiki/{0}' title='{0} on English Wikipedia'>{1}</a>".format(page_name, link_title)

main()
