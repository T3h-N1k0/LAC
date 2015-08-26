from lac import app
from wtforms import Form, BooleanField, TextField, SelectMultipleField, SelectField, PasswordField,validators, FormField, FieldList, DateField, TextAreaField
from datetime import datetime, timedelta, date
from lac.data_modelz import Shell

def get_shellz_choices():
    shellz = Shell.query.all()
    shellz_choices = [ (shell.path, shell.label) for shell in shellz ]
    return shellz_choices

def append_field_to_form(field, form):
    if field.fieldtype.type == 'Text':
        setattr(form,
                field.label,
                TextField(field.description))
    elif field.fieldtype.type in app.config['DATE_FIELDTYPEZ']:
        setattr(form,
                field.label,
                DateField(field.description,
                          format=app.config['DATE_FORMAT']))
    elif  field.fieldtype.type == 'GIDNumber':
        setattr(form,
                field.label,
                SelectField(field.description,
                            choices=ldap.get_posix_groupz_choices()))
    elif field.fieldtype.type == 'Submission':
        setattr(form,
                field.label,
                FormField(EditSubmissionForm))
    elif  field.fieldtype.type == 'Shell':
        setattr(form,
                field.label,
                SelectField(field.description,
                            choices=get_shellz_choices()))
    elif  field.fieldtype.type == 'Filesystem':
        setattr(form,
                field.label,
                SelectField(field.description,
                            choices=get_filesystem_choices()))
    elif  field.fieldtype.type == 'Checkbox':
        setattr(form,
                field.label,
                BooleanField(field.description))
    elif  field.fieldtype.type == 'TextArea':
        setattr(form,
                field.label,
                TextAreaField(field.description))

def append_fieldlist_to_form(field, form, branch=None):
    if field.fieldtype.type == 'Text':
        setattr(form,
                field.label,
                FieldList(TextField(field.description)))
    elif field.fieldtype.type in app.config['DATE_FIELDTYPEZ']:
        setattr(form,
                field.label,
                FieldList(DateField(field.description,
                                    format=app.config['DATE_FORMAT'])))
    elif  field.fieldtype.type == 'GIDNumber':
        setattr(form,
                field.label,
                FieldList(SelectField(
                    field.description,
                    choices=ldap.get_posix_groupz_choices(ldap.get_group_branch(branch))
                )))
    elif  field.fieldtype.type == 'Shell':
        setattr(form,
                field.label,
                FieldList(SelectField(field.description,
                                      choices=get_shellz_choices())))
    elif  field.fieldtype.type == 'Filesystem':
        setattr(form,
                field.label,
                FieldList(SelectField(field.description,
                                      choices=get_filesystem_choices())))
    elif  field.fieldtype.type == 'Checkbox':
        setattr(form,
                field.label,
                FieldList(BooleanField(field.description)))
    elif  field.fieldtype.type == 'TextArea':
        setattr(form,
                field.label,
                FieldList(TextAreaField(field.description)))
