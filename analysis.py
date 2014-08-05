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
import collections
import sqlite3
import itertools
import urllib.request

from io import BytesIO
from xml.dom import minidom

regex = re.compile("Qgs\w+")

db = sqlite3.connect("data.sqlite")
cur = db.cursor()
cur.execute("DROP TABLE counts")

cur.execute("CREATE TABLE counts ("
            "plugin STRING,"
            "word STRING,"
            "count INTEGER"
            ")")


def get_plugins():
    plugin_request = requests.get("http://plugins.qgis.org/plugins/plugins.xml?qgis=2.4")
    xml = minidom.parseString(plugin_request.text)
    plugins = xml.getElementsByTagName("pyqgis_plugin")
    for plugin in plugins:
        name = plugin.attributes["name"].value
        url = plugin.getElementsByTagName("download_url")[0].childNodes[0].data
        filename = plugin.getElementsByTagName("file_name")[0].childNodes[0].data
        yield name, url, filename

def count_from_plugin(name, url, filename):
    try:
        content = open(r"data\{}".format(filename), "rb")
        print("Uses downloaded version of {}".format(name))
    except IOError:
        print("Not found so fetching {}".format(url))
        urllib.request.urlretrieve(url, r"data\{}".format(filename))
        content = open(r"data\{}".format(filename), "rb")

    zip = zipfile.ZipFile(content)
    names = zip.namelist()
    pyfiles = (name for name in names if name.endswith(".py"))
    words = []
    for pyfile in pyfiles:
        with zip.open(name=pyfile) as f:
            text = str(f.read()).split(r'\n')

        for line, linetext in enumerate(text):
            matches = regex.findall(linetext)
            if matches:
                context = text[line-5:line+5]
                print(matches)
                print("\n".join(context))
                words.extend(matches)

    counts = collections.Counter(words)

    for word, count in counts.items():
        sql = "INSERT INTO counts VALUES('{}','{}',{})".format(url, word, count)
        cur.execute(sql)
        print(word, count)


try:
    os.mkdir("data")
except FileExistsError:
    pass

plugins = list(get_plugins())
print(len(plugins))

for plugin in itertools.islice(plugins, 10):
    count_from_plugin(*plugin)

db.commit()

cur.execute("SELECT word, sum(count) FROM counts GROUP BY word ORDER BY sum(count) DESC")
print("=====Totals=====")
for row in cur.fetchall():
    print(row[0], row[1])

db.close()
