# coding=utf-8
# -*- coding: utf-8 -*-
import os
import re
from functools import wraps
from string import capwords
import ldap
from flask import current_app, request, flash, render_template
import ldaphelper

__author__ = "Nicolas CHATELAIN"
__copyright__ = "Copyright 2014, Nicolas CHATELAIN @ CINES"
__license__ = "GPL"


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
        app.config.setdefault('LDAP_PORT', 636)
        app.config.setdefault('LDAP_SCHEMA', 'ldaps')
        app.config.setdefault('LDAP_DOMAIN', 'ou=cines,ou=people,dc=cines,dc=fr')
        app.config.setdefault('LDAP_LOGIN_VIEW', 'login')
        app.config.setdefault('LDAP_SEARCH_BASE', 'dc=cines,dc=fr')
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
        self.ldap_search_base = app.config['LDAP_SEARCH_BASE']
        if not hasattr(app, 'extensions'):
            app.extensions = {}

        app.extensions['ldap'] = self

    def connect(self):
        self.conn = ldap.initialize('{0}://{1}:{2}'.format(
            self.app.config['LDAP_SCHEMA'],
            self.app.config['LDAP_HOST'],
            self.app.config['LDAP_PORT']))

        self.conn.protocol_version = ldap.VERSION3
        self.conn.set_option( ldap.OPT_X_TLS_DEMAND, True )

        return self.conn

    def teardown(self, exception):
        ctx = stack.top
        if hasattr(ctx, 'ldap_host'):
            ctx.ldap_host.close()


    def anonymous_search(self,
                         base_dn=None,
                         ldap_filter=None,
                         attributes=None,
                         scope=ldap.SCOPE_SUBTREE):
        if not base_dn:
            base_dn = self.ldap_search_base
        try:
            self.connect()
            self.conn.simple_bind_s("","")
            records = self.conn.search_s(
                base_dn, scope, ldap_filter, attributes
            )
            self.conn.unbind_s()
            return ldaphelper.get_search_results(records)

        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            return self.other_err(e)


    # def admin_search(self,
    #            base_dn=self.app.config['LDAP_SEARCH_BASE'],
    #            ldap_filter=None,
    #            attributes=None,
    #            scope=ldap.SCOPE_SUBTREE):

    #     dn = self.get_full_dn_from_uid(self.app.config['LAC_ADMIN_USER'])
    #     try:
    #         self.connect()

    #         self.conn.simple_bind_s(dn,
    #                                 self.app.config['LAC_ADMIN_PASS'])

    #         records = self.conn.search_s(base_dn,
    #                                      scope,
    #                                      ldap_filter,
    #                                      attributes)
    #         self.conn.unbind_s()
    #         if records:
    #             return ldaphelper.get_search_results(records)
    #         else:
    #             return None

    #     except ldap.LDAPError as e:
    #         print(e)
    #         return self.ldap_err(e)
    #     except Exception as e:
    #         print('error : {0}'.format(e))
    #         return self.other_err(e)


    def search(self,
               base_dn=None,
               ldap_filter='',
               attributes=None,
               scope=ldap.SCOPE_SUBTREE):
        if not base_dn:
            base_dn = self.ldap_search_base
        try:
            self.connect()
            self.conn.simple_bind_s(session['user_dn'], session['password'])
            records = self.conn.search_s(base_dn, scope, ldap_filter, attributes)
            self.conn.unbind_s()
            if records:
                return ldaphelper.get_search_results(records)
            else:
                return None
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
            session['admin'] = self.is_ldap_admin(username)
            session['lac_admin'] = self.is_lac_admin(username)
            return True

        except ldap.LDAPError as e:
            return self.ldap_err(e)
        except Exception as e:
            print(e)
            return self.other_err(e)

    def is_lac_admin(self, uid):
        try:
            if self.get_full_dn_from_uid(uid) in self.get_lac_admin_memberz():
                return True
        except Exception as e:
            print(e)
            return False

    def is_ldap_admin(self, uid):

        try:
            if self.get_full_dn_from_uid(uid) in self.get_ldap_admin_memberz():
                return True
        except Exception as e:
            print(e)
            return False

    def get_full_dn_from_cn(self, cn):
        filter='(cn={0})'.format(cn)
        if 'logged_in' in session:
            result = self.search(ldap_filter=filter)
        else:
            result = self.anonymous_search(ldap_filter=filter)
        return result[0].get_dn() if result else None

    def get_full_dn_from_uid(self, uid):
        filter='(uid={0})'.format(uid)
        result = self.anonymous_search(ldap_filter=filter)
        return result[0].get_dn() if result else None

    def get_ldap_admin_memberz(self):
        ldap_filter='(cn=ldapadmin)'
        attributes=['member']
        resultz = self.search(ldap_filter=ldap_filter,attributes=attributes)
        memberz = resultz[0].get_attributes()['member']
        return memberz

    def get_lac_admin_memberz(self):
        ldap_filter='(cn=lacadmin)'
        attributes=['member']
        raw_resultz = self.search(ldap_filter=ldap_filter,attributes=attributes)
        memberz = raw_resultz[0].get_attributes()['member']
        return memberz


    def update_uid_attribute(self, uid, pre_modlist):
        dn = self.get_full_dn_from_uid(uid)
        mod_attrs = [(ldap.MOD_REPLACE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)

    def add_uid_attribute(self, uid, pre_modlist):
        dn = self.get_full_dn_from_uid(uid)
        mod_attrs = [(ldap.MOD_ADD, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)

    # def add_cn_attribute(self, cn, pre_modlist):
    #     dn = self.get_full_dn_from_cn(cn)
    #     mod_attrs = [(ldap.MOD_ADD, name, values)
    #                  for name, values in pre_modlist]
    #     self.generic_modify(dn, mod_attrs)

    def add_dn_attribute(self, dn, pre_modlist):
        mod_attrs = [(ldap.MOD_ADD, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)


    def remove_uid_attribute(self, uid, pre_modlist):
        dn = self.get_full_dn_from_uid(uid)
        mod_attrs = [(ldap.MOD_DELETE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)

    # def remove_cn_attribute(self, cn, pre_modlist):
    #     dn = self.get_full_dn_from_cn(cn)
    #     mod_attrs = [(ldap.MOD_DELETE, name, values)
    #                  for name, values in pre_modlist]
    #     self.generic_modify(dn, mod_attrs)

    def remove_dn_attribute(self, dn, pre_modlist):
        mod_attrs = [(ldap.MOD_DELETE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)

    # def update_cn_attribute(self, cn, pre_modlist):
    #     dn = self.get_full_dn_from_cn(cn)
    #     mod_attrs = [(ldap.MOD_REPLACE, name, values)
    #                  for name, values in pre_modlist]
    #     self.generic_modify(dn, mod_attrs)

    def update_dn_attribute(self, dn, pre_modlist):
        mod_attrs = [(ldap.MOD_REPLACE, name, values)
                     for name, values in pre_modlist]
        self.generic_modify(dn, mod_attrs)

    def generic_modify(self, dn, mod_attrs):
        try:
            self.connect()
            self.conn.simple_bind_s(session['user_dn'], session['password'])
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
            self.conn.delete_s(dn)
            self.conn.unbind_s()
            return True
        except ldap.LDAPError as e:
            print(e)
            return self.ldap_err(e)
        except Exception as e:
            print(e)
            return self.other_err(e)

    def is_cines_account(self, username):
        ldap_filter = '(&(objectClass=cinesusr)(uid={0}))'.format(username)
        base_dn='ou=cines,ou=people,{0}'.format(self.ldap_search_base)
        raw_result = self.anonymous_search(
            ldap_filter=ldap_filter,
            base_dn=base_dn)
        return False if not raw_result else True

    def is_cinesadmin_account(self, username):
        ldap_filter = '(uid={0})'.format(username)
        base_dn='ou=Admcines,ou=people,{0}'.format(self.ldap_search_base)
        raw_result = self.anonymous_search(
            ldap_filter=ldap_filter,
            base_dn=base_dn)
        return False if not raw_result else True

    def login(self):
        """
        View function for rendering and logic for auth form

        :return:
        """
        if request.method == 'POST':
            if "username" in request.form and "password" in request.form:
                if not (self.is_cines_account(request.form['username'])
                        or self.is_cinesadmin_account(request.form['username'])):
                    flash(u'Seuls les comptes CINES sont autorisés à se connecter à LAC')
                    return render_template(self.app.config['LDAP_LOGIN_TEMPLATE'])
                elif self.ldap_login(request.form['username'], request.form['password']):
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
        session.pop('admin', None)
        session.pop('password', None)
        session.pop('lac_admin', None)
        session.pop('logged_in', None)
        flash(u"Vous êtes à présent déconnecté")
        return redirect(url_for('login'))

    def get_uid_logz(self, uid):
        dn = self.get_full_dn_from_uid(uid)
        ldap_filter="(&(objectClass=auditModify)(reqDN={0}))".format(dn)
        attributes=['*']
        base_dn=self.app.config['LDAP_LOG_BASE']
        return self.search(base_dn,ldap_filter,attributes)

    def get_default_storage_list(self):
        ldap_filter='(objectClass=cinesQuota)'
        attributes=['cn']
        base_dn='ou=quota,ou=system,{0}'.format(self.ldap_search_base)
        storagez = self.search(base_dn,ldap_filter,attributes)
        if storagez:
            return storagez
        else:
            return []


    def get_group_quota_list(self):
        ldap_filter='(objectClass=cinesQuota)'
        attributes=['cn']
        base_dn='ou=groupePosix,{0}'.format(self.ldap_search_base)
        quotaz = self.search(base_dn,ldap_filter,attributes)
        if quotaz:
            return quotaz
        else:
            return []


    def get_default_storage(self, cn):
        ldap_filter='(&(objectClass=cinesQuota)(cn={0}))'.format(cn)
        attributes=['*']
        base_dn='ou=quota,ou=system,{0}'.format(self.ldap_search_base)
        return self.search(base_dn,ldap_filter,attributes)[0]

    def get_storage(self, cn):
        ldap_filter='(&(objectClass=cinesQuota)(cn={0}))'.format(cn)
        attributes=['*']
        base_dn='ou=groupePosix,{0}'.format(self.ldap_search_base)
        return self.search(base_dn,ldap_filter,attributes)[0]

    def get_sambasid_prefix(self):
        base_dn = self.ldap_search_base
        ldap_filter='(sambaDomainName={0})'.format(
            self.app.config['SAMBA_DOMAIN_NAME']
        )
        attributes=['sambaSID']
        sambasid_prefix = self.search(base_dn,
                           ldap_filter,
                           attributes)[0].get_attributes()['sambaSID'][0]
        return sambasid_prefix

    def get_posix_group_memberz(self, branch, cn):
        """
        List memberz of a group inherited from people ou
        """
        ldap_filter='(cn={0})'.format(cn)
        attributes=['memberUid', "entryDN"]
        base_dn='ou={0},ou=groupePosix,{1}'.format(
            branch,
            self.ldap_search_base
        )
        group = self.search(base_dn,ldap_filter,attributes)[0]
        group_attrz= group.get_attributes()
        if 'memberUid' in group_attrz:
            memberz = group_attrz['memberUid']
        else:
            memberz = []
        return memberz

    def get_posix_group_principal_memberz_from_gid(self, gid_number):
        ldap_filter='(&(gidNumber={0})(objectClass=posixAccount))'.format(
            gid_number
        )
        attributes=["uid", "entryDN"]
        base_dn='ou=people,{0}'.format(self.ldap_search_base)
        memberz = self.search(base_dn,ldap_filter,attributes)
        if memberz:
            memberz_dn = sorted([member.get_attributes()['uid'][0]
                                 for member in memberz])
        else:
            memberz_dn = []
        return memberz_dn


    def get_posix_groupz_from_member_uid(self, uid):
        ldap_filter='(&(objectClass=posixGroup)(memberUid={0}))'.format(uid)
        attributes=['cn', 'entryDN']
        base_dn='ou=groupePosix,{0}'.format(self.ldap_search_base)
        groupz_obj = self.search(base_dn,ldap_filter,attributes)
        groupz = []
        if groupz_obj:
            for group in groupz_obj:
                group_attrz = group.get_attributes()
                cn = group_attrz['cn'][0]
                dn = group_attrz['entryDN'][0]
                branch = self.get_branch_from_posix_group_dn(dn)
                groupz.append((cn, branch))
        return groupz

    def get_branch_from_posix_group_gidnumber(self, id):
        ldap_filter='(&(objectClass=posixGroup)(gidNumber={0}))'.format(id)
        attributes=['entryDN']
        base_dn='ou=groupePosix,{0}'.format(self.ldap_search_base)
        group = self.search(base_dn,ldap_filter,attributes)[0]
        return self.get_branch_from_posix_group_dn(
            group.get_attributes()['entryDN'][0]
        )

    def get_work_groupz_from_member_uid(self, uid):
        dn = self.get_full_dn_from_uid(uid)
        ldap_filter='(&(objectClass=cinesGrWork)(uniqueMember={0}))'.format(dn)
        attributes=['cn']
        base_dn='ou=grTravail,{0}'.format(self.ldap_search_base)
        groupz_obj = self.search(base_dn,ldap_filter,attributes)
        groupz = []
        if groupz_obj:
            for group in groupz_obj:
                groupz.append(group.get_attributes()['cn'][0])
        return groupz

    def get_wrk_group_dn_from_cn(self, cn):
        ldap_filter='(&(objectClass=cinesGrWork)(cn={0}))'.format(cn)
        attributes = ['entryDN']
        base_dn='ou=grTravail,{0}'.format(self.ldap_search_base)
        group_obj = self.search(base_dn,ldap_filter,attributes)[0]
        dn = group_obj.get_attributes()['entryDN'][0]
        return dn

    def get_people_group_dn_from_cn(self, cn):
        ldap_filter='(&(objectClass=posixGroup)(cn={0}))'.format(cn)
        attributes = ['entryDN']
        base_dn='ou=groupePosix,{0}'.format(self.ldap_search_base)
        result = self.search(base_dn,ldap_filter,attributes)
        if result:
            group_obj = result[0]
            dn = group_obj.get_attributes()['entryDN'][0]
        else:
            dn = None
            flash(u'Groupe non touvé')
        return dn

    def get_people_dn_from_ou(self, ou):
        ldap_filter='(ou={0})'.format(ou)
        attributes=['entryDN']
        base_dn='ou=people,{0}'.format(self.ldap_search_base)
        records = self.search(base_dn,ldap_filter,attributes)
        full_dn = records[0].get_attributes()['entryDN'][0]
        return full_dn

    def get_people_group_memberz(self, group):
        """
        List memberz of a group inherited from people ou
        """
        ldap_filter='(objectclass=inetOrgPerson)'
        attributes=['uid']
        base_dn='ou={0},ou=people,{1}'.format(group,
                                              self.ldap_search_base)
        records = self.anonymous_search(base_dn,ldap_filter,attributes)
        if records:
            return sorted(
                [member.get_attributes()['uid'][0]
                 for member in records]
            )
        else:
            return None

    def get_workgroup_memberz(self, group):
        """
        List memberz of a group inherited from grTravail ou
        """
        ldap_filter='(objectclass=cinesGrWork)'
        attributes=['uniqueMember']
        base_dn='cn={0},ou=grTravail,{1}'.format(
            group,
            self.ldap_search_base
        )
        records = self.anonymous_search(base_dn,ldap_filter,attributes)
        memberz = []
        for member in records:
            memberz.extend(member.get_attributes()['uniqueMember'])
        return memberz

    def get_group_full_dn(self, branch, cn):
        ldap_filter='(objectclass=posixGroup)'
        attributes=['entryDN']
        base_dn='cn={0},ou={1},ou=groupePosix,{2}'.format(
            cn,
            branch,
            self.ldap_search_base
        )
        resultz = self.anonymous_search(base_dn,ldap_filter,attributes)
        return resultz[0].get_attributes()['entryDN'][0]

    def get_group_branch(self, account_type):
        for branch in self.app.config['BRANCHZ']:
            if branch['account'] == account_type:
                return branch['group']

    def get_posix_groupz(self, branch=None):
        ldap_filter = "(objectClass=posixGroup)"
        base_dn = 'ou=groupePosix,{0}'.format(self.ldap_search_base)
        if branch:
            base_dn = ''.join(['ou={0},'.format(branch), base_dn])
        return self.anonymous_search(base_dn=base_dn,
                                  ldap_filter=ldap_filter,
                                  attributes=['cn', 'gidNumber'])

    def get_work_groupz(self):
        ldap_filter = "(objectClass=cinesGrWork)"
        base_dn = 'ou=grTravail,{0}'.format(self.ldap_search_base)
        groupz = self.anonymous_search(base_dn=base_dn,
                                  ldap_filter=ldap_filter,
                                  attributes=['cn'])
        return [group.get_attributes()['cn'][0] for group in groupz]


    def get_branch_from_posix_group_dn(self, dn):
        search_pattern = "cn=(.+?),ou=(.+?),"
        m = re.search(search_pattern, dn)
        if m:
            return m.group(2)
        else:
            return ''


    def get_submission_groupz_list(self):
        ldap_filter = "(&(objectClass=cinesGrWork)(cinesGrWorkType=1))"
        ldap_groupz = self.anonymous_search(ldap_filter=ldap_filter,
                             attributes=['cn'])
        ldap_groupz_list = []
        for group in ldap_groupz:
            group_attrz = group.get_attributes()
            name = group_attrz['cn'][0]
            ldap_groupz_list.append(name)
        return ldap_groupz_list

    def get_all_users(self):
        base_dn = "ou=people,{0}".format(self.ldap_search_base)
        ldap_filter='(objectclass=inetOrgPerson)'
        attributes=['*','+']
        userz = self.search(ldap_filter=ldap_filter,
                             attributes=attributes,
                             base_dn=base_dn)
        return userz

    def get_all_users_uid(self):
        base_dn = "ou=people,{0}".format(self.ldap_search_base)
        ldap_filter='(objectclass=inetOrgPerson)'
        attributes=['uid']
        userz = self.search(ldap_filter=ldap_filter,
                             attributes=attributes,
                             base_dn=base_dn)
        return sorted(
            [user.get_attributes()['uid'][0]
             for user in userz]
        )

    def get_all_groups(self):
        base_dn = "{0}".format(self.ldap_search_base)
        ldap_filter='(objectclass=posixGroup)'
        attributes=['*','+']
        return self.search(ldap_filter=ldap_filter,
                        attributes=attributes,
                        base_dn=base_dn)

    def get_all_ppolicies(self):
        base_dn = "ou=policies,ou=system,{0}".format(self.ldap_search_base)
        ldap_filter='(objectclass=pwdPolicy)'
        attributes=['*','+']
        return self.search(ldap_filter=ldap_filter,
                             attributes=attributes,
                             base_dn=base_dn)

    def get_ppolicy(self, ppolicy_label):
        base_dn = "ou=policies,ou=system,{0}".format(self.ldap_search_base)
        ldap_filter='(&(objectclass=pwdPolicy)(cn={0}))'.format(ppolicy_label)
        attributes=['*','+']
        return self.search(ldap_filter=ldap_filter,
                             attributes=attributes,
                             base_dn=base_dn)[0]

    def get_subschema(self):
        ldap_filter='(objectclass=*)'
        base_dn='cn=subschema'
        attributes=['*','+']
        scope=SCOPE_BASE
        subschema_subentry = self.search(ldap_filter=ldap_filter,
                                      base_dn=base_dn,
                                      attributes=attributes,
                                      scope=scope)[0].get_attributes()
        return schema.subentry.SubSchema( subschema_subentry )

    def set_submission(self, uid, group, state):
        old_cines_soumission = self.search(
                ldap_filter='(uid={0})'.format(uid),
                attributes=['cinesSoumission']
            )[0].get_attributes()['cinesSoumission'][0]
        if group in old_cines_soumission:
            new_cines_soumission = re.sub(r'(.*{0}=)\d(.*)'.format(group),
                                      r"\g<1>{0}\2".format(str(state)),
                                      old_cines_soumission)
        else:
            new_cines_soumission = "{0}{1}={2};".format(old_cines_soumission,
                                                        group,
                                                        state)
        pre_modlist = [('cinesSoumission', new_cines_soumission)]
        self.update_uid_attribute(uid, pre_modlist)
        flash(u'Soumission mis à jour pour le groupe {0}'.format(group))

    def set_group_ppolicy(self, group, ppolicy):
        memberz = self.get_people_group_memberz(group)
        ppolicy_value = 'cn={0},ou=policies,ou=system,{1}'.format(
            ppolicy,
            self.ldap_search_base) if ppolicy != '' else None
        pre_modlist= [('pwdPolicySubentry',
                       ppolicy_value)]
        for member in memberz:
            self.update_uid_attribute(member, pre_modlist)

    def get_uid_detailz(self, uid):
        ldap_filter='(uid={0})'.format(uid)
        attributes=['*','+']
        resultz = self.search(ldap_filter=ldap_filter,
                                  attributes=attributes)
        if resultz:
            return resultz[0]
        else:
            flash(u'Utilisateur {0} non trouvé'.format(uid))
            return None

    def get_user_pwd_policy(self, uid):
        ldap_filter = "(&(objectClass=posixAccount)(uid={0}))".format(uid)
        user = self.anonymous_search(ldap_filter=ldap_filter,
                                     attributes=['pwdPolicySubentry']
                                 )[0].get_attributes()
        if 'pwdPolicySubentry' in user:
            subentry_filter = '(entryDN={0})'.format(user['pwdPolicySubentry'][0])
        else:
            subentry_filter = '(&(objectClass=pwdPolicy)(cn=passwordDefault))'
        base_dn = 'ou=policies,ou=system,{0}'.format(self.ldap_search_base)
        return self.anonymous_search(ldap_filter=subentry_filter,
                             attributes=['*'])[0].get_attributes()

    def get_posix_groupz_memberz(self, groupz_infoz):
        memberz = []
        for branch, cn in groupz_infoz:
            memberz.extend(self.get_posix_group_memberz(branch, cn))
        return memberz

    def get_initial_submission(self):
        submission_groupz_list = self.get_submission_groupz_list()
        initial_submission = ''.join([
            '{0}=0;'.format(submission_group)
            for submission_group in submission_groupz_list
        ])
        return initial_submission

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
