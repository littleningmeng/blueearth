# -*- coding: utf-8 -*-
from flask import Flask, render_template
from views.wx import wx

app = Flask(__name__)
app.register_blueprint(wx, "/wx")


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
