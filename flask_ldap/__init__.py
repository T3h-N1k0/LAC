# coding=utf-8
# -*- coding: utf-8 -*-
import os

__author__ = "Nicolas CHATELAIN"
__copyright__ = "Copyright 2014, Nicolas CHATELAIN @ CINES"
__license__ = "GPL"

from functools import wraps
from string import capwords

import ldap
from flask import current_app, request, flash, render_template
import ldaphelper

# Find the stack on which we want to store the database connection.
# Starting with Flask 0.9, the _app_ctx_stack is the correct one,
# before that we need to use the _request_ctx_stack.
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack
from flask import session, redirect, url_for


class LDAP(object):
    def __init__(self, app=None, mongo=None):
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        app.config.setdefault('LDAP_HOST', '127.0.0.1')
        app.config.setdefault('LDAP_PORT', 389)
        app.config.setdefault('LDAP_SCHEMA', 'ldap')
        app.config.setdefault('LDAP_DOMAIN', 'ou=cines,ou=people,dc=cines,dc=fr')
        app.config.setdefault('LDAP_LOGIN_VIEW', 'login')
        app.config.setdefault('LDAP_SEARCH_BASE', 'OU=Users,DC=example,DC=com')
        app.config.setdefault('LDAP_LOGIN_TEMPLATE', 'login.html')
        app.config.setdefault('LDAP_SUCCESS_REDIRECT', 'test_ldap')
        app.config.setdefault('LDAP_PROFILE_KEY', 'sAMAccountName')
        # Use the newstyle teardown_appcontext if it's available,
        # otherwise fall back to the request context
        if hasattr(app, 'teardown_appcontext'):
            app.teardown_appcontext(self.teardown)
        else:
            app.teardown_request(self.teardown)

        self.login_func = app.config['LDAP_LOGIN_VIEW']

    def connect(self):
        # print('LDAP_SCHEMA {0}'.format(self.app.config['LDAP_SCHEMA']))
        # print('LDAP_PORT {0}'.format(self.app.config['LDAP_PORT']))
        # print('LDAP_HOST {0}'.format(self.app.config['LDAP_HOST']))
        self.conn = ldap.initialize('{0}://{1}:{2}'.format(
            self.app.config['LDAP_SCHEMA'],
            self.app.config['LDAP_HOST'],
            self.app.config['LDAP_PORT']))
        self.conn.set_option(ldap.OPT_REFERRALS, 0)
        return self.conn

    def teardown(self, exception):
        ctx = stack.top
        if hasattr(ctx, 'ldap_host'):
            ctx.ldap_host.close()


    def anonymous_search(self,
                         base_dn=None,
                         filter=None,
                         attributes=None,
                         scope=ldap.SCOPE_SUBTREE):
        try:
            if base_dn==None:
                base_dn=self.app.config['LDAP_SEARCH_BASE']
            self.connect()
            # print(base_dn)
            # print(attributes)
            self.conn.simple_bind_s("","")
            records = self.conn.search_s(base_dn, scope, filter, attributes)
            self.conn.unbind_s()
            return records

        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            return self.other_err(e)


    def admin_search(self,
               base_dn=None,
               ldap_filter=None,
               attributes=None,
               scope=ldap.SCOPE_SUBTREE):

        if base_dn==None:
            base_dn=self.app.config['LDAP_SEARCH_BASE']

        dn = self.get_full_dn_from_uid(self.app.config['LAC_ADMIN_USER'])
        try:
            self.connect()

            self.conn.simple_bind_s(dn,
                                    self.app.config['LAC_ADMIN_PASS'])

            records = self.conn.search_s(base_dn,
                                         scope,
                                         ldap_filter,
                                         attributes)
            self.conn.unbind_s()
            #print('recordz {0}'.format(records))
            return records

        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            print('error : {0}'.format(e))
            return self.other_err(e)


    def search(self,
               base_dn=None,
               ldap_filter='',
               attributes=None,
               scope=ldap.SCOPE_SUBTREE):
        try:
            if base_dn==None:
                base_dn=self.app.config['LDAP_SEARCH_BASE']
            # print("ldap_filter : {0}".format(ldap_filter))
            self.connect()
            self.conn.simple_bind_s(session['user_dn'], session['password'])
            records = self.conn.search_s(base_dn, scope, ldap_filter, attributes)
            self.conn.unbind_s()
            return records

        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            return self.other_err(e)
            print(e)
    def change_passwd(self, uid, old_pass, new_pass):
        try:
            dn = self.get_full_dn_from_uid(uid)
            self.connect()
            self.conn.simple_bind_s(session['user_dn'], session['password'])
            self.conn.passwd_s(dn, old_pass, new_pass)
            if session['uid'] == uid:
                session['password'] = new_pass
        except ldap.LDAPError as e:
            return self.ldap_err(e)
        except Exception as e:
            return self.other_err(e)


    def ldap_login(self, username, pwd):
        try:
            user_dn = self.get_full_dn_from_uid(username)
            self.connect()
            self.conn.set_option(ldap.OPT_REFERRALS, 0)
            self.conn.simple_bind_s(user_dn, pwd.encode('utf8'))
            self.conn.unbind_s()
            session['user_dn'] = user_dn
            session['uid'] = username
            session['password'] = pwd.encode('utf8')
            session['logged_in'] = True
            session['admin'] = self.is_lac_admin(username)
            return True

        except ldap.LDAPError as e:
            return self.ldap_err(e)
        except Exception as e:
            print(e)
            return self.other_err(e)

    def is_lac_admin(self, uid):
        if self.get_full_dn_from_uid(uid) in self.get_lac_admin_memberz():
            return True
        else:
            return False

    def get_full_dn_from_cn(self, cn):
        filter='(cn={0})'.format(cn)
        if 'logged_in' in session:
            result = self.search(ldap_filter=filter)
        else:
            result = self.anonymous_search(filter=filter)
        return result[0][0]

    def get_full_dn_from_uid(self, uid):
        # print('uid {0}'.format(uid))
        filter='(uid={0})'.format(uid)
        # print(filter)
        # if 'logged_in' in session:
        #     result = self.search(ldap_filter=filter)
        # else:
        result = self.anonymous_search(filter=filter)
        return result[0][0] if result else None

    # def get_ldap_admin_memberz(self):
    #     ldap_filter='(cn=ldapadmin)'
    #     attributes=['member']
    #     raw_resultz = ldaphelper.get_search_results(
    #         self.admin_search(ldap_filter=ldap_filter,attributes=attributes)
    #     )
    #     memberz = raw_resultz[0].get_attributes()['member']
    #     print("memberz {0}".format(memberz))
    #     return memberz

    def get_lac_admin_memberz(self):
        ldap_filter='(cn=lacadmin)'
        attributes=['member']
        raw_resultz = ldaphelper.get_search_results(
            self.admin_search(ldap_filter=ldap_filter,attributes=attributes)
        )
        memberz = raw_resultz[0].get_attributes()['member']
        return memberz


    def update_uid_attribute(self, uid, pre_modlist):
        dn = self.get_full_dn_from_uid(uid)
        mod_attrs = [(ldap.MOD_REPLACE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)
        # try:
        #     self.connect()
        #     self.conn.simple_bind_s(session['user_dn'], session['password'])
        #     self.conn.modify_s(dn, mod_attrs)
        #     self.conn.unbind_s()

        # except ldap.LDAPError as e:
        #     print(e)
        #     return self.ldap_err(e)
        # except Exception as e:
        #     print(e)
        #     return self.other_err(e)

    def add_uid_attribute(self, uid, pre_modlist):
        dn = self.get_full_dn_from_uid(uid)
        mod_attrs = [(ldap.MOD_ADD, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)
        # try:
        #     self.connect()
        #     self.conn.simple_bind_s(session['user_dn'], session['password'])
        #     self.conn.modify_s(dn, mod_attrs)
        #     self.conn.unbind_s()

        # except ldap.LDAPError as e:
        #     print(e)
        #     return self.ldap_err(e)
        # except Exception as e:
        #     print(e)
        #     return self.other_err(e)

    def add_cn_attribute(self, cn, pre_modlist):
        dn = self.get_full_dn_from_cn(cn)
        mod_attrs = [(ldap.MOD_ADD, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)
        # try:
        #     self.connect()
        #     self.conn.simple_bind_s(session['user_dn'], session['password'])
        #     print('modify_s({0}, {1})'.format(dn,mod_attrs))
        #     self.conn.modify_s(dn, mod_attrs)
        #     self.conn.unbind_s()

        # except ldap.LDAPError as e:
        #     print(e)
        #     return self.ldap_err(e)
        # except Exception as e:
        #     print(e)
        #     return self.other_err(e)

    def add_dn_attribute(self, dn, pre_modlist):
        mod_attrs = [(ldap.MOD_ADD, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)


    def remove_uid_attribute(self, uid, pre_modlist):
        dn = self.get_full_dn_from_uid(uid)
        mod_attrs = [(ldap.MOD_DELETE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)
        # try:
        #     self.connect()
        #     self.conn.simple_bind_s(session['user_dn'], session['password'])
        #     print('modify_s({0}, {1})'.format(dn,mod_attrs[0]))
        #     self.conn.modify_s(dn, mod_attrs)
        #     self.conn.unbind_s()

        # except ldap.LDAPError as e:
        #     print(e)
        #     return self.ldap_err(e)
        # except Exception as e:
        #     print(e)
        #     return self.other_err(e)

    def remove_cn_attribute(self, cn, pre_modlist):
        dn = self.get_full_dn_from_cn(cn)
        mod_attrs = [(ldap.MOD_DELETE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)
        # try:
        #     self.connect()
        #     self.conn.simple_bind_s(session['user_dn'], session['password'])
        #     print('modify_s({0}, {1})'.format(dn,mod_attrs[0]))
        #     self.conn.modify_s(dn, mod_attrs)
        #     self.conn.unbind_s()

        # except ldap.LDAPError as e:
        #     print(e)
        #     return self.ldap_err(e)
        # except Exception as e:
        #     print(e)
        #     return self.other_err(e)

    def remove_dn_attribute(self, dn, pre_modlist):
        mod_attrs = [(ldap.MOD_DELETE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)

    def update_cn_attribute(self, cn, pre_modlist):
        dn = self.get_full_dn_from_cn(cn)
        mod_attrs = [(ldap.MOD_REPLACE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)

    def generic_modify(self, dn, mod_attrs):
        try:
            self.connect()
            self.conn.simple_bind_s(session['user_dn'], session['password'])
            print('modify_s({0}, {1})'.format(dn,mod_attrs))
            self.conn.modify_s(dn, mod_attrs)
            self.conn.unbind_s()

        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            print(e)
            return self.other_err(e)

    def add(self, dn, add_record):
        try:
            self.connect()
            self.conn.simple_bind_s(session['user_dn'], session['password'])
            print('add_s({0}, {1})'.format(dn,add_record))
            self.conn.add_s(dn, add_record)
            self.conn.unbind_s()
            return True
        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            print(e)
            return self.other_err(e)

    def delete(self, dn):
        try:
            self.connect()
            self.conn.simple_bind_s(session['user_dn'], session['password'])
            print('delete_s({0})'.format(dn))
            self.conn.delete_s(dn)
            self.conn.unbind_s()
            return True
        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            print(e)
            return self.other_err(e)



    def login(self):
        """
        View function for rendering and logic for auth form

        :return:
        """
        if request.method == 'POST':
            if "username" in request.form and "password" in request.form:
                if self.ldap_login(request.form['username'], request.form['password']):
#                    for i in self.mu.keys():
#                        session[i] = self.mu[i]
                    return redirect(url_for(self.app.config['LDAP_SUCCESS_REDIRECT']))
                else:
                    return render_template(self.app.config['LDAP_LOGIN_TEMPLATE'])
        if 'logged_in' in session:
            flash(u"Vous êtes déjà authentifé en tant que {0}".format(session['user_dn']))
        return render_template(self.app.config['LDAP_LOGIN_TEMPLATE'])


    def ldap_err(self, exc):
        flash(message=dict(exc.message), category='error')
        return False

    def other_err(self, exc):
        flash(message=exc.message, category='error')
        return False

    @property
    def connection(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'ldap_host'):
                ctx.ldap_host = self.connect()
            return ctx.ldap_host

    def logout(self):
        session.pop('logged_in', None)
        flash(u"Vous êtes à présent déconnecté")
        return redirect(url_for('login'))


def login_required(f):
    """
    Decorator for views that require login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        return redirect(url_for(current_app.config['LDAP_LOGIN_VIEW']))

    return decorated

def admin_login_required(f):
    """
    Decorator for views that require login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin' in session:
            return f(*args, **kwargs)
        flash(u'Espace réservé aux admins')
        return redirect(url_for('home'))

    return decorated
