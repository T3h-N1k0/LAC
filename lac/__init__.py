# -*- coding: utf-8 -*-
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response
from flask.ext.sqlalchemy import SQLAlchemy
# from flask_debugtoolbar import DebugToolbarExtension
from werkzeug import secure_filename
from flask_bootstrap import Bootstrap
from sqlalchemy import Table, Column, Integer, ForeignKey, func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from wtforms import Form, BooleanField, TextField, SelectMultipleField, SelectField, PasswordField,validators, FormField, FieldList, DateField, TextAreaField
from datetime import datetime, timedelta, date
import time
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz
import ldaphelper
#import upsert
from ldap_decoder import PythonLDAPDecoder
from ldap import SCOPE_BASE,schema
import hashlib,binascii
import re
import os
# from data_modelz import *
# Custom modulez

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
