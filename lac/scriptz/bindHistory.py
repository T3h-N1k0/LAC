#!/usr/bin/python
# -*- coding: utf-8 -*
import ldap
import ldaphelper
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, relationship, backref
from datetime import datetime, timedelta
from pytz import timezone
import pytz
import ConfigParser





# Config
configParser = ConfigParser.RawConfigParser()
configFilePath = './script_config.ini'
configParser.read(configFilePath)


LDAP_HOST = configParser.get('Bind', 'host')
LDAP_PORT = configParser.get('Bind', 'ldap_port')
LDAP_SCHEMA = configParser.get('Bind', 'ldap_schema')
LDAP_SEARCH_BASE = configParser.get('Bind', 'ldap_search_base')
LAC_DB_HOST = configParser.get('Bind', 'lac_db_host')
LAC_DB_USER = configParser.get('Bind', 'lac_db_user')
LAC_DB_PASS = configParser.get('Bind', 'lac_db_pass')



utc = pytz.utc # Used for generalizedtime to datetime conversion

# Database mapping configuration/definition
Base = declarative_base()
engine = create_engine(
    'mysql://{0}:{1}@{2}/lac'.format(LAC_DB_USER,
                                     LAC_DB_PASS,
                                     LAC_DB_HOST))
Session = sessionmaker(bind=engine)
session = Session()


class User(Base):
    __bind_key__ = 'lac'
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    uid =Column(String(200))
    uid_number = Column(Integer, unique=True)
    firstname = Column(String(200))
    lastname = Column(String(200))
    email = Column(String(200))
    phone_number = Column(String(20))
    binds = relationship('UserBind',
                            backref="user",
                            lazy='dynamic',
                            order_by='desc(UserBind.time)')

class UserBind(Base):
    __bind_key__ = 'lac'
    __tablename__ = 'userbind'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id',
                                               onupdate="CASCADE",
                                               ondelete="CASCADE"))
    time = Column(DateTime)


# Retrieve account infoz
def get_account():
    """ Renvoi la liste des comptes avec leur dernier bind"""
    try:
        conn = ldap.initialize('{0}://{1}:{2}'.format(
            LDAP_SCHEMA,
            LDAP_HOST,
            LDAP_PORT))

        conn.protocol_version = ldap.VERSION3
        conn.set_option( ldap.OPT_X_TLS_DEMAND, True )

        conn.simple_bind_s("","")

        retrieveAttributes = ['uid', 'authTimestamp', 'uidNumber']
        result = conn.search_st(
            LDAP_SEARCH_BASE, ldap.SCOPE_SUBTREE, 'uid=*', retrieveAttributes)
        conn.unbind_s()
        return result

    except ldap.LDAPError, e:
        print e



# Datetime conversion
def generalized_time_to_datetime(generalized_time):
    created_datetime = datetime.strptime(
        generalized_time, "%Y%m%d%H%M%SZ"
    )
    created_datetime = utc.localize(created_datetime)
    created_datetime = created_datetime.astimezone(
        timezone('Europe/Paris')
    )
    return created_datetime.replace(tzinfo=None)


# Add new bind if not already in database
def update_user_last_bind(uid_number, uid, bind_datetime):
    user = session.query(User).filter_by(uid_number=uid_number).first()
    # Create user if doesn't already exists
    if not user:
        user = User(uid_number=uid_number,
                    uid=uid)
        session.add(user)
    # Add bind if not already in database
    if bind_datetime not in [bind.time for bind in user.binds.all()]:
        new_bind = UserBind(
            user_id = user.id,
            time = bind_datetime)
        session.add(new_bind)
        if __debug__:
            print(u"Nouveau bind pour {0} : {1}.".format(user.uid,
                                                         bind_datetime))
    session.commit()


def update_all_user_last_bind():
    accountz = ldaphelper.get_search_results(
        get_account()
    )
    # Parsing all accountz retrieved
    for account in accountz:
        account_attrz = account.get_attributes()

        #  If user has a last bind we update it
        if 'authTimestamp' in account_attrz:
            bind_datetime = generalized_time_to_datetime(
                account_attrz['authTimestamp'][0])
            uid_number = account_attrz['uidNumber'][0]
            uid = account_attrz['uid'][0]
            update_user_last_bind(uid_number, uid, bind_datetime)


if __name__ == '__main__':
    update_all_user_last_bind()
