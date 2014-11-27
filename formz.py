# coding: utf-8
from wtforms import Form, BooleanField, TextField, SelectMultipleField, SelectField, PasswordField,validators, FormField, FieldList, DateField, FileField, HiddenField
### Formz

class SearchUserForm(Form):
    uid_number = TextField(u'Numéro du compte (uidNumber)')
    sn = TextField('Nom d\'utilisateur (sn)')
    uid = TextField('Login (uid)')
    mail = TextField('Courriel (mail)')
    user_type = SelectField(u'Type d\'utilisateur',
                            choices=[('','Tous'),
                                     ('ccc','Compte C.C.C.'),
                                     ('cines','Compte CINES'),
                                     ('deci','Compte DECI'),
                                     ('sam','Compte S.A.M.'),
                                     ('autre','Compte divers')])

    user_disabled = BooleanField('Uniquement les comptes inactifs : ')


class ChangePassForm(Form):
    new_pass = PasswordField('Nouveau mot de passe', [
        validators.Required(),
        validators.EqualTo('new_pass_confirm',
                           message='Les mots de passe doivent correspondre'
                       )
    ])
    new_pass_confirm = PasswordField('Confirmation du mot de passe')

class SelectOCForm(Form):
    available_oc = SelectMultipleField(u'Classes disponibles', coerce=int)
    selected_oc = SelectMultipleField(u'Classes selectionnées', coerce=int)

class SelectAttrForm(Form):
    available_attr = SelectMultipleField(u'Attributs disponibles', coerce=int)
    selected_attr = SelectMultipleField(u'Attributs selectionnés', coerce=int)

class SelectMemberzForm(Form):
    available_memberz = SelectMultipleField(u'Membres disponibles')
    selected_memberz = SelectMultipleField(u'Membres selectionnés')

class SelectGroupzForm(Form):
    available_groupz = SelectMultipleField(u'Groupes disponibles')
    selected_groupz = SelectMultipleField(u'Groupes selectionnés')

class CreateQuotaForm(Form):
    group = SelectField(u'Groupe')
    default_quota = SelectField(u'Quota par défaut')

class EditPageViewForm(Form):
    oc_form = FormField(SelectOCForm)
    attr_form = FormField(SelectAttrForm)

class AddPageViewForm(Form):
    label = TextField(u'Libellé de la vue')
    description = TextField('Description de la vue')

class EditGroupViewForm(Form):
    attr_form = FormField(SelectAttrForm)

class EditGroupBaseForm(Form):
    # group_form = FormField(SelectGroupzForm)
    action = SelectField('Action',
                         choices=[(0, 'Ajout'), (1, 'Modification')],
                         default=1)
    submited = HiddenField(default="False")
class EditSubmissionForm(Form):
    wrk_group = SelectField(u'Groupe de travail')
    member = BooleanField('Membre')
    submission = BooleanField(u'Autorisé à la soumission')

class EditGroupSubmissionForm(Form):
    submission_form = FormField(EditSubmissionForm)
    group_form = FormField(SelectGroupzForm)

class SizeQuotaForm(Form):
    value = TextField('Valeur')
    unit = SelectField(u'Unité',
                       choices=[(1, 'ko'), (1000, 'Mo'), (1000000, 'Go')],
                       default=1000,
                       coerce=int)

class InodeQuotaForm(Form):
    value = TextField('Valeur')
    unit = SelectField(u'Unité',
                       choices=[(1000000, 'Million'), (1000000000, 'Milliard')],
                       default=1000000,
                       coerce=int)


class EditDefaultQuotaForm(Form):
    cinesQuotaSizeHard = FormField(SizeQuotaForm)
    cinesQuotaSizeSoft = FormField(SizeQuotaForm)
    cinesQuotaInodeHard = FormField(InodeQuotaForm)
    cinesQuotaInodeSoft = FormField(InodeQuotaForm)

class EditQuotaForm(Form):
    cinesQuotaSizeHardTemp = FormField(SizeQuotaForm)
    cinesQuotaSizeSoftTemp = FormField(SizeQuotaForm)
    cinesQuotaSizeTempExpire = DateField(
        u'Date d\'expiration pour cinesQuotaSizeSoftTemp')
    cinesQuotaInodeHardTemp = FormField(InodeQuotaForm)
    cinesQuotaInodeSoftTemp = FormField(InodeQuotaForm)
    cinesQuotaInodeTempExpire = DateField(
        u'Date d\'expiration pour cinesQuotaInodeSoftTemp')

class UserzFileForm(Form):
    userz_file = FileField('Fichier contenant les logins utilisateur')

class AddObjectTypeForm(Form):
    label = TextField(u'\'ou\' associée à ce type d\'objet')

class LDAPObjectTypeForm(Form):
    label = TextField(u'\'ou\' associée à ce type d\'objet')
    description = TextField(u'Description')
    ranges = TextField(
        u'Ranges d\'ID associées à ce type (au format "n-p;n-p;...")')
    apply_to = SelectField(u'Appliquée à un',
                           choices=[('group', 'Groupe'),
                                    ('user', 'Utilisateur')],
                           default='group')
    object_classes = FormField(SelectOCForm)
    ppolicy = SelectField(u'Ppolicy', choices=[], default='')
    set_ppolicy = BooleanField(u'Appliquer la ppolicy aux objets déjà créés')

class AddUserForm(Form):
    # display_type = SelectField(u'Type d\'affichage pour le compte')
    group = SelectField(u'Groupe')
    ldap_object_type = SelectField(u'Type d\'objet LDAP', coerce=int)
    uid = TextField(u'Login (uid)')
    cn = TextField(u'Common Name')

class AddPolicyForm(Form):
    cn = TextField(u'Common Name')

class AddGroupForm(Form):
    cn = TextField(u'Nom (cn)')
    filesystem = SelectField(u'Système de fichier',default='DEFAUT')
    description = TextField(u'Description')
    group_type = SelectField(u'Type de groupe')


class FilesystemForm(Form):
    label = TextField(u'Libellé du système de fichiers')
    description = TextField(u'Description du système de fichiers')

class ShellForm(Form):
    label = TextField(u'Emplacement du shell')
    description = TextField(u'Description du shell')
