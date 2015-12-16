# Web application for LDAP management based on Flask framework.


## Description

Modules used:
- SQLAlchemy ORM is used for mapping with databases.
- Bootstrap is used for display customization.
- WTForms is used to manipulate HTML Forms.
- python-ldap is used to communicate with LDAP server.
- Redis is used to cache some data retrieved from LDAP server.
- MySQL is used to store application specific data.

The code is split like this :
- data_modelz.py : data classes definition used by SQLAlchemy to retrieve data from MySQL databases
- formz.py : forms classes definition used by WTForms
- form_manager.py : class used to generate custom formz, set default form values and help manage WTForm formz
- cache.py : class use to cache data locally with Redis instead of querying multiple time LDAP server.
- converter.py : class used to help convert different time format dans custom form fieldz
- flask_ldap.py : class used to communicate with LDAP server
- engine.py : class used to perform CINES specific functionz.
- views.py : file used by Flask to define the views (URL) of the application
- helperz.py : file defining various helper functionz.
- templates/ : folder containing templates used by Flask views to render HTML pages
- static/ : folder containing display files (CSS/JavaScript/images/...)
- scriptz/ : folder containing standalone scriptz


## Installation

### Install dependenciez
    apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev redis-server libmysqlclient-dev mysql-server mysql-client apache2

### Conf mysql
    mysql -u root -p
    CREATE DATABASE lac;
    CREATE USER 'lac'@'localhost' IDENTIFIED BY '<LAC_PASS>';
    GRANT ALL ON lac.* TO 'lac'@'localhost';


### Create a virtualenv
    pip install flask
    pip install python-ldap
    pip install flask-sqlalchemy
    pip install flask-debugtoolbar
    pip install flask-bootstrap
    pip install wtforms
    pip install python-dateutil
    pip install pytz
    pip install redis

### mod_wsgi for Apache
#### Install
    git clone https://github.com/GrahamDumpleton/mod_wsgi
    cd mod_wsgi
    ./configure
    make
    sudo make install

#### Add in apache configuration
    LoadModule wsgi_module modules/mod_wsgi.so

### Copy config files
    mkdir /var/www/lac
    cp ./default_configz/lac.wsgi /var/www/lac/
    cp ./default_configz/001-lac.conf /etc/apache2/sites-available/

### RedHat subtilitiez
    Compile python2.7 with ./configure --enable-shared
    Compile mod_wsgi with ./configure --with-python=/usr/local/bin/python2.7
