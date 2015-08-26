from datetime import datetime, timedelta, date


### Run !

from lac import app
app.debug = app.config['DEBUG']
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
#app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(day=2)
# toolbar = DebugToolbarExtension(app)
#decoder = PythonLDAPDecoder(app.config['ENCODING'])
app.run(host='0.0.0.0')
