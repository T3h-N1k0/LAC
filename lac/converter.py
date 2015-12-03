from datetime import datetime, timedelta, date
import time
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz
import re

from flask import current_app, request, flash, render_template

utc = pytz.utc

class Converter(object):

    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['converter'] = self
        self.cache = app.extensions['cache']
        self.ldap = app.extensions['ldap']

        self.date_format = app.config['DATE_FORMAT']
        self.timezone = timezone(app.config['TIMEZONE'])
        self.text_fieldz = app.config['TEXT_FIELDTYPEZ']

    def to_display_mode(self, value, display_mode):
        if display_mode in  self.text_fieldz :
            return value.decode('utf-8')
        elif display_mode == 'Datetime' :
            return value.strftime(self.date_format)
        elif display_mode == 'Generalizedtime' :
            return self.generalized_time_to_datetime(value)
        elif display_mode == 'GIDNumber' :
            return self.cache.get_posix_group_cn_by_gid(value)
        elif display_mode == 'DaysNumber' :
            return self.days_number_to_datetime(value)

    def from_display_mode(self, value, display_mode):
        if value is None:
            return ''
        if display_mode in  self.text_fieldz :
            return value.encode('utf-8')
        elif display_mode == 'Generalizedtime' :
            return self.datetime_to_generalized_time(value).encode('utf-8')
        elif display_mode == 'DaysNumber' :
            return str(self.datetime_to_days_number(value)).encode('utf-8')
        else:
            return value.encode('utf-8')


    def generalized_time_to_datetime(self, generalized_time):
        if len(generalized_time) > 14:
            m = re.search('^\d{14}', generalized_time)
            generalized_time = '{0}Z'.format(m.group(0))
        created_datetime = datetime.strptime(
            generalized_time, "%Y%m%d%H%M%SZ"
        )
        created_datetime = utc.localize(created_datetime)
        created_datetime = created_datetime.astimezone(
            self.timezone
        )
        return created_datetime


    def datetime_to_generalized_time(self, da_datetime):
        return da_datetime.strftime("%Y%m%d%H%M%SZ")


    def generalized_time_sec_to_datetime(self, generalized_time):
        created_datetime = datetime.strptime(
            generalized_time, "%Y%m%d%H%M%S.%fZ"
        )
        created_datetime = utc.localize(created_datetime)
        created_datetime = created_datetime.astimezone(
            self.timezone
        )
        return created_datetime

    def datetime_to_generalized_time_sec(self, da_datetime):
        return da_datetime.strftime("%Y%m%d%H%M%S.%fZ")

    def datetime_to_timestamp(self, date):
        return str(int(time.mktime(
            datetime.strptime(str(date), "%Y-%m-%d").timetuple()
        )))


    def datetime_to_days_number(self, datetime):
        return (int(datetime.strftime("%s"))/86400)+1

    def days_number_to_datetime(self, nb):
        return datetime.fromtimestamp(
            # 86400 == nombre de secondes par jour
            int(nb) * 86400
        )
