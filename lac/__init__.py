# -*- coding: utf-8 -*-
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
# from flask_debugtoolbar import DebugToolbarExtension

__author__ = "Nicolas CHATELAIN"
__copyright__ = "Copyright 2014, Nicolas CHATELAIN @ CINES"
__license__ = "GPL"


app = Flask(__name__)

app.config.from_object('config')

app.config['SQLALCHEMY_BINDS'] = {
    'lac': app.config['LAC_DB_URI'],
    'otrs': app.config['OTRS_DB_URI'],
    'gescli': app.config['GESCLI_DB_URI'],
    'gescpt': app.config['GESCPT_DB_URI']

}
db = SQLAlchemy(app)

Bootstrap(app)


import lac.views
