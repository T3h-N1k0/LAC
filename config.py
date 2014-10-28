### Put this in configuration file
#DATABASE = 'lac'
DEBUG = True
SECRET_KEY = 'development-key_omgwtfbbq'
#PGSQL_USERNAME = 'admin'
#USER = 'uid=chatelain,ou=cines,ou=people,dc=cines,dc=fr'
#PASSWORD = 'Sympalecines!'
# PGSQL_PASSWORD = 'omgwtfbbq'
LDAP_HOST = 'ldapone.cines.fr'
LDAP_SEARCH_BASE = 'dc=cines,dc=fr'
LDAP_LOGIN_VIEW = 'login'
LDAP_SUCCESS_REDIRECT = 'home'
LDAP_DOMAIN = 'ou=cines,ou=people,dc=cines,dc=fr'
ENCODING = 'utf-8'
TIMEZONE = 'Europe/Paris'
DATE_DISPLAY_FORMAT = '%Y-%m-%d %H:%M:%S %Z%z'
SQLALCHEMY_DATABASE_URI = 'mysql://lac:omgwtfbbq@localhost/lac'
PEOPLE_GROUPS = ['ccc', 'cines', 'deci', 'sam', 'autre', 'test', 'soft']
