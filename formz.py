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
    cinesQuotaSizeSoftTempExpire = TextField(
        u'Date d\'expiration pour cinesQuotaSizeSoftTemp')
    cinesQuotaInodeHardTemp = FormField(InodeQuotaForm)
    cinesQuotaInodeSoftTemp = FormField(InodeQuotaForm)
    cinesQuotaInodeTempExpire = TextField(
        u'Date d\'expiration pour cinesQuotaInodeSoftTemp')

class UserzFileForm(Form):
    userz_file = FileField('Fichier contenant les logins utilisateur')
