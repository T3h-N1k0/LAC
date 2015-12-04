# coding=utf-8
# -*- coding: utf-8 -*-
import os
import re
import hashlib
import time
from string import strip
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from flask import current_app, request, flash, render_template, session, redirect, url_for
from lac.data_modelz import *
from lac.helperz import *

__author__ = "Nicolas CHATELAIN"
__copyright__ = "Copyright 2014, Nicolas CHATELAIN @ CINES"
__license__ = "GPL"


class Engine(object):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['engine'] = self
        self.cache = app.extensions['cache']
        self.ldap = app.extensions['ldap']
        self.converter = app.extensions['converter']
        self.fm = app.extensions['form_manager']
        self.ldap_search_base = app.config['LDAP_SEARCH_BASE']
        self.ldap_admin = app.config['LDAP_DEFAULT_ADMIN']



    def is_ccc_group(self, member):
        return 'ccc' == self.cache.get_group_from_member_uid(member)

    def is_cines_group(self, uid):
        return 'cines' == self.cache.get_group_from_member_uid(uid)

    def is_principal_group(self, member, group):
        return self.cache.get_posix_group_cn_by_gid(member['gidNumber'][0]) == group

    def disable_account(self, user):
        user_attr = user.get_attributes()
        new_shadow_expire_datetime = datetime.now() - timedelta(days=1)
        new_shadow_expire = str(
            self.converter.datetime_to_days_number(
                new_shadow_expire_datetime))
        self.ldap.update_uid_attribute(user_attr['uid'][0],
                                  [('shadowExpire', new_shadow_expire),
                                   ('pwdAccountLockedTime', "000001010000Z")]
                              )
        flash(u'Compte {0} désactivé'.format(user_attr['uid'][0]))

    def enable_account(self, user):
        user_uid = user.get_attributes()['uid'][0]
        if self.cache.get_group_from_member_uid(user_uid) == 'ccc':
            new_shadow_expire_datetime = self.converter.days_number_to_datetime(
                user.get_attributes()['cinesdaterenew'][0]
            ) + relativedelta(
                months = +self.app.config['SHADOW_DURATION']
            )
            new_shadow_expire = str(
                self.converter.datetime_to_days_number(new_shadow_expire_datetime))
            self.ldap.update_uid_attribute(user_uid,
                                      [('shadowExpire', new_shadow_expire)]
            )
        else:
            self.ldap.remove_uid_attribute(user_uid,
                                      [('shadowExpire', None)])
        self.ldap.remove_uid_attribute(user_uid,
                                       [('pwdAccountLockedTime', None)])

    def get_search_user_fieldz(self):
        page = Page.query.filter_by(label = "search_user").first()
        page_attributez = Field.query.filter_by(page_id = page.id).all()
        return page_attributez

    def get_search_user_attributez(self):
        search_attributez = [attr.label.encode('utf-8')
                             for attr in self.get_search_user_fieldz()]
        return search_attributez

    def get_resultz_from_search_user_form(self, form):
        filter_list =[]
        if form.uid_number.data != "" :
            filter_list.append("(uidNumber={0})".format(
                strip(form.uid_number.data)
            ))
        if form.sn.data != "" :
            filter_list.append("(sn=*{0}*)".format(
                strip(form.sn.data)
            ))
        if form.uid.data != "" :
            filter_list.append("(uid=*{0}*)".format(
                strip(form.uid.data)
            ))
        if form.mail.data != "":
            filter_list.append("(mail=*{0}*)".format(
                strip(form.mail.data)
            ))
        if form.user_disabled.data :
            filter_list.append("(shadowExpire=0)")
        if form.ip.data :
            filter_list.append("(cinesIpClient={0})".format(
                strip(form.ip.data)
            ))
        if form.nationality.data :
            filter_list.append("(cinesNationality={0})".format(
                strip(form.nationality.data)
            ))
        if form.user_type.data == "":
            base_dn = "ou=people,{0}".format(self.ldap_search_base)
        else:
            base_dn = "ou={0},ou=people,{1}".format(form.user_type.data,
                                          self.ldap_search_base)
        if filter_list != [] :
            ldap_filter = "(&(objectClass=posixAccount){0})".format("".join(
                filter_list
            ))
        else:
            ldap_filter = "(objectClass=posixAccount)"
        search_resultz = self.ldap.search(
            ldap_filter=ldap_filter,
            attributes=self.get_search_user_attributez(),
            base_dn=base_dn)
        return search_resultz

    def get_search_group_fieldz(self):
        page = Page.query.filter_by(label = "search_group").first()
        page_attributez = Field.query.filter_by(page_id = page.id, display=True).all()
        return page_attributez

    def get_search_group_attributez(self):
        search_attributez = [attr.label.encode('utf-8')
                             for attr in self.get_search_group_fieldz()]
        return search_attributez

    def get_resultz_from_search_group_form(self, form):
        filter_list =[]
        if form.gid_number.data != "" :
            filter_list.append("(gidNumber={0})".format(
                strip(form.gid_number.data)
            ))
        if form.cn.data != "" :
            filter_list.append("(cn=*{0}*)".format(
                strip(form.cn.data)
            ))
        if form.description.data :
            filter_list.append(
                "(description=*{0}*)".format(
                    strip(form.description.data)
                )
            )
        if form.group_type.data == "":
            base_dn = "ou=groupePosix,{0}".format(self.ldap_search_base)
        else:
            base_dn = "ou={0},ou=groupePosix,{1}".format(
            strip(form.group_type.data),
                self.ldap_search_base)
        if filter_list != [] :
            ldap_filter = "(&(objectClass=posixGroup){0})".format("".join(
                filter_list
            ))
        else:
            ldap_filter = "(objectClass=posixGroup)"
        search_resultz = self.ldap.search(
            ldap_filter=ldap_filter,
            attributes=self.get_search_group_attributez(),
            base_dn=base_dn)
        return search_resultz

    def update_group_memberz_cines_c4(self, branch, group, comite):
        memberz_uid = self.ldap.get_posix_group_memberz(branch, group)
        if len(memberz_uid)>1:
            ldap_filter = '(&(objectClass=posixAccount)(|{0}))'.format(
                ''.join(['(uid={0})'.format(uid) for uid in memberz_uid]))
        elif len(memberz_uid)==1:
            ldap_filter = '(&(objectClass=posixAccount)(uid={0}))'.format(
                memberz_uid[0])
        else:
            return
        memberz = self.ldap.search(
                ldap_filter=ldap_filter,
                attributes=['cinesC4', 'dn', 'uid', 'gidNumber']
            )
        for member in memberz:
            member_attrz = member.get_attributes()
            if (
                    self.is_ccc_group(member_attrz['uid'][0])
                    and self.is_principal_group(member_attrz, group)
                    and (
                        'cinesC4' not in member_attrz
                         or member_attrz['cinesC4'][0] != comite
                    )
            ):
                if not comite and 'cinesC4' in member_attrz:
                    self.ldap.remove_uid_attribute(
                        member_attrz['uid'][0],
                        [('cinesC4', None)]
                    )
                elif comite:
                    self.ldap.update_uid_attribute(
                        member_attrz['uid'][0],
                        [('cinesC4', comite.encode('utf-8'))])
                print('{0} mis à jour à : {1}'.format(
                    member_attrz['uid'][0],
                    comite))

    def update_password_from_form(self, form, uid):
        pre_modlist = []
        if self.cache.get_group_from_member_uid(uid) == 'cines':
            nt_hash = hashlib.new(
                'md4',
                strip(form.new_pass.data).encode('utf-16le')
            ).hexdigest().upper()
            pre_modlist = [('sambaPwdLastSet', str(int(time.time()))),
                           ('sambaNTPassword', nt_hash)]

        if uid != session['uid']:
            pre_modlist.append(('userPassword',
                                strip(form.new_pass.data).encode('utf-8')))
            if self.cache.get_group_from_member_uid(uid) not in ['autre', 'soft']:
                pre_modlist.append(('pwdReset', 'TRUE'))
            flash(u'Mot de passe pour {0} mis à jour avec succès.'.format(uid))
            self.ldap.update_uid_attribute(uid, pre_modlist)
            return redirect(url_for('show_user',
                                    page= self.cache.get_group_from_member_uid(uid),
                                    uid=uid))
        else:
            self.ldap.change_passwd(
                uid,
                session['password'],
                strip(form.new_pass.data)
                )
            flash(
                u'Votre mot de passe a été mis à jour avec succès.'.format(uid)
            )

            if pre_modlist:
                self.ldap.update_uid_attribute(uid, pre_modlist)
            return redirect(url_for('home'))

    def update_page_from_form(self, page, raw_form):
        form = raw_form['form']
        page_oc_id_list = raw_form['page_oc_id_list']
        page_unic_attr_id_list = raw_form['page_unic_attr_id_list']
        attr_label_list = raw_form['attr_label_list']
        if attr_label_list is not None:
            self.update_fields_from_edit_page_admin_form(form, attr_label_list, page)
        if form.oc_form.selected_oc.data is not None:
            # On traite les ObjectClass ajoutées
            for oc_id in form.oc_form.selected_oc.data :
                if oc_id not in page_oc_id_list:
                    print("Creation de l'Object Class id {0}".format(oc_id))
                    page_oc =  PageObjectClass(page.id, oc_id)
                    db.session.add(page_oc)
            # On traite les ObjectClass supprimées
            # et les fieldz associés en cascade
            for oc_id in page_oc_id_list:
                if oc_id not in form.oc_form.selected_oc.data:
                    print("Suppression de l'Object Class id {0}".format(oc_id))
                    PageObjectClass.query.filter_by(page_id=page.id,
                                                    ldapobjectclass_id= oc_id
                    ).delete()
                    attr_to_del_list = [
                        attr.id for attr in get_attr_from_oc_id_list([oc_id])
                    ]
                    print("Attributs à supprimer {0}".format(attr_to_del_list))
                    Field.query.filter(Field.page_id==page.id,
                                       Field.ldapattribute_id.in_(
                                           attr_to_del_list
                                       )
                    ).delete(synchronize_session='fetch')
        if form.attr_form.selected_attr.data is not None:
            # On traite les Attributes ajoutées
            for attr_id in form.attr_form.selected_attr.data :
                if attr_id not in page_unic_attr_id_list:
                    print("Creation de l'attribut id {0}".format(attr_id))
                    attr = LDAPAttribute.query.filter_by(id = attr_id).first()
                    self.create_default_field(attr, page)
        if page_unic_attr_id_list is not None:
            # On traite les Attributes supprimées
            for attr_id in page_unic_attr_id_list:
                if attr_id not in form.attr_form.selected_attr.data:
                    print("Suppression de l'attribut id {0}".format(attr_id))
                    Field.query.filter_by(
                        id=attr_id
                    ).delete()
        db.session.commit()

    def update_lac_admin_from_form(self, form):
        dn = "cn=lacadmin,ou=system,{0}".format(self.ldap_search_base)
        memberz = [ get_uid_from_dn(dn)
                    for dn in self.ldap.get_lac_admin_memberz() ]
        if form.selected_memberz.data is not None:
            memberz_to_add = []
            for member in form.selected_memberz.data:
                if member not in memberz:
                    print('ajout de {0}'.format(member))
                    memberz_to_add.append(self.ldap.get_full_dn_from_uid(member))
            if memberz_to_add:
                self.ldap.add_dn_attribute(dn,
                                           [('member', member.encode('utf8'))
                                            for member in memberz_to_add]
                                       )
        if memberz is not None:
            memberz_to_del = []
            for member in memberz:
                if member not in form.selected_memberz.data:
                    print('suppression de {0}'.format(member))
                    memberz_to_del.append(self.ldap.get_full_dn_from_uid(member))
            if memberz_to_del:
                self.ldap.remove_dn_attribute(dn,
                                              [('member', member.encode('utf8'))
                                               for member in memberz_to_del]
                                   )

    def update_ldap_admin_from_form(self, form):
        dn = "cn=ldapadmin,ou=system,{0}".format(self.ldap_search_base)
        memberz = [ get_uid_from_dn(dn)
                    for dn in self.ldap.get_ldap_admin_memberz() ]
        if form.selected_memberz.data is not None:
            memberz_to_add = []
            for member in form.selected_memberz.data:
                if member not in memberz:
                    print('ajout de {0}'.format(member))
                    memberz_to_add.append(self.ldap.get_full_dn_from_uid(member))
            if memberz_to_add:
                ldap.add_dn_attribute(dn,
                                      [('member', member.encode('utf8'))
                                        for member in memberz_to_add]
                                   )
        if memberz is not None:
            memberz_to_del = []
            for member in memberz:
                if member not in form.selected_memberz.data:
                    print('suppression de {0}'.format(member))
                    memberz_to_del.append(self.ldap.get_full_dn_from_uid(member))
            if memberz_to_del:
                self.ldap.remove_dn_attribute(dn,
                                          [('member', member.encode('utf8'))
                                           for member in memberz_to_del]
                                   )
        fm.populate_ldap_admin_choices(form)

    def get_last_used_id(self, ldap_ot):
        attributes=['gidNumber'] if ldap_ot.apply_to == 'group' else ['uidNumber']
        if ldap_ot.apply_to == 'group':
            ldap_filter = '(objectClass=posixGroup)'
        else:
            ldap_filter = '(objectClass=posixAccount)'
        base_dn='ou={0},ou={1},{2}'.format(
            ldap_ot.label,
            'groupePosix' if ldap_ot.apply_to == 'group' else 'people',
            self.ldap_search_base
        )
        resultz = self.ldap.search(base_dn,ldap_filter,attributes)
        if not resultz:
            return 0
        max_id= 0
        for result in resultz:
            result_id = int(result.get_attributes()[attributes[0]][0])
            if result_id > max_id:
                max_id = result_id
        return str(max_id)



    def is_active(self, user):
        user_attrz = user.get_attributes()
        if ('shadowExpire' in user_attrz and datetime.now()> self.converter.days_number_to_datetime(
                user_attrz['shadowExpire'][0]
        )) or ('pwdAccountLockedTime' in user_attrz):
            return False
        else:
            return True


    def update_default_quota(self, storage_cn, form):
        cinesQuotaSizeHard = self.fm.get_quota_value_from_form(
            form,
            'cinesQuotaSizeHard')
        cinesQuotaSizeSoft = self.fm.get_quota_value_from_form(
            form,
            'cinesQuotaSizeSoft')
        cinesQuotaInodeHard = self.fm.get_quota_value_from_form(
            form,
            'cinesQuotaInodeHard')
        cinesQuotaInodeSoft = self.fm.get_quota_value_from_form(
            form,
            'cinesQuotaInodeSoft')
        pre_modlist = [('cinesQuotaSizeHard', cinesQuotaSizeHard),
                       ('cinesQuotaSizeSoft', cinesQuotaSizeSoft),
                       ('cinesQuotaInodeHard', cinesQuotaInodeHard),
                       ('cinesQuotaInodeSoft', cinesQuotaInodeSoft)]
#        self.ldap.update_cn_attribute(storage_cn, pre_modlist)

    def update_quota(self, storage, form):
        default_storage_cn = storage['cn'][0].split('.')[0]
        default_storage = self.ldap.get_default_storage(default_storage_cn).get_attributes()

        pre_modlist = []

        for field_name in self.app.config['QUOTA_FIELDZ']:
            form_value = self.fm.get_quota_value_from_form(
                form,
                field_name)
            default_field = self.app.config['QUOTA_FIELDZ'][field_name]['default']
            if (
                    form_value != default_storage[default_field][0]
                    and (field_name not in storage
                         or  form_value != storage[field_name][0])
            ):
                print('form_value : {0} field_name : {1}  default_storage[default_field] : {2}'.format(form_value, field_name,  default_storage[default_field]))
                pre_modlist.append((field_name, form_value))


        cinesQuotaSizeTempExpire = self.converter.datetime_to_timestamp(
            form.cinesQuotaSizeTempExpire.data
        ).encode('utf-8')
        if cinesQuotaSizeTempExpire != storage['cinesQuotaSizeTempExpire']:
            pre_modlist.append(('cinesQuotaSizeTempExpire',
                                cinesQuotaSizeTempExpire))

        cinesQuotaInodeTempExpire = self.converter.datetime_to_timestamp(
            form.cinesQuotaInodeTempExpire.data
        ).encode('utf-8')

        if cinesQuotaInodeTempExpire != storage['cinesQuotaInodeTempExpire']:
            pre_modlist.append(('cinesQuotaInodeTempExpire',
                                cinesQuotaInodeTempExpire))
#        self.ldap.update_cn_attribute(storage['cn'][0], pre_modlist)





    def populate_last_used_idz(self):
        ignore_ot_list = ['reserved', 'grLight', 'grPrace']
        ldap_otz = LDAPObjectType.query.all()
        for ldap_ot in ldap_otz:
            if ldap_ot.label not in ignore_ot_list:
                last_used_id = self.get_last_used_id(ldap_ot)
                id_range = self.get_range_list_from_string(ldap_ot.ranges)
                if int(last_used_id) not in id_range:
                    last_used_id = id_range[0]
                ldap_ot.last_used_id = last_used_id
                db.session.add(ldap_ot)
        db.session.commit()

    def create_ldapattr_if_not_exists(self, label):
        db_attr = LDAPAttribute.query.filter_by(
            label = label
        ).first()
        if db_attr is None:
            db_attr = LDAPAttribute(label=label)
        return db_attr


    def create_ldap_object_from_add_group_form(self, form, page_label):
        ot = LDAPObjectType.query.filter_by(label = page_label).first()
        cn = strip(form.cn.data).encode('utf-8')
        description = strip(form.description.data).encode('utf-8')
        id_number = str(self.get_next_id_from_ldap_ot(ot))
        object_classes = [oc_ot.ldapobjectclass.label.encode('utf-8')
                          for oc_ot in LDAPObjectTypeObjectClass.query.filter_by(
                              ldapobjecttype_id = ot.id).all()]
        if not object_classes:
            flash(u'ObjectClasss manquants pour ce type d\'objet')
            return 0

        full_dn = "cn={0},ou={1},ou=groupePosix,{2}".format(
            cn,
            ot.label,
            self.ldap_search_base)
        add_record = [('cn', [cn]),
                      ('gidNumber', [id_number]),
                      ('objectClass', object_classes)]
        if page_label != 'grProjet':
            add_record.append(('fileSystem', [form.filesystem.data.encode('utf-8')]))
        if description and description != '':
            add_record.append(('description', [description]))
        if hasattr(form, 'responsable'):
            add_record.append(('cinesProjResp', [form.responsable.data.encode('utf-8')]))
        if 'sambaGroupMapping' in object_classes:
            add_record.extend([
                ('sambaSID', "{0}-{1}".format(self.ldap.get_sambasid_prefix(),
                                                     id_number)),
                ('sambaGroupType', ['2'])
            ])

        if self.ldap.add(full_dn, add_record):
            ot.last_used_id= id_number
            db.session.add(ot)
            db.session.commit()
            self.cache.populate_grouplist()
            self.cache.populate_people_group()
            flash(u'Groupe créé')
            return 1

    def create_ldap_object_from_add_workgroup_form(self, form):
        ot = LDAPObjectType.query.filter_by(label = 'grTravail').first()
        cn = strip(form.cn.data).encode('utf-8')
        description = strip(form.description.data).encode('utf-8')
        object_classes = [oc_ot.ldapobjectclass.label.encode('utf-8')
                          for oc_ot in LDAPObjectTypeObjectClass.query.filter_by(
                              ldapobjecttype_id = ot.id).all()]
        if not object_classes:
            flash(u'ObjectClasss manquants pour ce type d\'objet')
            return 0

        full_dn = "cn={0},ou=grTravail,{1}".format(
            cn,
            self.ldap_search_base)
        add_record = [('cn', [cn]),
                      ('cinesGrWorkType', [
                          getattr(form, 'cinesGrWorkType').data.encode('utf-8')
                      ]),
                      ('uniqueMember', [self.ldap_admin]),
                      ('objectClass', object_classes)]
        if description and description != '':
            add_record.append(('description', [description]))
        if self.ldap.add(full_dn, add_record):
            db.session.add(ot)
            db.session.commit()
            self.cache.populate_work_group()
            flash(u'Groupe créé')
            return 1

    def create_ldap_object_from_add_user_form(self, form, fieldz, page):
        ldap_ot = LDAPObjectType.query.filter_by(
            label=page.label
        ).first()
        ldap_ot_ocz = LDAPObjectTypeObjectClass.query.filter_by(
            ldapobjecttype_id = ldap_ot.id
        ).all()
        ot_oc_list = [oc.ldapobjectclass.label.encode('utf-8')
                      for oc in ldap_ot_ocz]
        form_attributez = []
        uid = form.uid.data
        for field in fieldz:
            form_field_values = [
                self.converter.from_display_mode(
                    strip(entry.data),
                    field.fieldtype.type
                )
                for entry in getattr(form, field.label).entries
            ]
            if field.label == 'cinesdaterenew' :
                now_days_number = self.converter.datetime_to_days_number(datetime.now())
                if form_field_values[0] == now_days_number :
                    form_field_values = []
            if (field.label not in ['cinesUserToPurge', 'cn', 'cinesIpClient']
                and form_field_values != [''] ):
                form_attributez.append((field.label, form_field_values))
            if (field.label == 'cinesIpClient' and form_field_values != ['']):
                form_attributez.append((field.label, ';'.join(form_field_values)))
            if field.label == 'gidNumber':
                gid_number = form_field_values[0]
                self.cache.add_to_people_group_if_not_member(
                    self.cache.get_posix_group_cn_by_gid(gid_number),
                    [uid.encode('utf-8')])
        uid_number = self.get_next_id_from_ldap_ot(ldap_ot)
        add_record = [('uid', [uid.encode('utf-8')]),
                      ('cn', [uid.encode('utf-8')]),
                      ('uidNumber', [str(uid_number).encode('utf-8')]),
                      ('objectClass', ot_oc_list)]
        add_record.extend(form_attributez)
        add_record.append(
            ('homeDirectory', "/home/{0}".format(uid).encode('utf-8')))
        new_shadow_expire_datetime = datetime.now() + relativedelta(
            months = +self.app.config['SHADOW_DURATION']
        )
        new_shadow_expire = str(
            self.converter.datetime_to_days_number(new_shadow_expire_datetime))
        add_record.append(
            ('shadowlastchange',
             [str(self.converter.datetime_to_days_number(datetime.now()))]
         )
        )
        add_record.append(
            ('shadowexpire', [new_shadow_expire] ))
        if 'cinesusr' in ot_oc_list:
            add_record.append(
                ('cinesSoumission', [self.ldap.get_initial_submission()])
            )
        if 'sambaSamAccount' in ot_oc_list:
            add_record.append(
                ('sambaSID', "{0}-{1}".format(self.ldap.get_sambasid_prefix(),
                                                     uid_number))
            )
        if  page.label == 'ccc' and gid_number:
            group_cn = self.cache.get_posix_group_cn_by_gid(gid_number)
            ressource = C4Ressource.query.filter_by(
                                            code_projet = group_cn).first()
            if ressource:
                comite = ressource.comite.ct
            else:
                comite = ''
            if comite != '':
                add_record.append(
                    ('cinesC4', comite.encode('utf-8'))
                )
        if ldap_ot.ppolicy != '':
            add_record.append(
                ('pwdPolicySubentry',
                 'cn={0},ou=policies,ou=system,{1}'.format(
                     ldap_ot.ppolicy,
                     self.ldap_search_base)
                )
            )
        parent_dn = self.ldap.get_people_dn_from_ou(ldap_ot.label)
        full_dn = "uid={0};{1}".format(uid,parent_dn)
        if self.ldap.add(full_dn, add_record):
            ldap_ot.last_used_id= uid_number
            db.session.add(ldap_ot)
            db.session.commit()
            self.cache.populate_grouplist()
            self.cache.populate_people_group()
        else:
            flash(u'L\'utilisateur n\'a pas été créé')
        return True

    def create_ldap_object_from_add_object_type_form(self,
                                                     form,
                                                     ldap_object_type ):
        selected_oc_choices = self.fm.get_ot_oc_choices(ldap_object_type)
        ot_oc_id_list = [oc[0] for oc in selected_oc_choices]
        ldap_object_type.label = strip(form.label.data)
        ldap_object_type.description = strip(form.description.data)
        ldap_object_type.ranges = strip(form.ranges.data)
        ldap_object_type.apply_to = strip(form.apply_to.data)
        ldap_object_type.ppolicy = form.ppolicy.data
        db.session.add(ldap_object_type)
        if form.object_classes.selected_oc.data is not None:
            # On traite les ObjectClass ajoutées
            for oc_id in form.object_classes.selected_oc.data :
                if oc_id not in ot_oc_id_list:
                    print("Creation de l'Object Class id {0}".format(oc_id))
                    ot_oc =  LDAPObjectTypeObjectClass(
                        ldap_object_type.id, oc_id)
                    db.session.add(ot_oc)
                    # On traite les ObjectClass supprimées
                    # et les fieldz associés en cascade
            for oc_id in ot_oc_id_list:
                if oc_id not in form.object_classes.selected_oc.data:
                    print("Suppression de l'Object Class id {0}".format(oc_id))
                    LDAPObjectTypeObjectClass.query.filter_by(
                        ldapobjecttype_id=ldap_object_type.id,
                        ldapobjectclass_id= oc_id
                    ).delete()
        db.session.commit()
        if form.set_ppolicy.data :
            self.ldap.set_group_ppolicy(ldap_object_type.label,
                                   ldap_object_type.ppolicy)
        flash(u'{0} mis à jour'.format(ldap_object_type.description))

    def create_ldap_quota(self, storage, group_id):
        niou_cn = '{0}.{1}'.format(
            storage,
            group_id)
        print("plop  : {0}".format(storage))
        default_storage = self.ldap.get_default_storage(
            storage).get_attributes()
        default_size_unit = getattr(
            getattr(SizeQuotaForm, 'unit'),'kwargs')['default']
        default_inode_unit = getattr(
            getattr(InodeQuotaForm, 'unit'),'kwargs')['default']
        cinesQuotaSizeHard = str(int(
            default_storage['cinesQuotaSizeHard'][0]
        ) / default_size_unit)
        cinesQuotaSizeSoft = str(int(
            default_storage['cinesQuotaSizeSoft'][0]
        ) / default_size_unit)
        cinesQuotaInodeHard = str(int(
            default_storage['cinesQuotaInodeHard'][0]
        ) / default_inode_unit)
        cinesQuotaInodeSoft = str(int(
            default_storage['cinesQuotaInodeSoft'][0]
        ) / default_inode_unit)
        add_record = [('cn', [niou_cn]),
                      ('objectClass', ['top', 'cinesQuota']),
                      ('cinesQuotaSizeHard', cinesQuotaSizeHard),
                      ('cinesQuotaSizeSoft', cinesQuotaSizeSoft),
                      ('cinesQuotaInodeHard', cinesQuotaInodeHard),
                      ('cinesQuotaInodeSoft', cinesQuotaInodeSoft)
        ]
        print(group_id)
        group_full_dn = self.ldap.get_full_dn_from_cn(
            self.cache.get_posix_group_cn_by_gid(group_id))
        full_dn = 'cn={0},{1}'.format(niou_cn,group_full_dn)
        self.ldap.add(full_dn, add_record)
        flash(u'Quota initialisé')

    def update_users_by_file(self, edit_form, attrz_list):
        fieldz = Field.query.filter(Field.id.in_(attrz_list)).all()
        pre_modlist = []
        for field in fieldz:
            pre_modlist.append(
                (field.label,
                 strip(getattr(edit_form, field.label).data).encode('utf-8'))
            )
        if edit_form.action.data == '0':
            for uid in userz:
                ldap.add_uid_attribute(uid, pre_modlist)
        elif edit_form.action.data == '1':
            for uid in userz:
                ldap.update_uid_attribute(uid, pre_modlist)
        flash(u'Les utilisateurs ont été mis à jour')

    def generate_backup_file(self, userz, attributez):
        userz = [strip(user).encode('utf-8') for user in userz.split(',')]
        attributez = [strip(attribute).encode('utf-8')
                      for attribute in attributez.split(',')]
        file_name = "backup_{0}.txt".format(
            datetime.now().strftime("%d%b%HH%M_%Ss"))
        file_content = " ".join(attributez)
        for user in userz:
            user_attr = ldap.search(
                ldap_filter="(uid={0})".format(user),
                attributes=attributez)[0].get_attributes()
            line = ",".join(["{0}={1}".format(key, value)
                for key, value in user_attr.iteritems()])
            line = ",".join(["uid={0}".format(user),line])
            file_content = "\n".join([file_content, line])
            response = make_response(file_content)
            response.headers[
                'Content-Disposition'
            ] = 'attachment; filename={0}'.format(file_name)
        return response

    def get_next_id_from_ldap_ot(self, ldap_ot):
        id_range = self.get_range_list_from_string(ldap_ot.ranges)
        next_index = id_range.index(ldap_ot.last_used_id)+1
        if ldap_ot.apply_to == 'group':
            id_type = 'gidNumber'
        else:
            id_type = 'uidNumber'
        while 1:
            test_id = id_range[next_index]
            ldap_filter = '({0}={1})'.format(id_type, test_id)
            result = self.ldap.search(ldap_filter=ldap_filter,
                                     attributes = [id_type])
            if not result:
                return test_id
            next_index += 1

    def get_storagez_labelz(self):
        storagez = ldap.get_group_quota_list()
        storagez_labelz = [storage.get_attributes()['cn'][0]
                               for storage in storagez]
        return storagez_labelz

    def get_range_list_from_string(self, rangez_string):
        rangez = rangez_string.split(';')
        rangez_lst = []
        for range_string in rangez:
            if range_string != '':
                range_split = range_string.split('-')
                rangez_lst.extend(range(
                    int(range_split[0]),
                    int(range_split[1])+1))
        return sorted(set(rangez_lst))


    def update_ldap_object_from_edit_ppolicy_form(self, form, attributes, cn):
        dn = "cn={0},ou=policies,ou=system,{1}".format(self.ldap_search_base)
        ppolicy_attrz = self.ldap.get_ppolicy(cn).get_attributes()
        pre_modlist = []
        for attr in attributes:
            field_value = strip(getattr(form, attr).data).encode('utf-8')
            if attr not in ppolicy_attrz or ppolicy_attrz[attr][0] != field_value:
                # if attr == 'pwdMustChange':
                #     pre_modlist.append((attr, [True if field_value else False]))
                # else:
                pre_modlist.append((attr, [field_value]))
        self.ldap.update_dn_attribute(dn, pre_modlist)

    def update_ldap_object_from_edit_user_form(self, form, fieldz, uid, page):
        uid_attributez = self.ldap.get_uid_detailz(uid).get_attributes()
        pre_modlist = []
        for field in fieldz:
            form_values = [
                self.converter.from_display_mode(
                    strip(entry.data),
                    field.fieldtype.type
                )
                for entry in getattr(form, field.label).entries
            ]
            if field.label == 'cinesIpClient':
                form_values = [';'.join(form_values)]
            if (field.label not in uid_attributez
                or uid_attributez[field.label] != form_values):
                if form_values == [''] or (field.label == 'cinesUserToPurge'
                                           and True not in form_values):
                    form_values = None
                if (
                        field.label == 'cinesUserToPurge'
                        and form_values
                        and True in form_values
                ):
                    form_values = ['1']
                pre_modlist.append((field.label, form_values))
                if  page.label == 'ccc' and field.label == 'gidNumber':
                    group_cn = self.cache.get_posix_group_cn_by_gid(form_values[0])
                    ressource = C4Ressource.query.filter_by(
                                            code_projet = group_cn).first()
                    if ressource:
                        comite = ressource.comite.ct
                    else:
                        comite = ''
                    if comite != '':
                        pre_modlist.append(
                            ('cinesC4', comite.encode('utf-8'))
                        )
                    print('Group: {0} && Comite: {1}'.format(group_cn, comite))
        self.ldap.update_uid_attribute(uid, pre_modlist)

    def upsert_otrs_user(self, uid):
        user_attrz = self.ldap.get_uid_detailz(uid).get_attributes()
        otrs_user = OTRSCustomerUser.query.filter_by(login = uid).first()
        if not otrs_user:
            otrs_user = OTRSCustomerUser(login = uid)
        if 'telephoneNumber' in user_attrz:
            telephone_number = ';'.join(
                [phone for phone in user_attrz['telephoneNumber']])
        else:
            telephone_number = ''
        user_type = LDAPObjectType.query.filter_by(
            label = self.cache.get_group_from_member_uid(uid)
        ).first().description
        first_gr_name = self.cache.get_posix_group_cn_by_gid(user_attrz['gidNumber'][0])
        otrs_user.email = user_attrz['mail'][0]
        otrs_user.customer_id = user_attrz['uidNumber'][0]
        otrs_user.first_name = user_attrz['givenName'][0]
        otrs_user.last_name = user_attrz['sn'][0]
        otrs_user.phone = telephone_number
        otrs_user.comments = '{0}; {1}'.format(user_type, first_gr_name)
        otrs_user.valid_id = 1
        otrs_user.create_time = datetime.now()
        db.session.add(otrs_user)
        db.session.commit()

    def delete_otrs_user(self, uid):
        date = datetime.now().strftime("%Y%m%d%H%M")
        disabled_login = "".join(['ZDEL', date, "_", uid])
        # print(disabled_login)
        otrs_user = OTRSCustomerUser.query.filter_by(login = uid).first()
        if otrs_user:
            otrs_user.login = disabled_login
            otrs_user.valid_id = 2
            db.session.add(otrs_user)
        otrs_ticketz = OTRSTicket.query.filter_by(customer_user_id = uid).all()
        for ticket in otrs_ticketz:
            ticket.customer_user_id = disabled_login
            db.session.add(ticket)
        if self.is_cines_group(uid):
            OTRSUser.query.filter_by(login=uid).update(
                {
                    'valid_id': 2,
                    'login': disabled_login,
                    'change_time': datetime.now()
                }, synchronize_session=False
            )
        db.session.commit()

    def update_user_table_on_deletion(self, uid):
        ldap_user = self.ldap.get_uid_detailz(uid).get_attributes()
        db_user = db.session.query(User).filter_by(uid=uid).first()
        # Create user if doesn't already exists
        if not db_user:
            db_user = User(uid=uid)
            db.session.add(db_user)
        db_user.uid_number = ldap_user['uidNumber'][0].decode('utf-8')
        db_user.firstname = ldap_user['givenName'][0].decode('utf-8')
        db_user.lastname = ldap_user['sn'][0].decode('utf-8')
        db_user.deletion_timestamp = datetime.now()
        if 'mail' in ldap_user:
            db_user.email = ldap_user['mail'][0].decode('utf-8')
        if 'telephoneNumber' in ldap_user:
            db_user.phone_number = ldap_user['telephoneNumber'][0].decode('utf-8')
        db.session.commit()


    def remove_user_from_all_groupz(self, uid, posix_groupz, work_groupz):
        user_dn = self.ldap.get_full_dn_from_uid(uid)
        for group_cn in work_groupz:
            group_dn = 'cn={0},ou=grTravail,{1}'.format(
                group_cn,
                self.ldap_search_base
            )
            pre_modlist = [('uniqueMember', user_dn.encode('utf-8'))]
            self.ldap.remove_dn_attribute(group_dn,pre_modlist)
        for (group_cn, group_branch) in posix_groupz:
            group_dn = self.ldap.get_group_full_dn(group_branch, group_cn)
            pre_modlist = [('memberUid', uid.encode('utf-8'))]
            self.ldap.remove_dn_attribute(group_dn,pre_modlist)


    def update_user_submission(self, uid, form):
        wrk_group = strip(form.wrk_group.data)
        is_submission = form.submission.data
        is_member = form.member.data
        if is_submission and is_member:
            self.cache.add_to_work_group_if_not_member(wrk_group, [uid])
            self.ldap.set_submission(uid, wrk_group, '1')
        elif is_member and not is_submission:
            self.cache.add_to_work_group_if_not_member(wrk_group, [uid])
            self.ldap.set_submission(uid, wrk_group, '0')
        elif not is_member:
            self.cache.rem_from_workgroup_if_member(wrk_group, [uid])
            self.ldap.set_submission(uid, wrk_group, '0')

    def update_group_submission(self, form):
        groupz_id = form.group_form.selected_groupz.data
        groupz_infoz = [
            (self.ldap.get_branch_from_posix_group_gidnumber(id),
             self.cache.get_posix_group_cn_by_gid(id))
            for id in groupz_id
        ]
        groupz_memberz = self.ldap.get_posix_groupz_memberz(groupz_infoz)
        wrk_group = form.submission_form.wrk_group.data
        is_submission = form.submission_form.submission.data
        is_member = form.submission_form.member.data
        if is_submission and is_member:
            self.cache.add_to_work_group_if_not_member(
                wrk_group,
                groupz_memberz_uid)
            for uid in groupz_memberz_uid:
                self.ldap.set_submission(uid, wrk_group, '1')
        elif is_member and not is_submission:
            self.cache.add_to_work_group_if_not_member(
                wrk_group,
                groupz_memberz_uid)
            for uid in groupz_memberz_uid:
                self.ldap.set_submission(uid, wrk_group, '0')
        elif not is_member:
            self.cache.rem_from_workgroup_if_member(wrk_group, groupz_memberz_uid)
            for uid in groupz_memberz_uid:
                self.ldap.set_submission(uid, wrk_group, '0')

    def update_ldap_object_from_edit_group_form(self, form, page, group_cn):
        ldap_filter='(&(cn={0})(objectClass=posixGroup))'.format(group_cn)
        attributes=['*','+']
        group_attributez = self.ldap.search(
            ldap_filter=ldap_filter,
            attributes=attributes)[0].get_attributes()
        pagefieldz = Field.query.filter_by(page_id = page.id,
                                           edit = True).all()
        pre_modlist = []
        for field in pagefieldz:
            form_field_values = [strip(entry.data).encode('utf-8')
                                 for entry in getattr(form, field.label).entries]
            if form_field_values == ['']:
                form_field_values = None
            if ((field.label not in group_attributez)
                or (field.label in group_attributez
                    and group_attributez[field.label] != form_field_values)):
                pre_modlist.append((field.label, form_field_values))
        pre_modlist.append(
            ('memberuid',
             [
                 member.encode('utf-8') for member in
                 form.memberz.selected_memberz.data
             ])
        )
        group_dn="cn={0},ou={1},ou=groupePosix,{2}".format(
            group_cn,
            page.label,
            self.ldap_search_base)
        self.ldap.update_dn_attribute(group_dn, pre_modlist)

    def update_ldap_object_from_edit_workgroup_form(self, form, page, group_cn):
        dn="cn={0},ou=grTravail,{1}".format(
            group_cn,
            self.ldap_search_base)
        ldap_filter='(&(cn={0})(objectClass=cinesGrWork))'.format(group_cn)
        attributes=['*','+']
        group_attributez = self.ldap.search(
            ldap_filter=ldap_filter,
            attributes=attributes)[0].get_attributes()
        pagefieldz = Field.query.filter_by(page_id = page.id,
                                           edit = True).all()
        pre_modlist = []
        for field in pagefieldz:
            form_field_values = [strip(entry.data).encode('utf-8')
                                 for entry in
                                 getattr(form, field.label).entries]
            if form_field_values == ['']:
                form_field_values = None
            if ((field.label not in group_attributez)
                or (field.label in group_attributez
                    and group_attributez[field.label] != form_field_values)):
                pre_modlist.append((field.label, form_field_values))
        old_memberz = group_attributez['uniqueMember']
        new_memberz = [
            self.ldap.get_full_dn_from_uid(member).encode('utf-8')
            for member in form.memberz.selected_memberz.data
            if self.ldap.get_full_dn_from_uid(member) is not None
        ]
        for member in old_memberz:
            if (member not in new_memberz
                and self.cache.get_group_from_member_uid(
                    get_uid_from_dn(member)) == "cines"):
                self.ldap.set_submission( get_uid_from_dn(member), group_cn, '0')
        pre_modlist.append(
            ('uniqueMember',
             new_memberz
             )
        )
        self.cache.populate_work_group()
        self.ldap.update_dn_attribute(dn, pre_modlist)

    def update_fields_from_edit_page_admin_form(self, form, attributes, page):
        Field.query.filter(Field.page_id == page.id,
                           ~Field.label.in_(attributes)
        ).delete(synchronize_session='fetch')
        for attribute in attributes:
            attribute_field = getattr(form, attribute)
            self.upsert_field(attribute, attribute_field, page)


    def create_default_field(self, attribute, page):
        print("Create default {0} for {1}".format(attribute, page.label))
        field_type = FieldType.query.filter_by(type='Text').first()
        page_attr = Field(label = attribute.label,
                          page = page,
                          ldapattribute = attribute,
                          fieldtype=field_type)
        db.session.add(page_attr)
        db.session.commit()
        return page_attr

    def upsert_field(self, attr_label, form_field, page):
        print('Upsert field {0}'.format(attr_label))
        attribute = LDAPAttribute.query.filter_by(label = attr_label).first()
        field_type = FieldType.query.filter_by(
            id=form_field.display_mode.data
        ).first()
        existing_field = Field.query.filter_by(page_id=page.id,
                                               label=attribute.label,
                                               ldapattribute_id=attribute.id
        ).first()
        if existing_field is not None:
            existing_field.display = form_field.display.data
            existing_field.edit = form_field.edit.data
            existing_field.restrict = form_field.restrict.data
            existing_field.fieldtype = field_type
            existing_field.description = strip(form_field.desc.data)
            existing_field.multivalue = form_field.multivalue.data
            existing_field.mandatory = form_field.mandatory.data
            existing_field.priority = form_field.priority.data
            existing_field.block = strip(form_field.block.data)
        else:
            new_field = Field(label=attribute.label,
                              page=page,
                              ldapattribute=attribute,
                              display=form_field.display.data,
                              edit=form_field.edit.data,
                              restrict=form_field.restrict.data,
                              fieldtype=field_type,
                              description=form_field.desc.data,
                              multivalue=form_field.multivalue.data,
                              mandatory=form_field.mandatory.data,
                              priority=form_field.priority.data,
                              block=form_field.block.data)
            db.session.add(new_field)

    # def add_user_to_lac_admin(self, user):
    #     self.ldap.update_uid_attribute(user, pre_modlist)


    def get_dict_from_raw_log_valuez(self, raw_valuez):
        valuez = {}
        for raw_value in raw_valuez:
            # print(raw_value)
            raw_value_split = raw_value.split(":")
            attr_name = raw_value_split[0]
            attr_operation = raw_value_split[1][:1]
            attr_value = raw_value_split[1][1:]
            if attr_name in [
                    'userPassword',
                    'sambaNTPassword',
                    'pwdHistory'
            ]:
                attr_value = '<PASSWORD_HASH>'
            elif attr_name in [
            'pwdChangedTime',
            'modifyTimestamp',
            'pwdFailureTime',
            ]:
                if attr_value != "":
                    attr_value = self.converter.generalized_time_to_datetime(
                        attr_value.strip())
            if attr_name not in [
                    'entryCSN',
                    'modifiersName',
                    'modifyTimestamp',
                    'uidNumber'
            ]:
                if attr_name in valuez:
                    valuez[attr_name].append(
                        (attr_value ,
                         attr_operation)
                    )
                else:
                    valuez[attr_name] = [(attr_value, attr_operation)]
        return valuez

    def allowed_file(self, filename):
        print("filename : {0}".format(filename))
        print(filename.rsplit('.', 1)[1])

        return '.' in filename and \
               filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

    def get_cinesdaterenew_from_uid(self, uid):
        page = Page.query.filter_by(label='ccc').first()
        field = Field.query.filter_by(
            page_id = page.id,
            label = 'cinesdaterenew').first()
        ldap_filter='(uid={0})'.format(uid)
        attributes=['cinesdaterenew']
        base_dn='ou=people,{0}'.format(self.ldap_search_base)
        uid_attrz= self.ldap.search(base_dn,ldap_filter,attributes)[0].get_attributes()
        if 'cinesdaterenew' in uid_attrz:
            date_renew = self.converter.to_display_mode(
                uid_attrz['cinesdaterenew'][0], field.fieldtype.type
            )
        else:
            date_renew = ''
        return date_renew

    def add_ppolicy(self, cn):
        dn = "cn={0},ou=policies,ou=system,{1}".format(
            cn,
            self.ldap_search_base)
        add_record=[('cn',[cn]),
                    ('pwdAttribute', ['userPassword']),
                    ('objectClass', ['device', 'pwdPolicy'])]
        if self.ldap.add(dn, add_record):
            flash(u'PPolicy {0} ajoutée'.format(cn))
