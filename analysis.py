"""
Downloads QGIS plugins and does a word count on any Qgs* classes.

Why? Because I can

Needs zip file caching and other smart things.

In the future it should read from the QGIS plugins XML, or REST API, to download the latest version for each plugin.

Might use pandas in the future for data stuff.
"""
import requests
import os
import zipfile
import re
import sqlite3
import itertools
import urllib.request
import begin

from io import BytesIO
from xml.dom import minidom

import server

regex = re.compile("Qgs\w+")

db = sqlite3.connect("data.sqlite")

def get_plugins(qgisversion='2.4'):
    """
    Fetch the plugins from plugin repo
    :return: name, url, filename
    """
    plugin_request = requests.get("http://plugins.qgis.org/plugins/plugins.xml?qgis={}".format(qgisversion))
    xml = minidom.parseString(plugin_request.text)
    plugins = xml.getElementsByTagName("pyqgis_plugin")
    for plugin in plugins:
        name = plugin.attributes["name"].value
        url = plugin.getElementsByTagName("download_url")[0].childNodes[0].data
        filename = plugin.getElementsByTagName("file_name")[0].childNodes[0].data
        yield name, url, filename

def count_from_text(name, text):
    cur = db.cursor()
    for line, linetext in enumerate(text):
        matches = regex.findall(linetext)
        if matches:
            context = text[line-5:line+5]
            context = "\n".join(context)
            for match in matches:
                sql = "INSERT INTO counts VALUES(:name,:match,:context)"
                cur.execute(sql, dict(name=name, match=match, context=context))

def count_from_plugin(name, url, filename):
    try:
        content = open(r"data{0}{1}".format(os.sep,filename), "rb")
        print("Using pre-downloaded version of {}".format(name))
    except IOError:
        print("Not found so fetching {}".format(url))
        urllib.request.urlretrieve(url, r"data{0}{1}".format(os.sep,filename))
        content = open(r"data{0}{1}".format(os.sep,filename), "rb")

    zip = zipfile.ZipFile(content)
    names = zip.namelist()
    pyfiles = (name for name in names if name.endswith(".py"))
    words = []
    for pyfile in pyfiles:
        with zip.open(name=pyfile) as f:
            text = str(f.read()).split(r'\n')

        count_from_text(name, text)

def scrape_plugins(count):

    cur = db.cursor()
    cur.executescript("DROP TABLE IF EXISTS counts;"
                "CREATE TABLE counts ("
                "plugin STRING,"
                "word STRING,"
                "context STRING"
                ");")
    try:
        os.mkdir("data")
    except FileExistsError:
        pass

    plugins = list(get_plugins())

    if not count:
        count = len(plugins)
    else:
        count = int(count)

    print("Scanning {} of {}".format(count, len(plugins)))

    for number, plugin in enumerate(itertools.islice(plugins, count)):
        print(number)
        count_from_plugin(*plugin)

    db.commit()

    cur.execute("SELECT word, count(word) FROM counts GROUP BY word ORDER BY count(word) DESC")
    print("=====Totals=====")
    for row in cur.fetchall():
        print(row[0], row[1])

    db.close()

@begin.start
def run(serve_the_things=False,
        scrape_the_things=True,
        count=None):

    if serve_the_things:
        server.run_server(db)
        return

    if scrape_the_things:
        scrape_plugins(count)


