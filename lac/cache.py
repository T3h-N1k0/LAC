import redis
from functools import wraps
from string import capwords
from flask import current_app, request, flash, render_template

# Find the stack on which we want to store the database connection.
# Starting with Flask 0.9, the _app_ctx_stack is the correct one,
# before that we need to use the _request_ctx_stack.
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack
from flask import session, redirect, url_for

class Cache(object):
    def __init__(self, app=None, host=None, ldap=None):

        if host is not None:
            self.redis_host = host
        if ldap is not None:
            self.ldap = ldap
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None
        self.r = redis.Redis(app.config['REDIS_HOST'])

    def init_app(self, app):
        app.config.setdefault('REDIS_HOST', self.redis_host)
        # Use the newstyle teardown_appcontext if it's available,
        # otherwise fall back to the request context
        if hasattr(app, 'teardown_appcontext'):
            app.teardown_appcontext(self.teardown)
        else:
            app.teardown_request(self.teardown)

    def teardown(self, exception):
        ctx = stack.top

    def add_to_work_group_if_not_member(self, group, memberz_uid):
        memberz_dn = [self.ldap.get_full_dn_from_uid(uid)
                      for uid in memberz_uid]
        memberz_dn_filtered = [dn
                               for dn in memberz_dn
                               if dn not in self.r.smembers(
                                       "wrk_groupz:{0}".format(group))
        ]
        if memberz_dn_filtered:
            pre_modlist = [('uniqueMember', memberz_dn_filtered)]
            group_dn = self.ldap.get_wrk_group_dn_from_cn(group)
            self.ldap.add_dn_attribute(group_dn, pre_modlist)

        self.populate_work_group_redis()

    def add_to_people_group_if_not_member(self, group, memberz_uid):
        memberz_uid_filtered = [uid.encode("utf-8")
                               for uid in memberz_uid
                               if uid not in self.r.smembers(
                                       "people_groupz:{0}".format(group))
        ]
        if memberz_uid_filtered:
            pre_modlist = [('memberUid', memberz_uid_filtered)]
            group_dn = self.ldap.get_people_group_dn_from_cn(group)
            self.ldap.add_dn_attribute(group_dn, pre_modlist)
            self.populate_people_group_redis()

    def rem_from_group_if_member(self, group, memberz_uid):
        memberz_dn = [self.ldap.get_full_dn_from_uid(uid)
                      for uid in memberz_uid]
        memberz_dn_filtered = [dn
                               for dn in memberz_dn
                               if dn in self.r.smembers(
                                       "wrk_groupz:{0}".format(group))
        ]
        if memberz_dn_filtered:
            pre_modlist = [('uniqueMember', memberz_dn_filtered)]
            group_dn = self.ldap.get_wrk_group_dn_from_cn(group)
            self.ldap.remove_dn_attribute(group_dn, pre_modlist)

        self.populate_work_group_redis()

    def get_posix_group_cn_by_gid(self, gid):
        return self.r.hget('grouplist', gid)

    def populate_grouplist(self):
        grouplist = self.ldap.get_posix_groupz_choices()
        for (uid, group) in grouplist:
            self.r.hset('grouplist', uid, group)

    def populate_work_group(self):
        for group in self.ldap.get_work_groupz():
            self.r.delete('wrk_groupz:{0}'.format(group))
            memberz = self.ldap.get_work_group_memberz(group)
            for member in memberz:
                self.r.sadd("wrk_groupz:{0}".format(group), member)

    def populate_people_group(self):
        for branch in self.app.config['BRANCHZ']:
            people_group = branch['account']
            # print(people_group)
            print('people_group : {0}'.format(people_group))
            self.r.delete('people_groupz:{0}'.format(people_group))
            memberz = self.ldap.get_people_group_memberz(people_group)
            if memberz:
                for member in memberz:
                    self.r.sadd("people_groupz:{0}".format(people_group), member)
