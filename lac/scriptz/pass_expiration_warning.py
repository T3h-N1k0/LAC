#!/usr/bin/python
# -*- coding: utf-8 -*
import ldap
import ldaphelper
from datetime import datetime, timedelta
from pytz import timezone
import pytz
import ConfigParser
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText



# Config
configParser = ConfigParser.RawConfigParser()
configFilePath = './script_config.ini'
configParser.read(configFilePath)


LDAP_HOST = configParser.get('Bind', 'host')
LDAP_PORT = configParser.get('Bind', 'ldap_port')
LDAP_SCHEMA = configParser.get('Bind', 'ldap_schema')
LDAP_SEARCH_BASE = configParser.get('Bind', 'ldap_search_base')
MAIL_SENDER = configParser.get('Mail', 'mail_sender')
SMTP_SERVER = configParser.get('Mail', 'smtp_server')
utc = pytz.utc # Used for generalizedtime to datetime conversion


def connect():
    conn = ldap.initialize('{0}://{1}:{2}'.format(
        LDAP_SCHEMA,
        LDAP_HOST,
        LDAP_PORT))

    conn.protocol_version = ldap.VERSION3
    conn.set_option( ldap.OPT_X_TLS_DEMAND, True )

    return conn


def anonymous_search(base_dn=None,
                     ldap_filter=None,
                     attributes=None,
                     scope=ldap.SCOPE_SUBTREE):
    if not base_dn:
        base_dn = LDAP_SEARCH_BASE
    try:
        conn = connect()
        conn.simple_bind_s("","")
        records = conn.search_s(
            base_dn, scope, ldap_filter, attributes
        )
        conn.unbind_s()
        return ldaphelper.get_search_results(records)

    except ldap.LDAPError as e:
        print(e)
    except Exception as e:
        print(e)

def get_all_accoutz():
    userz = []
    branchz_to_check = ['cines', 'soft', 'autre', 'admcines']
    for branch in branchz_to_check:
        userz.extend(get_branch_accountz(branch))
    return userz

# Retrieve accountz infoz for given branch
def get_branch_accountz(branch):
    """ Renvoi la liste des comptes avec leur dernier bind"""

    search_base = 'ou={0},ou=people,{1}'.format(
        branch,
        LDAP_SEARCH_BASE
    )
    retrieveAttributes = ['uid', 'pwdChangedTime', 'mail']
    accountz = anonymous_search(
        search_base,
        "uid=*",
        retrieveAttributes
    )
    return accountz

def get_user_pwd_policy(uid):
    ldap_filter = "(&(objectClass=posixAccount)(uid={0}))".format(uid)
    user = anonymous_search(
        ldap_filter=ldap_filter,
        attributes=['pwdPolicySubentry']
    )[0].get_attributes()
    if 'pwdPolicySubentry' in user:
        subentry_filter = '(entryDN={0})'.format(user['pwdPolicySubentry'][0])
    else:
        subentry_filter = '(&(objectClass=pwdPolicy)(cn=passwordDefault))'
    base_dn = 'ou=policies,ou=system,{0}'.format(LDAP_SEARCH_BASE)
    return anonymous_search(
        ldap_filter=subentry_filter,
        attributes=['*']
    )[0].get_attributes()


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

def send_mail(email_address, message):
    sender = MAIL_SENDER
    msg = MIMEMultipart()
    msg['Subject'] = "Expiration de votre mot de passe"
    msg['From'] = sender
    msg['To'] = email_address

    msg.attach(MIMEText(message.encode('utf-8'), 'plain', 'utf-8'))
    server = smtplib.SMTP(SMTP_SERVER)
    server.ehlo_or_helo_if_needed()
    server.sendmail(sender, email_address, msg.as_string())
    server.quit()

def check_user_pwd_expiration(user):
    user_attributez = user.get_attributes()
    user_ppolicy = get_user_pwd_policy(user_attributez['uid'][0])
    pwd_max_age = int(user_ppolicy['pwdMaxAge'][0])
    pwd_expire_warning = int(user_ppolicy['pwdExpireWarning'][0])
    email = user_attributez['mail'][0] if 'mail' in user_attributez else None
    if 'pwdChangedTime' in user_attributez:
        pwd_changed_time = user_attributez['pwdChangedTime'][0]
        pwd_changed_datetime = generalized_time_to_datetime(
            pwd_changed_time
        )
        delta = datetime.now() - pwd_changed_datetime
        delta_in_sec = int(delta.total_seconds())
        if delta_in_sec > pwd_max_age:
            message = u"Le compte {0} a expiré.\nVous pouvez le mettre à jour ici : https://lacv2.cines.fr".format(user_attributez['uid'][0])
            print(message)
#            print("mail : {0}".format(email))
            if email:
                send_mail(email, message)
        elif (pwd_max_age - delta_in_sec) < pwd_expire_warning:
            expiration_date = pwd_changed_datetime + timedelta(
                0,
                pwd_max_age
            )
            message = u"Le compte {0} va expirer le {1}.\nVous pouvez le mettre à jour ici : https://lacv2.cines.fr".format(
                user_attributez['uid'][0],
                expiration_date)
            print(message)
            if email:
                send_mail(email, message)
def warn_all_expired_accountz():
    userz = get_all_accoutz()
    for user in userz:
        check_user_pwd_expiration(user)
    print(len(userz))
if __name__ == '__main__':
    warn_all_expired_accountz()
