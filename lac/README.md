# Install
apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev redis-server libmysqlclient-dev mysql-server mysql-client

# Conf mysql
mysql -u root -p
CREATE DATABASE lac;
CREATE USER 'lac'@'localhost' IDENTIFIED BY '<LAC_PASS>';
GRANT ALL ON lac.* TO 'lac'@'localhost';


Create a virtualenv

pip install flask
pip install python-ldap
pip install flask-sqlalchemy
pip install flask-debugtoolbar
pip install flask-bootstrap
pip install wtforms
pip install python-dateutil
pip install pytz
pip install redis
