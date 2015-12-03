# Install dependenciez
    apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev redis-server libmysqlclient-dev mysql-server mysql-client apache2

# Conf mysql
    mysql -u root -p
    CREATE DATABASE lac;
    CREATE USER 'lac'@'localhost' IDENTIFIED BY '<LAC_PASS>';
    GRANT ALL ON lac.* TO 'lac'@'localhost';


#Create a virtualenv
    pip install flask
    pip install python-ldap
    pip install flask-sqlalchemy
    pip install flask-debugtoolbar
    pip install flask-bootstrap
    pip install wtforms
    pip install python-dateutil
    pip install pytz
    pip install redis

# mod_wsgi for Apache
## Install
    git clone https://github.com/GrahamDumpleton/mod_wsgi
    cd mod_wsgi
    ./configure
    make
    sudo make install

## Add in apache configuration
    LoadModule wsgi_module modules/mod_wsgi.so

# Copy config files
    mkdir /var/www/lac
    cp ./default_configz/lac.wsgi /var/www/lac/
    cp ./default_configz/001-lac.conf /etc/apache2/sites-available/

# Edit ./configz

# RedHat subtilitiez
    Compile python2.7 with ./configure --enable-shared
    Compile mod_wsgi with ./configure --with-python=/usr/local/bin/python2.7
