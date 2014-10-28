# -*- coding: utf-8 -*-
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from flask.ext.ldap import LDAP, login_required
from flask.ext.sqlalchemy import SQLAlchemy
#from flask_bootstrap import Bootstrap
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from wtforms import Form, BooleanField, TextField, SelectMultipleField, SelectField, PasswordField,validators, FormField, FieldList
from datetime import datetime, timedelta
import time
from pytz import timezone
import pytz
import ldaphelper
#import upsert
from ldap_decoder import PythonLDAPDecoder
from ldap import SCOPE_BASE,schema
import redis

__author__ = "Nicolas CHATELAIN"
__copyright__ = "Copyright 2014, Nicolas CHATELAIN @ CINES"
__license__ = "GPL"



app = Flask(__name__)
ldap = LDAP(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://lac:omgwtfbbq@localhost/lac'
db = SQLAlchemy(app)
#Bootstrap(app)
utc = pytz.utc
r = redis.Redis('localhost')

# Add login URL associated with login function
app.add_url_rule('/login', 'login', ldap.login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', ldap.logout, methods=['GET', 'POST'])


### Data Model


# One to many : LDAPObjectClass (1)---(n) LDAPAttributes
# Many to one : LDAPObjectClass (n)---(1) PageObjectClass
class LDAPObjectClass(db.Model):
    __tablename__ = 'ldapobjectclass'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), unique=True)

    ldapobjectclassattributes = db.relationship("LDAPObjectClassAttribute",
                                     backref="ldapobjectclass",
                                     lazy='dynamic')

    pageobjectclasses = db.relationship("PageObjectClass",
                                     backref="ldapobjectclass",
                                     lazy='dynamic')

    def __init__(self, label):
        self.label = label

    def __repr__(self):
        return '<LDAPObjectClass %r>' % self.label

# Many to one : LDAPObjectClassAttribute (n)---(1) LDAPObjectClass
# Many to one : LDAPObjectClassAttribute (n)---(1) LDAPAttribute
class LDAPObjectClassAttribute(db.Model):
    __tablename__ = 'ldapobjectclassattribute'
    id = db.Column(db.Integer, primary_key=True)
    mandatory = db.Column(db.Boolean())

    ldapobjectclass_id = Column(Integer, ForeignKey('ldapobjectclass.id',
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"))
    ldapattribute_id = Column(Integer, ForeignKey('ldapattribute.id',
                                         onupdate="CASCADE",
                                         ondelete="CASCADE"))

    def __init__(self, mandatory, ldapobjectclass, ldapattribute):
        self.mandatory = mandatory
        self.ldapobjectclass = ldapobjectclass
        self.ldapattribute = ldapattribute

#    def __repr__(self):
#        return '<PageObjectClass %r>' % self.label


# Many to one : LDAPAttributes (n)---(1) LDAPObjectClass
# One to many : LDAPAttribute (1)---(n) Field
class LDAPAttribute(db.Model):
    __tablename__ = 'ldapattribute'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), unique=True)

    ldapobjectclassattributes = db.relationship("LDAPObjectClassAttribute",
                                     backref="ldapattribute",
                                     lazy='dynamic')

    fields = db.relationship('Field',
                          backref='ldapattribute',
                          lazy='dynamic')

    def __init__(self, label):
        self.label = label

    def __repr__(self):
        return '<LDAPAttribute %r>' % self.label



# One to many : Page (1)---(n) Field
class Page(db.Model):
    __tablename__ = 'page'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(80))

    fields = db.relationship("Field",
                             backref="page",
                             lazy='dynamic')

    pageobjectclasses = db.relationship("PageObjectClass",
                                     backref="page",
                                     lazy='dynamic')


    def __init__(self, label, description):
        self.label = label
        self.description = description

    def __repr__(self):
        return '<Page %r>' % self.label


# Many to one : PageObjectClass (n)---(1) Page
# Many to one : PageObjectClass (n)---(1) LDAPObjectClass
class PageObjectClass(db.Model):
    __tablename__ = 'pageobjectclass'
    id = db.Column(db.Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('page.id',
                                         onupdate="CASCADE",
                                         ondelete="CASCADE"))
    ldapobjectclass_id = Column(Integer, ForeignKey('ldapobjectclass.id',
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"))

    def __init__(self, page_id, ldapobjectclass_id):
        self.page_id = page_id
        self.ldapobjectclass_id = ldapobjectclass_id

#    def __repr__(self):
#        return '<PageObjectClass %r>' % self.label

# Many to one : Field (n)---(1) Page
# Many to one : Field (n)---(1) LDAPAttribute
# Many to one : Field (n)---(1) FieldType
class Field(db.Model):
    __tablename__ = 'field'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50))
    description = db.Column(db.String(80))
    display = db.Column(db.Boolean())
    edit = db.Column(db.Boolean())
    multivalue = db.Column(db.Boolean())
    restrict = db.Column(db.Boolean())
    display_mode = db.Column(db.String(50), unique=True)

    page_id = Column(Integer, ForeignKey('page.id',
                                         onupdate="CASCADE",
                                         ondelete="CASCADE"))
    ldapattribute_id = Column(Integer, ForeignKey('ldapattribute.id',
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"))

    fieldtype_id = Column(Integer, ForeignKey('fieldtype.id',
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"))

    def __init__(self,
                 label,
                 page,
                 ldapattribute,
                 fieldtype=None,
                 description=None,
                 display=False,
                 edit=False,
                 multivalue=False,
                 restrict=False):
        self.label = label
        self.description = description
        self.display = display
        self.edit = edit
        self.restrict = restrict
        self.page = page
        self.ldapattribute = ldapattribute
        self.fieldtype = fieldtype
        self.multivalue = multivalue

    def __repr__(self):
        return '<Field %r>' % self.label

# One to many : FieldType (1)---(n) Field
class FieldType(db.Model):
    __tablename__ = 'fieldtype'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(80))

    fields = db.relationship('Field',
                          backref='fieldtype',
                          lazy='dynamic')

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
    old_pass = PasswordField('Ancien mot de passe')
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
    available_memberz = SelectMultipleField(u'Membres disponibles', coerce=int)
    selected_memberz = SelectMultipleField(u'Membres selectionnés', coerce=int)

class EditPageViewForm(Form):
    oc_form = FormField(SelectOCForm)
    attr_form = FormField(SelectAttrForm)

class AddPageViewForm(Form):
    label = TextField(u'Libellé de la vue')
    description = TextField('Description de la vue')

class TestForm(Form):
    @classmethod
    def append_field(cls, name, field):
        setattr(cls, name, field)
        return cls


### Routez

@app.route('/')
@login_required
def home():
    populate_people_group_redis()
    populate_grouplist_redis()
    return render_template('home.html',
                           groupz = app.config['PEOPLE_GROUPS'])


@app.route('/search_user', methods=['POST', 'GET'])
@login_required
def search_user():
    """
    Search for a posixAccount in the entire LDAP tree
    """
    form = SearchUserForm(request.form)
    search_resultz=""
    page = Page.query.filter_by(label = "search_user").first()
    page_attributez = Field.query.filter_by(page_id = page.id).all()
    search_attributez = [attr.label.encode('utf-8')
                         for attr in page_attributez]
    print("Search attributez : {0}".format(search_attributez))

    if request.method == 'POST' and form.validate():
        filter_list =[]
        if form.uid_number.data != "" :
            filter_list.append("(uidNumber={0})".format(form.uid_number.data))
        if form.sn.data != "" :
            filter_list.append("(sn={0})".format(form.sn.data))
        if form.uid.data != "" :
            filter_list.append("(uid={0})".format(form.uid.data))
        if form.mail.data != "":
            filter_list.append("(mail={0})".format(form.mail.data))
        if form.user_disabled.data :
            filter_list.append("(shadowExpire=0)")
        if form.user_type.data == "":
            base_dn = "ou=people,{0}".format(app.config['LDAP_SEARCH_BASE'])
        else:
            base_dn = "ou={0},ou=people,{1}".format(form.user_type.data,
                                          app.config['LDAP_SEARCH_BASE'])

        if filter_list != [] :
            ldap_filter = "(&(objectClass=posixAccount){0})".format("".join(
                filter_list
            ))
        else:
            ldap_filter = "(objectClass=posixAccount)"

        print("Search filter : {0}".format(ldap_filter))
        #print("ROOT_DN : {0}".format(base_dn))

        print(search_attributez)
        raw_resultz = ldap.search(ldap_filter=ldap_filter,
                                  attributes=search_attributez,
                                  base_dn=base_dn)

        print(raw_resultz)
        search_resultz = ldaphelper.get_search_results(raw_resultz)

    return render_template('search_user.html',
                           userz=search_resultz,
                           form=form,
                           attributes=page_attributez,
                           timestamp=time.strftime("%Y%m%d_%H%M") )


@app.route('/edit/<uid>', methods=['POST', 'GET'])
@login_required
def change_password(uid):
    """
    Change the password for a given UID
    """
    form=ChangePassForm(request.form)
    if request.method == 'POST' and form.validate():
        ldap.change_passwd(uid, form.old_pass.data, form.new_pass.data)
    return render_template('change_password.html', form=form, uid=uid)


@app.route('/people/<group>')
@login_required
def show_group_memberz(group):
    memberz = get_group_person_memberz(group)
    return render_template('show_group_memberz.html',
                           memberz=memberz,
                           group=group)



@app.route('/details/<uid>')
@login_required
def get_account_detailz(uid):
    detailz = get_uid_detailz(uid)
    print(detailz)
    return render_template('show_detailz.html', account=detailz)


@app.route('/whoami')
@login_required
def get_my_infoz():
    return redirect(url_for('get_account_detailz', uid=session['uid']))


@app.route('/anonymous_detailz/<uid>')
def test(uid):
    return ldap.get_full_dn_from_uid(uid)


@app.route('/show/<page>/<uid>')
@login_required
def show(page, uid):
    print("uid : {0}".format(uid))
    page = Page.query.filter_by(label = page).first()
    page_fieldz = dict(
        (row.label.lower(), row)
        for row in Field.query.filter_by(page_id = page.id).all()
    )
    uid_detailz = ldaphelper.get_search_results(get_uid_detailz(uid))[0]
    return render_template('show_page.html',
                           uid = uid,
                           uid_attributez=uid_detailz.get_attributes(),
                           page_fieldz=page_fieldz)

@app.route('/edit_page/<page_label>', methods=('GET', 'POST'))
@app.route('/edit_page/')
@login_required
def edit_page(page_label=None):
    """
    Customize page attributes
    """
    page = Page.query.filter_by(label=page_label).first()

    if page is None:
        pagez = Page.query.all()
        return render_template('list_viewz.html',
                               pagez=pagez)

    raw_form = generate_edit_page_admin_form(page)
    form = raw_form['form']
    attr_label_list = raw_form['attr_label_list']

    if request.method == 'POST' :
        page_oc_id_list = raw_form['page_oc_id_list']
        page_unic_attr_id_list = raw_form['page_unic_attr_id_list']


        if attr_label_list is not None:
            update_fields_from_edit_page_admin_form(form, attr_label_list, page)
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
                    create_default_field(attr, page)

        if page_unic_attr_id_list is not None:
            # On traite les Attributes supprimées
            for attr_id in page_unic_attr_id_list:
                if attr_id not in form.attr_form.selected_attr.data:
                    print("Suppression de l'attribut id {0}".format(attr_id))
                    Field.query.filter_by(
                        id=attr_id
                    ).delete()

        print("Commit !")
        db.session.commit()

        raw_form = generate_edit_page_admin_form(page)
        form = raw_form['form']
        attr_label_list = raw_form['attr_label_list']
        print(attr_label_list)
        print("test {0}".format(Field.query.filter_by(page_id = page.id).all()))

    return render_template('edit_page.html',
                           page=page,
                           attr_label_list = attr_label_list,
                           form=form)

@app.route('/lac_admin/', methods=('GET', 'POST'))
@login_required
def edit_lac_admin():
    form = SelectMemberzForm(request.form)
    memberz = get_lac_admin_memberz()
    all_userz = get_all_users()


@app.route('/add_page/', methods=('GET', 'POST'))
@login_required
def add_page():
    form = AddPageViewForm(request.form)
    if request.method == 'POST' :
        if form.label.data is not None and form.description.data is not None:
            page = Page(label = form.label.data,
                        description = form.description.data)
            db.session.add(page)
            db.session.commit()
            flash(u'Vue correctement ajoutée')
            return render_template('home.html')

    return render_template('add_page.html',
                           form=form)

@app.route('/reset_schema/')
@login_required
def reset_schema():
    """
    Delete all values in DB for tables LDAPObjectClass & LDAPAttribute
    Columnpy back LDAP schema in DB
    """
    subschema = get_subschema()
    all_oc_oid = subschema.listall(schema.ObjectClass)
    # Suppression du contenu des tables LDAP
    LDAPObjectClass.query.delete()
    LDAPAttribute.query.delete()
    LDAPObjectClassAttribute.query.delete()
    # On parse chaque ObjectClass
    for oid in all_oc_oid:
        oc_name = subschema.get_obj(schema.ObjectClass, oid).names[0]
        # On ne récupère pas les classes dans la liste
        if oc_name not in ('subschema', 'subentry', 'objectClass'):
            oc_attrs = subschema.attribute_types( [oc_name] )
            db_oc =  LDAPObjectClass(oc_name)
            db.session.add(db_oc)
            must_attrs = oc_attrs[0]
            may_attrs = oc_attrs[1]
            # Traitement des attributs obligatoires
            for (oid, attr_obj) in must_attrs.iteritems():
                if attr_obj.names[0] != 'objectClass':
                    db_attr = create_ldapattr_if_not_exists(attr_obj.names[0])
                    db_attr_oc = LDAPObjectClassAttribute(
                        mandatory = True,
                        ldapobjectclass = db_oc,
                        ldapattribute = db_attr)
                    db.session.add(db_attr, db_attr_oc)
            # Traitement des attributs facultatifs
            for (oid, attr_obj) in may_attrs.iteritems():
                db_attr = create_ldapattr_if_not_exists(attr_obj.names[0])
                db_attr_oc = LDAPObjectClassAttribute(
                    mandatory = False,
                    ldapobjectclass = db_oc,
                    ldapattribute = db_attr)
                db.session.add(db_attr, db_attr_oc)
    db.session.commit()
    return render_template('test.html')

@app.route('/update_schema/')
@login_required
def update_schema():
    """
    Check DB schema consistency over LDAP
    Update if necessary
    """
    subschema = get_subschema()
    all_oc_oid = subschema.listall(schema.ObjectClass)
    db_oc_list_labelz =  [oc.label for oc in LDAPObjectClass.query.all()]

    infoz = []

    # On parse chaque ObjectClass récupéré de LDAP
    for oid in all_oc_oid:
        ldap_oc_name = subschema.get_obj(schema.ObjectClass, oid).names[0]

        # On ne récupère pas les classes dans la liste
        if ldap_oc_name not in ('subschema', 'subentry', 'objectClass'):

            ldap_oc_attrs = subschema.attribute_types( [ldap_oc_name] )
            ldap_must_attrs = ldap_oc_attrs[0]
            ldap_may_attrs = ldap_oc_attrs[1]
            ldap_all_attrs = []

            # Création de l'ObjectClass s'il n'est pas déjà présent
            if ldap_oc_name in db_oc_list_labelz:
                db_oc = LDAPObjectClass.query.filter_by(
                    label=ldap_oc_name
                ).first()
            else:
                db_oc =  LDAPObjectClass(ldap_oc_name)
                db.session.add(db_oc)
                infoz.append(
                    u'Création de l\'ObjectClass {0}'.format(ldap_oc_name)
                )

            db_oc_attr_label_list =  [
                oc_attr.ldapattribute.label
                for oc_attr in  LDAPObjectClassAttribute.query.filter_by(
                        ldapobjectclass_id = db_oc.id
                ).all()
            ]
            # Vérifie que les MUST attributes de ldap sont présent en base
            for (oid, attr_obj) in ldap_must_attrs.iteritems():
                if attr_obj.names[0] != 'objectClass':
                    ldap_all_attrs.append(attr_obj.names[0])
                    if attr_obj.names[0] not in db_oc_attr_label_list:
                        db_attr = create_ldapattr_if_not_exists(
                            attr_obj.names[0]
                        )
                        db_attr_oc = LDAPObjectClassAttribute(
                            mandatory = True,
                            ldapobjectclass = db_oc,
                            ldapattribute = db_attr)
                        db.session.add(db_attr, db_attr_oc)
                        infoz.append(
                            u'Création de l\'Attribut {0}'.format(
                                attr_obj.names[0]
                            )
                        )
            # Vérifie que les MAY attributes de ldap sont présent en base
            for (oid, attr_obj) in ldap_may_attrs.iteritems():
                ldap_all_attrs.append(attr_obj.names[0])
                if attr_obj.names[0] not in db_oc_attr_label_list:
                    db_attr = create_ldapattr_if_not_exists(
                        attr_obj.names[0]
                    )
                    db_attr_oc = LDAPObjectClassAttribute(
                        mandatory = True,
                        ldapobjectclass = db_oc,
                        ldapattribute = db_attr)
                    db.session.add(db_attr, db_attr_oc)
                    infoz.append(
                        u'Création de l\'Attribut {0}'.format(
                            attr_obj.names[0]
                        )
                    )
            # On vérifie qu'il n'y a pas d'attributs en base absents dans LDAP
            for db_oc_attr_label in db_oc_attr_label_list:
                if db_oc_attr_label not in ldap_all_attrs:
                    db_attr = LDAPAttribute.query.filter_by(
                        label = db_oc_attr_label
                    ).first()
                    LDAPObjectClassAttribute.query.filter_by(
                        ldapobjectclass_id = db_oc.id,
                        ldapattribute_id = db_attr.id
                    ).delete()
                    infoz.append(
                        u'Suppression de l\'Attribut {0}'.format(
                            db_oc_attr_label
                        )
                    )
    db.session.commit()

    if not infoz:
        infoz.append(u'Aucune donnée mise à jour')

    flash(u'\n'.join(infoz))
    return render_template('test.html')





@app.route('/hello/')
@app.route('/hello/<name>')
@login_required
def hello(name=None):
    return render_template('test.html', name=session['uid'])


@app.route('/edit/<page>/<uid>', methods=('GET', 'POST'))
@login_required
def edit(page,uid):
    page = Page.query.filter_by(label=page).first()
    raw_form = generate_edit_form(page,uid)
    form = raw_form['form']
    attributes = raw_form['attributes']
    uid_attributez = ldaphelper.get_search_results(
        get_uid_detailz(uid)
    )[0].get_attributes()
    page_attrz = dict(
        (row.label.lower(), row)
        for row in Field.query.filter_by(page_id = page.id).all()
    )
    for attr in attributes:
        #print([entry.data for entry in getattr(form, attr).entries  ])
        pass
    if request.method == 'POST' and form.validate() :
        update_ldap_object_from_edit_form(form, attributes, uid)
    else:
        for attr in attributes:
            form_attr = getattr(form, attr)
            while(len(form_attr.entries)>0):
                form_attr.pop_entry()

        for attr_name, attr_values in uid_attributez.iteritems():
            if attr_name in page_attrz and page_attrz[attr_name].edit:
                attr_field = getattr(form, attr_name)
                for attr_value in uid_attributez[attr_name]:
                    attr_field.append_entry(attr_value)

    return render_template('edit.html',
                           form=form,
                           page=page,
                           page_attrz=page_attrz,
                           uid=uid,
                           attributes = attributes)

### Helperz

def populate_grouplist_redis():
    grouplist = get_groupz_list()
    for (uid, group) in grouplist:
        r.hset('grouplist', uid, group)
    print(r.hgetall('grouplist'))

def populate_people_group_redis():
    for group in app.config['PEOPLE_GROUPS']:
        r.delete('groupz:{0}'.format(group))
        memberz = get_group_person_memberz(group)
        for member in memberz:
            r.sadd("groupz:{0}".format(group), member)

def create_ldapattr_if_not_exists(label):
    db_attr = LDAPAttribute.query.filter_by(
        label = label
    ).first()
    if db_attr is None:
        db_attr = LDAPAttribute(label=label)
    return db_attr

def update_ldap_object_from_edit_form(form, attributes, uid):
    uid_attributez = ldaphelper.get_search_results(
        get_uid_detailz(uid)
    )[0].get_attributes()
    pre_modlist = []
    for attr in attributes:
        form_field_values = [entry.data.encode('utf-8')
                             for entry in getattr(form, attr).entries]
        print('form_field_values : {0}'.format(form_field_values))
        if uid_attributez[attr] != form_field_values:
            pre_modlist.append((attr, form_field_values))
    print(pre_modlist)
    ldap.update_uid_attribute(uid, pre_modlist)


def generate_edit_form(page, uid):
    page_attrz = dict(
        (row.label.lower(), row)
        for row in Field.query.filter_by(page_id = page.id).all()
    )
    uid_attributez = ldaphelper.get_search_results(
        get_uid_detailz(uid)
    )[0].get_attributes()
    date_formatz = ['Datetime', 'DaysNumber', 'GeneralizedTime']
    groupz_list = get_groupz_list()

    attributes = []
    class EditForm(Form):
        @classmethod
        def append_field(cls, name, field):
            setattr(cls, name, field)
            return cls

    for attr_name, attr_values in uid_attributez.iteritems():
        if attr_name in page_attrz and page_attrz[attr_name].edit:
            attributes.append(attr_name)
            if page_attrz[attr_name].fieldtype.type == 'Text':
                setattr(EditForm,
                        attr_name,
                        FieldList(TextField(page_attrz[attr_name].description)))
            elif page_attrz[attr_name].fieldtype.type in date_formatz:
                setattr(EditForm,
                        attr_name,
                        FieldList(DateField(page_attrz[attr_name].description)))
            elif  page_attrz[attr_name].fieldtype.type == 'GIDNumber':
                setattr(EditForm,
                        attr_name,
                        FieldList(SelectField(page_attrz[attr_name].description,
                                              choices=groupz_list)))

    form = EditForm(request.form)
    return {'form' : form,
            'attributes': attributes}


def generate_edit_page_admin_form(page):

    # selection des attributs hérités des object classes
    select_oc_choices = get_selected_oc_choices(page)

    page_oc_id_list = [oc[0] for oc in select_oc_choices]

    page_oc_attr_list = get_attr_from_oc_id_list(page_oc_id_list)

    page_oc_attr_id_list = [ a.id for a in page_oc_attr_list ]

    print("page_oc_attr_id_list : {0}".format(page_oc_attr_id_list))

    # Sélection des attributs indépendants des object classes
    page_unic_attr_list = Field.query.filter(
        Field.page_id==page.id,
        ~Field.ldapattribute_id.in_(page_oc_attr_id_list)
    ).all()
    print("page_unic_attr_list : {0}".format(page_unic_attr_list))

    print("fuuu {0}".format([a.ldapattribute_id for a in page_unic_attr_list]))
    page_unic_attr_id_list = [attr.id for attr in page_unic_attr_list]
    print("page_unic_attr_id_list {0}".format(page_unic_attr_id_list))

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
                                       choices=get_display_mode_choices())
            desc = TextField(u'Description du champ',
                                    default=existing_field.description
                                   if existing_field is not None else None)
        setattr(EditPageForm, label, FormField(EditFieldForm))

    form = EditPageForm(request.form)
    form.oc_form.available_oc.choices = get_available_oc_choices(
        page_oc_id_list
    )
    form.oc_form.selected_oc.choices = select_oc_choices
    form.attr_form.available_attr.choices = get_available_unic_attr_choices(
        page_unic_attr_id_list
    )
    form.attr_form.selected_attr.choices = select_unic_attr_choices

    return {'form' : form,
            'attr_label_list': attr_label_list,
            'page_oc_id_list': page_oc_id_list,
            'page_unic_attr_id_list': page_unic_attr_id_list}


def update_fields_from_edit_page_admin_form(form, attributes, page):
    Field.query.filter(Field.page_id == page.id,
                       ~Field.label.in_(attributes)
    ).delete(synchronize_session='fetch')

    for attribute in attributes:
        attribute_field = getattr(form, attribute)
        upsert_field(attribute, attribute_field, page)


def create_default_field(attribute, page):
    print("Create default {0} for {1}".format(attribute, page.label))
    page_attr = Field(label = attribute.label,
                      page = page,
                      ldapattribute = attribute)
    db.session.add(page_attr)
    db.session.commit()

def upsert_field(attr_label, form_field, page):
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
        existing_field.description = form_field.desc.data
        existing_field.multivalue = form_field.multivalue.data
    else:
        new_field = Field(label=attribute.label,
                          page=page,
                          ldapattribute=attribute,
                          display=form_field.display.data,
                          edit=form_field.edit.data,
                          restrict=form_field.restrict.data,
                          fieldtype=field_type,
                          description=form_field.desc.data,
                          multivalue=form_field.multivalue.data)
        db.session.add(new_field)

def get_display_mode_choices():
    field_types = FieldType.query.all()
    display_mode_choices = [(field_type.id, field_type.type)
                            for field_type in field_types]
    return display_mode_choices

def get_available_unic_attr_choices(page_unic_attr_id_list):
    available_unic_attr = LDAPAttribute.query.all()
    available_unic_attr_choices = filter(
        None, [(attr.id,attr.label)
               if attr.id not in page_unic_attr_id_list
               and attr is not None
               else None for attr in available_unic_attr]
    )
    return available_unic_attr_choices

def get_available_oc_choices(selected_oc_id_list):
    available_oc = LDAPObjectClass.query.all()
    available_oc_choices = filter(None, [(oc.id,oc.label)
                                      if oc.id not in selected_oc_id_list
                                      and oc is not None
                                      else None for oc in available_oc])
    return available_oc_choices

def get_selected_oc_choices(page):
    page_oc_list = PageObjectClass.query.filter_by(page_id=page.id).all()
    select_oc_choices = filter(None,[(oc.ldapobjectclass.id,
                                      oc.ldapobjectclass.label)
                                     for oc in page_oc_list ])
    return select_oc_choices

def get_attr_from_oc_id_list(oc_id_list):
    oc_attr_list = LDAPObjectClassAttribute.query.filter(
        LDAPObjectClassAttribute.ldapobjectclass_id.in_(oc_id_list)
    ).all()
    oc_attr_id_list = [oc_attr.ldapattribute_id for oc_attr in oc_attr_list]
    attr_list = LDAPAttribute.query.filter(
        LDAPAttribute.id.in_(oc_attr_id_list)
    ).all()
    return attr_list

def get_group_from_member_uid(uid):
    for group in app.config['PEOPLE_GROUPS']:
        if uid in r.smembers("groupz:{0}".format(group)):
            return group
    flash(u"Impossible de trouver le groupe associé à {0}".format(uid))
app.jinja_env.globals.update(
    get_group_from_member_uid=get_group_from_member_uid
)

def get_attr(form, name):
    return getattr(form, name)
app.jinja_env.globals.update(get_attr=get_attr)

def get_type(obj):
    return str(type(obj))
app.jinja_env.globals.update(get_type=get_type)

def get_group_person_memberz(group):
    """
    List memberz of a group inherited from people ou
    """
    ldap_filter='(objectclass=inetOrgPerson)'
    attributes=['uid']
    base_dn='ou={0},ou=people,{1}'.format(group,app.config['LDAP_SEARCH_BASE'])

    records = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    memberz = [ member.get_attributes()['uid'][0] for member in records]
    return memberz

def get_groupz_list():
    ldap_filter = "(objectClass=posixGroup)"
    ldap_groupz = ldaphelper.get_search_results(
        ldap.search(ldap_filter=ldap_filter,
                         attributes=['cn', 'gidNumber'])
    )
    ldap_groupz_list = []
    for group in ldap_groupz:
        group_attrz = group.get_attributes()
        ldap_groupz_list.append((group_attrz['gidNumber'][0],
                                 group_attrz['cn'][0]))

    return ldap_groupz_list

def get_uid_detailz(uid):
    ldap_filter='(uid={0})'.format(uid)
    attributes=['*','+']
    detailz = ldap.search(ldap_filter=ldap_filter,attributes=attributes)
    return detailz

def get_subschema():
    ldap_filter='(objectclass=*)'
    base_dn='cn=subschema'
    attributes=['*','+']
    scope=SCOPE_BASE
    raw_schema = ldap.search(ldap_filter=ldap_filter,
                          base_dn=base_dn,
                          attributes=attributes,
                          scope=scope)
    subschema_entry = ldaphelper.get_search_results(raw_schema)[0]
    subschema_subentry = subschema_entry.get_attributes()
    subschema = schema.subentry.SubSchema( subschema_subentry )
    return subschema

def process_ldap_result(resultz):
    for result in resultz:
        print("Pretty print : {0}".format(result.pretty_print()))
        for attribute in result.get_attributes():
            if attribute == 'gidNumber':
                result[line][1][attribute][0]=get_posix_group_cn_by_gid(
                    result[line][1][attribute][0]
                )
            if attribute == 'createTimestamp' or attribute == 'authTimestamp':
                result[line][1][attribute][0]= generalized_time_to_datetime(
                    result[line][1][attribute][0]
                )

            if attribute == 'cinesdaterenew':
                result[line][1][attribute][0] = datetime.fromtimestamp(
                    # 86400 == nombre de secondes par jour
                    int(result[line][1][attribute][0]) * 86400
                )
    return result

def generalized_time_to_datetime(generalized_time):
    created_datetime = datetime.strptime(
        generalized_time, "%Y%m%d%H%M%SZ"
    )
    created_datetime = utc.localize(created_datetime)
    created_datetime = created_datetime.astimezone(
        timezone(app.config['TIMEZONE'])
    )
    return created_datetime

app.jinja_env.globals.update(
    generalized_time_to_datetime=generalized_time_to_datetime
)
def days_number_to_datetime(nb):
    return datetime.fromtimestamp(
        # 86400 == nombre de secondes par jour
        int(nb) * 86400
    )
app.jinja_env.globals.update(
    days_number_to_datetime=days_number_to_datetime
)

def get_posix_group_cn_by_gid(gid):
    return r.hget('grouplist', gid)

app.jinja_env.globals.update(
    get_posix_group_cn_by_gid=get_posix_group_cn_by_gid
)
### Run !

if __name__ == '__main__':
    app.config.from_object('config')
    app.debug = app.config['DEBUG']
    decoder = PythonLDAPDecoder(app.config['ENCODING'])
    app.run()
