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
    ip = TextField('Adresse IP (cinesIpClient)')
    user_disabled = BooleanField('Uniquement les comptes inactifs : ')

class SearchGroupForm(Form):
    gid_number = TextField(u'Numéro du groupe (gidNumber)')
    cn = TextField(u'Nom du groupe (cn)')
    description = TextField(u'Description')

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
                       choices=[(1, 'Ko'),
                                (1000, 'Mo'),
                                (1000000, 'Go'),
                                (1000000000, 'Po')],
                       default=1000,
                       coerce=int)

class InodeQuotaForm(Form):
    value = TextField('Valeur')
    unit = SelectField(u'Unité',
                       choices=[(1000, 'Millier'),(1000000, 'Million'), (1000000000, 'Milliard')],
                       default=1000,
                       coerce=int)


class EditDefaultQuotaForm(Form):
    cinesQuotaSizeHard = FormField(SizeQuotaForm,
                                   label=u'Quota taille maximale autorisée avant blocage écriture (cinesQuotaSizeHard)')
    cinesQuotaSizeSoft = FormField(SizeQuotaForm,
                                    label=u'Quota taille maximale autorise avant avertissement (cinesQuotaSizeSoft)')
    cinesQuotaInodeHard = FormField(InodeQuotaForm,
                                    label=u'Quota nombre inodes maximal autorisé avant blocage écriture (cinesQuotaInodeHard)')
    cinesQuotaInodeSoft = FormField(InodeQuotaForm,
                                    label=u'Quota nombre inodes maximal autorisé avant avertissement (cinesQuotaInodeSoft)')

class EditQuotaForm(Form):
    cinesQuotaSizeHard = FormField(SizeQuotaForm,
                                   label=u'Quota taille maximale autorisée avant blocage écriture (cinesQuotaSizeHard)')
    cinesQuotaSizeSoft = FormField(SizeQuotaForm,
                                    label=u'Quota taille maximale autorise avant avertissement (cinesQuotaSizeSoft)')
    cinesQuotaInodeHard = FormField(InodeQuotaForm,
                                    label=u'Quota nombre inodes maximal autorisé avant blocage écriture (cinesQuotaInodeHard)')
    cinesQuotaInodeSoft = FormField(InodeQuotaForm,
                                    label=u'Quota nombre inodes maximal autorisé avant avertissement (cinesQuotaInodeSoft)')
    cinesQuotaSizeHardTemp = FormField(SizeQuotaForm,
                                       label=u'Valeur temporaire de quota (taille) maximale avant blocage écriture (cinesQuotaSizeHardTemp)')
    cinesQuotaSizeSoftTemp = FormField(SizeQuotaForm,
                                       label=u'Valeur temporaire de quota (taille) maximale avant avertissement (cinesQuotaSizeSoftTemp)')
    cinesQuotaSizeTempExpire = DateField(
        label=u'Date expiration du quota temporaire (cinesQuotaSizeTempExpire)')
    cinesQuotaInodeHardTemp = FormField(InodeQuotaForm,
                                        label=u'Valeur temporaire de quota (nombre inodes) maximale avant blocage ecriture (cinesQuotaInodeHardTemp)')
    cinesQuotaInodeSoftTemp = FormField(InodeQuotaForm,
                                        label=u'Valeur temporaire de quota (nombre inodes) maximale avant avertissement (cinesQuotaInodeSoftTemp)')
    cinesQuotaInodeTempExpire = DateField(
        label=u'Date expiration du quota temporaire (cinesQuotaInodeTempExpire)')

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
    group = SelectField(u'Groupe')
    uid = TextField(u'Login (uid)')

class AddPolicyForm(Form):
    cn = TextField(u'Common Name')

class SelectGroupTypeForm(Form):
    group_type = SelectField(u'Type de groupe')

class AddGenericGroupForm(Form):
    cn = TextField(u'Nom (cn)')
    filesystem = SelectField(u'Système de fichier',default='DEFAUT')
    description = TextField(u'Description')


class AddC4GroupForm(Form):
    cn = SelectField(u'Nom (cn)')
    filesystem = SelectField(u'Système de fichier',default='DEFAUT')
    description = TextField(u'Description')

class FilesystemForm(Form):
    label = TextField(u'Libellé du système de fichiers')
    description = TextField(u'Description du système de fichiers')

class ShellForm(Form):
    label = TextField(u'Libellé du shell')
    path = TextField(u'Emplacement du shell')
