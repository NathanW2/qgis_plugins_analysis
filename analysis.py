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

from io import BytesIO

regex = re.compile("Qgs\w+")

db = sqlite3.connect("data.sqlite")
cur = db.cursor()
cur.execute("DROP TABLE counts")

cur.execute("CREATE TABLE counts ("
            "plugin STRING,"
            "word STRING,"
            "count INTEGER"
            ")")

plugins = ["http://plugins.qgis.org/plugins/qgsexpressionsplus/version/0.3/download/",
           "http://plugins.qgis.org/plugins/openlayers_plugin/version/1.3.3/download/"]

def count_from_plugin(plugin):
    print("Fetching {}".format(plugin))
    r = requests.get(plugin)
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
        sql = "INSERT INTO counts VALUES('{}','{}',{})".format(plugin, word, count)
        cur.execute(sql)
        print(word, count)

for url in plugins:
    count_from_plugin(url)

cur.execute("SELECT word, sum(count) FROM counts GROUP BY word")
print('\n'.join(cur.fetchall()))

