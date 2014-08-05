import sqlite3

from flask import Flask, render_template, g
app = Flask(__name__)

DATABASE = 'data.sqlite'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/<classname>')
def show_class_info(classname):
    # show the user profile for that user
    cur = get_db().cursor()
    cur.execute("SELECT count(word) FROM counts WHERE word = :name", dict(name=classname))
    count = cur.fetchone()[0]
    cur.execute("SELECT context FROM counts WHERE word = :name", dict(name=classname))
    snippets = [row[0] for row in cur.fetchall()]
    return render_template('classinfo.html', name=classname, count=count, snippets=snippets)

@app.route('/')
def hello_world():
    cur = get_db().cursor()
    print(cur)
    cur.execute("SELECT word, count(word) FROM counts GROUP BY word ORDER BY count(word) DESC")
    classes = []
    for row in cur.fetchall():
        word, count = row[0], row[1]
        classobj = dict(name=word,
                        count=count)
        classes.append(classobj)

    classes
    return render_template('classlist.html', classes=classes)

def run_server(db_instance):
    app.run(debug=True)
