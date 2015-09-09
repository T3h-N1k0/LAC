# coding: utf-8

from flask import current_app, request, flash, render_template
from wtforms import Form, BooleanField, TextField, SelectMultipleField, SelectField, PasswordField,validators, FormField, FieldList, DateField, TextAreaField
from lac.formz import *
import lac.helperz
from data_modelz import *

class FormManager(object):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['form_manager'] = self
        self.cache = app.extensions['cache']
        self.ldap = app.extensions['ldap']
        self.converter = app.extensions['converter']


    def get_shellz_choices(self):
        shellz = Shell.query.all()
        shellz_choices = [ (shell.path, shell.label) for shell in shellz ]
        return shellz_choices

    def get_posix_groupz_choices(self, branch=None):
        ldap_groupz = self.ldap.get_posix_groupz(branch)
        ldap_groupz_list = [('', '---')]
        for group in ldap_groupz:
            group_attrz = group.get_attributes()
            ldap_groupz_list.append((group_attrz['gidNumber'][0],
                                 group_attrz['cn'][0]))
        sorted_by_second = sorted(ldap_groupz_list, key=lambda tup: tup[1])
        return sorted_by_second

    def get_filesystem_choices(self):
        filesystems = Filesystem.query.all()
        fs_choices = [ (fs.label, fs.description) for fs in filesystems]
        return fs_choices

    def append_field_to_form(self, field, form):
        if field.fieldtype.type == 'Text':
            setattr(form,
                    field.label,
                    TextField(field.description))
        elif field.fieldtype.type in self.app.config['DATE_FIELDTYPEZ']:
            setattr(form,
                    field.label,
                    DateField(field.description,
                              format=self.app.config['DATE_FORMAT']))
        elif  field.fieldtype.type == 'GIDNumber':
            setattr(form,
                    field.label,
                    SelectField(field.description,
                                choices=self.get_posix_groupz_choices()))
        elif field.fieldtype.type == 'Submission':
            setattr(form,
                    field.label,
                    FormField(EditSubmissionForm))
        elif  field.fieldtype.type == 'Shell':
            setattr(form,
                    field.label,
                    SelectField(field.description,
                                choices=self.get_shellz_choices()))
        elif  field.fieldtype.type == 'Filesystem':
            setattr(form,
                    field.label,
                    SelectField(field.description,
                                choices=self.get_filesystem_choices()))
        elif  field.fieldtype.type == 'Checkbox':
            setattr(form,
                    field.label,
                    BooleanField(field.description))
        elif  field.fieldtype.type == 'TextArea':
            setattr(form,
                    field.label,
                    TextAreaField(field.description))

    def append_fieldlist_to_form(self, field, form, branch=None):
        if field.fieldtype.type == 'Text':
            setattr(form,
                    field.label,
                    FieldList(TextField(field.description)))
        elif field.fieldtype.type in self.app.config['DATE_FIELDTYPEZ']:
            setattr(form,
                    field.label,
                    FieldList(DateField(field.description,
                                        format=self.app.config['DATE_FORMAT'])))
        elif  field.fieldtype.type == 'GIDNumber':
            setattr(form,
                    field.label,
                    FieldList(SelectField(
                        field.description,
                        choices=self.get_posix_groupz_choices(
                            self.ldap.get_group_branch(branch))
                    )))
        elif  field.fieldtype.type == 'Shell':
            setattr(form,
                    field.label,
                    FieldList(SelectField(field.description,
                                          choices=self.get_shellz_choices())))
        elif  field.fieldtype.type == 'Filesystem':
            setattr(form,
                    field.label,
                    FieldList(SelectField(field.description,
                                          choices=self.get_filesystem_choices())
                          ))
        elif  field.fieldtype.type == 'Checkbox':
            setattr(form,
                    field.label,
                    FieldList(BooleanField(field.description)))
        elif  field.fieldtype.type == 'TextArea':
            setattr(form,
                    field.label,
                    FieldList(TextAreaField(field.description)))


    def set_default_quota_form_values(self, form, storage):
        default_size_unit = form.cinesQuotaSizeHard.unit.default
        default_inode_unit = form.cinesQuotaInodeHard.unit.default
        cinesQuotaSizeHard = int(
            storage['cinesQuotaSizeHard'][0]
        ) / default_size_unit
        cinesQuotaSizeSoft = int(
            storage['cinesQuotaSizeSoft'][0]
        ) / default_size_unit
        cinesQuotaInodeHard = int(
            storage['cinesQuotaInodeHard'][0]
        ) / default_inode_unit
        cinesQuotaInodeSoft = int(
            storage['cinesQuotaInodeSoft'][0]
        ) / default_inode_unit
        form.cinesQuotaSizeHard.value.data= cinesQuotaSizeHard
        form.cinesQuotaSizeSoft.value.data= cinesQuotaSizeSoft
        form.cinesQuotaInodeHard.value.data= cinesQuotaInodeHard
        form.cinesQuotaInodeSoft.value.data= cinesQuotaInodeSoft

    def get_default_quota_form_value(self,
                                     storage,
                                     default_storage,
                                     form,
                                     field_name):
        default_inode_unit = form.cinesQuotaInodeHardTemp.unit.default
        default_size_unit = form.cinesQuotaSizeHardTemp.unit.default

        if field_name in storage:
            stored_value = storage[field_name][0]
            default = False
        else:
            stored_value = default_storage[
                self.app.config['QUOTA_FIELDZ'][field_name]['default']
            ][0]
            default = True

        display_value = int(stored_value) / (
            default_size_unit if app.config[
                'QUOTA_FIELDZ'][field_name]['type'] == 'size'
            else default_inode_unit
        )

        return (display_value, default)

    def set_quota_form_values(self, form, storage):
        default_storage_cn = storage['cn'][0].split('.')[0]
        default_storage = self.ldap.get_default_storage(
            default_storage_cn).get_attributes()
        date_now = datetime.now()

        default_fieldz = []
        cinesQuotaSizeHard = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaSizeHard')
        cinesQuotaSizeSoft = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaSizeSoft')
        cinesQuotaInodeHard = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaInodeHard')
        cinesQuotaInodeSoft = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaInodeSoft')
        cinesQuotaSizeHardTemp = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaSizeHardTemp')
        cinesQuotaSizeSoftTemp = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaSizeSoftTemp')
        cinesQuotaInodeHardTemp = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaInodeHardTemp')
        cinesQuotaInodeSoftTemp = self.get_default_quota_form_value(
            storage,
            default_storage,
            form,
            'cinesQuotaInodeSoftTemp')
        cinesQuotaSizeTempExpire = datetime.fromtimestamp(
            float(storage['cinesQuotaSizeTempExpire'][0])
        ) if 'cinesQuotaSizeTempExpire' in storage else date_now
        cinesQuotaInodeTempExpire =  datetime.fromtimestamp(
            float(storage['cinesQuotaInodeTempExpire'][0])
        ) if 'cinesQuotaInodeTempExpire' in storage else date_now

        form.cinesQuotaSizeHard.value.data= cinesQuotaSizeHard[0]
        form.cinesQuotaSizeSoft.value.data= cinesQuotaSizeSoft[0]
        form.cinesQuotaInodeHard.value.data= cinesQuotaInodeHard[0]
        form.cinesQuotaInodeSoft.value.data= cinesQuotaInodeSoft[0]
        form.cinesQuotaSizeHardTemp.value.data= cinesQuotaSizeHardTemp[0]
        form.cinesQuotaSizeSoftTemp.value.data= cinesQuotaSizeSoftTemp[0]
        form.cinesQuotaInodeHardTemp.value.data= cinesQuotaInodeHardTemp[0]
        form.cinesQuotaInodeSoftTemp.value.data= cinesQuotaInodeSoftTemp[0]
        form.cinesQuotaSizeTempExpire.data = cinesQuotaSizeTempExpire
        form.cinesQuotaInodeTempExpire.data = cinesQuotaInodeTempExpire
        if cinesQuotaSizeHard[1]:
            default_fieldz.append('cinesQuotaSizeHard')
        if cinesQuotaSizeSoft[1]:
            default_fieldz.append('cinesQuotaSizeSoft')
        if cinesQuotaInodeHard[1]:
            default_fieldz.append('cinesQuotaInodeHard')
        if cinesQuotaInodeSoft[1]:
            default_fieldz.append('cinesQuotaInodeSoft')
        if cinesQuotaSizeHardTemp[1]:
            default_fieldz.append('cinesQuotaSizeHardTemp')
        if cinesQuotaSizeSoftTemp[1]:
            default_fieldz.append('cinesQuotaSizeSoftTemp')
        if cinesQuotaInodeHardTemp[1]:
             default_fieldz.append('cinesQuotaInodeHardTemp')
        if cinesQuotaInodeSoftTemp[1]:
            default_fieldz.append('cinesQuotaInodeSoftTemp')
        return default_fieldz

    def get_quota_value_from_form(self, form, quota):
        field = getattr(form, quota)
        value = str(
            int(
                field.value.data
            ) * int(
                field.unit.data)
        ).encode('utf-8')
        return value

    def populate_lac_admin_choices(self, form):
        memberz = [ get_uid_from_dn(dn) for dn in ldap.get_lac_admin_memberz() ]
        all_userz = get_all_users()
        selected_memberz = [ (uid, uid) for uid in memberz ]
        available_userz = [ (user.get_attributes()['uid'][0],
                             user.get_attributes()['uid'][0])
                            for user in all_userz
                            if user.get_attributes()['uid'][0] not in memberz]
        form.available_memberz.choices = available_userz
        form.selected_memberz.choices = selected_memberz


    def populate_ldap_admin_choices(form):
        memberz = [get_uid_from_dn(dn) for dn in ldap.get_ldap_admin_memberz()]
        all_userz = get_all_users()
        selected_memberz = [ (uid, uid) for uid in memberz ]
        available_userz = [ (user.get_attributes()['uid'][0],
                             user.get_attributes()['uid'][0])
                            for user in all_userz
                            if user.get_attributes()['uid'][0] not in memberz]
        form.available_memberz.choices = available_userz
        form.selected_memberz.choices = selected_memberz


    def get_c4_groupz_choices():
        existing_groupz = [
            group.get_attributes()['cn'][0] for group in get_all_groups()]
        c4_projectz = C4Projet.query.all()
        c4_groupz_choices = [(project.code_projet, project.code_projet)
                             for project in c4_projectz
                             if project.code_projet not in existing_groupz]
        c4_groupz_choices.insert(0, ('', '---'))

        return c4_groupz_choices


    def set_validators_to_form_field(self, form, field, validators):
        form_field_kwargs = getattr(
            getattr(form, field),'kwargs')


    def get_display_mode_choices(self):
        field_types = FieldType.query.all()
        display_mode_choices = [(field_type.id, field_type.type)
                                for field_type in field_types]
        return display_mode_choices

    def get_available_unic_attr_choices(self, page_unic_attr_id_list):
        available_unic_attr = LDAPAttribute.query.all()
        available_unic_attr_choices = filter(
            None, [(attr.id,attr.label)
                   if attr.id not in page_unic_attr_id_list
                   and attr is not None
                   else None for attr in available_unic_attr]
        )
        return available_unic_attr_choices

    def get_available_oc_choices(self, selected_oc_id_list):
        available_oc = LDAPObjectClass.query.all()
        available_oc_choices = filter(None, [(oc.id,oc.label)
                                          if oc.id not in selected_oc_id_list
                                          and oc is not None
                                          else None for oc in available_oc])
        return available_oc_choices

    def get_page_oc_choices(self, page):
        page_oc_list = PageObjectClass.query.filter_by(page_id=page.id).all()
        select_oc_choices = filter(None,[(oc.ldapobjectclass.id,
                                          oc.ldapobjectclass.label)
                                         for oc in page_oc_list ])
        return select_oc_choices

    def get_ot_oc_choices(self, object_type):
        ot_oc_list = LDAPObjectTypeObjectClass.query.filter_by(
            ldapobjecttype_id=object_type.id).all()
        select_oc_choices = filter(None,[(oc.ldapobjectclass.id,
                                          oc.ldapobjectclass.label)
                                         for oc in ot_oc_list ])
        return select_oc_choices


    def set_edit_ppolicy_form_values(self, form, fieldz_namez, ppolicy_cn=None):
        if ppolicy_cn:
            ppolicy_attz = self.ldap.get_ppolicy(ppolicy_cn).get_attributes()
        else:
            ppolicy_attz = {}

        for field_name in fieldz_namez:
            field = getattr(form, field_name)
            if field_name in ppolicy_attz and len(ppolicy_attz[field_name]):
                for field_value in ppolicy_attz[field_name]:
                    field.data = field_value.decode('utf-8')


    def generate_edit_page_admin_form(self, page):

        # selection des attributs hérités des object classes
        select_oc_choices = self.get_page_oc_choices(page)
        page_oc_id_list = [oc[0] for oc in select_oc_choices]
        page_oc_attr_list = get_attr_from_oc_id_list(page_oc_id_list)
        page_oc_attr_id_list = [ a.id for a in page_oc_attr_list ]
        # Sélection des attributs indépendants des object classes
        page_unic_attr_list = Field.query.filter(
            Field.page_id==page.id,
            ~Field.ldapattribute_id.in_(page_oc_attr_id_list)
        ).all()
        page_unic_attr_id_list = [attr.id for attr in page_unic_attr_list]
        select_unic_attr_choices = filter(None, [(attr.id,
                                                  attr.label)
                                                 for attr in page_unic_attr_list ])
        attributes = set(page_oc_attr_list)
        attributes.update(
            [attr.ldapattribute for attr in page_unic_attr_list]
        )
        if attributes is not None:
            attr_label_list = sorted(set([ attr.label for attr in attributes ]))
        else:
            attr_label_list = set([])
        class EditPageForm(EditPageViewForm):
            pass
        for label in attr_label_list:
            existing_field = Field.query.filter_by(label=label,
                                                   page_id=page.id).first()
            class EditFieldForm(Form):
                display = BooleanField('Affichage du champ ',
                                       default=existing_field.display
                                       if existing_field is not None else None)
                edit = BooleanField(u'Champ éditable ',
                                       default=existing_field.edit
                                       if existing_field is not None else None)
                restrict = BooleanField(u'Champ restreint aux admins',
                                        default=existing_field.restrict
                                       if existing_field is not None else None)
                multivalue = BooleanField(u'Champ multi-valeur',
                                        default=existing_field.multivalue
                                       if existing_field is not None else None)

                display_mode = SelectField('Mode d\'affichage',
                                           default=existing_field.fieldtype_id
                                           if existing_field is not None else None,
                                           choices=self.get_display_mode_choices())
                desc = TextField(u'Description du champ',
                                 default=existing_field.description
                                 if existing_field is not None else None)
                priority = TextField(u'Priorité',
                                     default=existing_field.priority
                                     if existing_field is not None else None)
                block = SelectField('Bloc',
                                   default=existing_field.block
                                   if existing_field is not None else None,
                                   choices=[
                                       (x, x) for x in list(
                                           ' ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                                   ])
            setattr(EditPageForm, label, FormField(EditFieldForm))
        form = EditPageForm(request.form)
        form.oc_form.available_oc.choices = self.get_available_oc_choices(
            page_oc_id_list
        )
        form.oc_form.selected_oc.choices = select_oc_choices
        form.attr_form.available_attr.choices = self.get_available_unic_attr_choices(
            page_unic_attr_id_list
        )
        form.attr_form.selected_attr.choices = select_unic_attr_choices
        return {'form' : form,
                'attr_label_list': attr_label_list,
                'page_oc_id_list': page_oc_id_list,
                'page_unic_attr_id_list': page_unic_attr_id_list}


    def generate_edit_group_submission(self):
        form = EditGroupSubmissionForm(request.form)
        form.submission_form.wrk_group.choices = [
            (group, group)
            for group in ldap.get_submission_groupz_list()
        ]
        form.group_form.available_groupz.choices = fm.get_posix_groupz_choices()
        form.group_form.selected_groupz.choices = []
        return form

    def generate_kustom_batch_edit_form(self, page, attributez):
        page_fieldz = dict(
            (row.label, row)
            for row in Field.query.filter_by(page_id = page.id).all()
        )

        class EditGroupForm(EditGroupBaseForm):
            pass

        for field_id in attributez:
            print('field_id {0}'.format(field_id))
            field = Field.query.filter_by(
                id = field_id
            ).first()
            self.append_field_to_form(field,
                                 EditGroupForm)

        form = EditGroupForm(request.form)
        return form

    def generate_edit_group_form(self, page):
        page_fieldz = Field.query.filter_by(page_id = page.id).all()

        class EditGroupForm(EditGroupBaseForm):
            pass

        for field in page_fieldz:
            self.append_fieldlist_to_form(field,
                                     EditGroupForm)
        return EditGroupForm(request.form)

    def generate_select_work_group_form(self, uid):
        actual_work_groupz = self.ldap.get_work_groupz_from_member_uid(uid)
        available_work_groupz = self.ldap.get_work_groupz()
        selected_choices = [(group, group) for group in actual_work_groupz]
        available_choices = [(group, group) for group in available_work_groupz
                             if group not in actual_work_groupz]
        form = SelectGroupzForm(request.form)
        form.available_groupz.choices = available_choices
        form.selected_groupz.choices = selected_choices
        return form

    def generate_edit_user_form_class(self, page):
        page_fieldz = Field.query.filter_by(page_id = page.id,
                                            edit = True).all()
        class EditForm(Form):
            wrk_groupz = FormField(SelectGroupzForm, label=u"Groupes de travail")
        for field in page_fieldz:
            self.append_fieldlist_to_form(field, EditForm, page.label)
        return EditForm

    def generate_add_user_form_class(self, page):
        page_fieldz = Field.query.filter_by(page_id = page.id,
                                            edit = True).all()
        uid = TextField(u'Login (uid)')
        class EditForm(Form):
            wrk_groupz = FormField(SelectGroupzForm, label=u"Groupes de travail")
        for field in page_fieldz:
            self.append_fieldlist_to_form(field, EditForm, page.label)
        setattr(EditForm,
                "uid",
                TextField("Login"))
        return EditForm

    def generate_edit_ppolicy_form_class(self, page):
        page_fieldz = Field.query.filter_by(page_id = page.id,
                                            edit = True).all()
        class EditForm(Form):
            pass
        for field in page_fieldz:
            self.append_field_to_form(field, EditForm)
        return EditForm

    def set_edit_ldap_object_type_form_valuez(self, ldap_object_type, form):
        selected_oc_choices = self.get_ot_oc_choices(ldap_object_type)
        ot_oc_id_list = [oc[0] for oc in selected_oc_choices]
        ppolicy_choices = [(ppolicy.get_attributes()['cn'][0],
                            ppolicy.get_attributes()['cn'][0])
                           for ppolicy in self.ldap.get_all_ppolicies()
        ]
        ppolicy_choices.append(('', 'Aucune'))
        available_oc_choices = filter(
            None,
            [(oc.id,oc.label)
             if oc.id not in ot_oc_id_list
             and oc is not None
             else None for oc in LDAPObjectClass.query.all()]
        )
        form.label.data = ldap_object_type.label
        form.description.data = ldap_object_type.description
        form.ranges.data = ldap_object_type.ranges
        form.apply_to.data = ldap_object_type.apply_to
        form.ppolicy.data = ldap_object_type.ppolicy
        form.ppolicy.choices = ppolicy_choices
        form.object_classes.selected_oc.choices = selected_oc_choices
        form.object_classes.available_oc.choices = available_oc_choices
        return form

    def generate_edit_file_view_form(self, page):
        view_form = EditGroupViewForm(request.form)
        view_form.attr_form.available_attr.choices = [
            (attr.id, attr.label)
            for attr in Field.query.filter_by(page_id = page.id).all()
        ]
        view_form.attr_form.selected_attr.choices = []

    def generate_create_quota_form(self):
        form = CreateQuotaForm(request.form)
        default_storagez = self.ldap.get_default_storage_list()
        form.default_quota.choices = [
            (storage.get_attributes()['cn'][0],
             storage.get_attributes()['cn'][0])
            for storage in default_storagez ]
        form.group.choices = self.get_posix_groupz_choices()
        return form

    def set_edit_group_form_values(self, form, fieldz, branch, cn=None):
        if cn:
            ldap_filter='(cn={0})'.format(cn)
            attributes=['*','+']
            base_dn='ou={0},ou=groupePosix,{1}'.format(
                branch,
                self.app.config['LDAP_SEARCH_BASE']
            )
            group_attributez = self.ldap.search(
                ldap_filter=ldap_filter,
                attributes=attributes,
                base_dn=base_dn)[0].get_attributes()
        else:
            group_attributez = {}
        for field in fieldz:
            form_field = getattr(form, field.label)
            while(len(form_field.entries)>0):
                form_field.pop_entry()
            if field.label in group_attributez and len(
                    group_attributez[field.label]):
                for field_value in group_attributez[field.label]:
                    form_field.append_entry(
                        self.converter.to_display_mode(field_value,
                                                field.fieldtype.type))
            else:
                form_field.append_entry()


    def set_edit_user_form_values(self, form, fieldz, uid=None):
        if uid:
            actual_work_groupz = self.ldap.get_work_groupz_from_member_uid(uid)
        else:
            actual_work_groupz = []
        available_work_groupz = self.ldap.get_work_groupz()
        selected_choices = [(group, group) for group in actual_work_groupz]
        available_choices = [(group, group) for group in available_work_groupz
                             if group not in actual_work_groupz]
        form.wrk_groupz.available_groupz.choices = available_choices
        form.wrk_groupz.selected_groupz.choices = selected_choices

        if uid:
            uid_attributez = self.ldap.get_uid_detailz(uid).get_attributes()
        else:
            uid_attributez = {}

        for field in fieldz:
            form_field = getattr(form, field.label)
            while(len(form_field.entries)>0):
                form_field.pop_entry()
            if field.label in uid_attributez and len(uid_attributez[field.label]):
                if field.label == "cinesIpClient":
                    uid_attributez[field.label] = [
                        ip_address
                        for ip_address in uid_attributez[field.label][0].split(";")
                    ]
                for field_value in uid_attributez[field.label]:
                    if field.label != 'gidNumber':
                        form_field.append_entry(
                            self.converter.to_display_mode(field_value,
                                                      field.fieldtype.type))
                    else:
                        form_field.append_entry(field_value)
            else:
                form_field.append_entry()
