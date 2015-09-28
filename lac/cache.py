import redis
from functools import wraps
from string import capwords
from flask import current_app, request, flash, render_template


class Cache(object):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['cache'] = self
        app.config.setdefault('REDIS_HOST', 'localhost')
        self.r = redis.Redis(app.config['REDIS_HOST'])
        self.ldap = app.extensions['ldap']

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

        self.populate_work_group()

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
            self.populate_people_group()

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

        self.populate_work_group()

    def get_posix_group_cn_by_gid(self, gid):
        return self.r.hget('grouplist', gid)

    def populate_grouplist(self):
        ldap_groupz = self.ldap.get_posix_groupz()
        for group in ldap_groupz:
            group_attrz = group.get_attributes()
            self.r.hset('grouplist',
                        group_attrz['gidNumber'][0],
                        group_attrz['cn'][0])

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


    def get_group_from_member_uid(self, uid):
        for branch in self.app.config['BRANCHZ']:
            print(branch)
            people_group = branch['account']
            if uid in self.r.smembers("people_groupz:{0}".format(people_group)):
                return people_group

    def update_work_groupz_memberz(self, uid, selected_groupz, actual_groupz):
        for group in selected_groupz:
            self.add_to_work_group_if_not_member(group, [uid])
        for group in actual_groupz:
            if group not in selected_groupz:
                self.rem_from_group_if_member(group, [uid])
