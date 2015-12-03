import sys
sys.path.insert(0, '/path/to/code/lac/')
sys.path.insert(0, ':/path/to/virtualenv/lac/lib/python2.7/site-packages/')
import os
# activate virtualenv
activate_this = os.path.expanduser("/path/to/virtualenvs/lac/bin/activate_this.py")
execfile(activate_this, dict(__file__=activate_this))

from lac import app as application
