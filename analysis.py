"""
Downloads QGIS plugins and does a word count on any Qgs* classes.

Why? Because I can

Needs zip file caching and other smart things.

In the future it should read from the QGIS plugins XML, or REST API, to download the latest version for each plugin.

Might use pandas in the future for data stuff.
"""
import requests
import zipfile
import re
import collections
import sqlite3
import itertools

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
        yield name, url

def count_from_plugin(name, url):
    print("Fetching {}".format(url))
    r = requests.get(url)
    content = BytesIO(r.content)
    zip = zipfile.ZipFile(content)
    names = zip.namelist()
    pyfiles = (name for name in names if name.endswith(".py"))
    words = []
    for pyfile in pyfiles:
        with zip.open(name=pyfile) as f:
            text = str(f.read())
            matches = regex.findall(text)
            words.extend(matches)
    counts = collections.Counter(words)

    for word, count in counts.items():
        sql = "INSERT INTO counts VALUES('{}','{}',{})".format(url, word, count)
        cur.execute(sql)
        print(word, count)

plugins = list(get_plugins())
print(len(plugins))

for name, url in itertools.islice(plugins, 10):
    count_from_plugin(name, url)

db.commit()

cur.execute("SELECT word, sum(count) FROM counts GROUP BY word")
print("=====Totals=====")
for row in cur.fetchall():
    print(row[0], row[1])

db.close()
