# -*- coding: utf-8 -*-
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response
from flask.ext.ldap import LDAP, login_required, admin_login_required
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug import secure_filename
#from flask_bootstrap import Bootstrap
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from wtforms import Form, BooleanField, TextField, SelectMultipleField, SelectField, PasswordField,validators, FormField, FieldList, DateField
from datetime import datetime, timedelta
import time
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz
import ldaphelper
#import upsert
from ldap_decoder import PythonLDAPDecoder
from ldap import SCOPE_BASE,schema
import hashlib,binascii
import redis
import re
import os

# Custom modulez
from formz import *

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


ALLOWED_EXTENSIONS = set(['txt', 'csv'])


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

    ldapobjecttypeobjectclasses = db.relationship("LDAPObjectTypeObjectClass",
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

# Many to one : LDAPObjectTypeObjectClass (n)---(1) LDAPObjectType
# Many to one : LDAPObjectTypeObjectClass (n)---(1) LDAPObjectClass
class LDAPObjectTypeObjectClass(db.Model):
    __tablename__ = 'ldapobjecttypeobjectclass'
    id = db.Column(db.Integer, primary_key=True)
    ldapobjecttype_id = Column(Integer, ForeignKey('ldapobjecttype.id',
                                         onupdate="CASCADE",
                                         ondelete="CASCADE"))
    ldapobjectclass_id = Column(Integer, ForeignKey('ldapobjectclass.id',
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"))

    def __init__(self, ldapobjecttype_id, ldapobjectclass_id):
        self.ldapobjecttype_id = ldapobjecttype_id
        self.ldapobjectclass_id = ldapobjectclass_id


class LDAPObjectType(db.Model):
    __tablename__ = 'ldapobjecttype'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(50))
    ranges = db.Column(db.String(200))
    apply_to = db.Column(db.String(20))
    last_used_id = db.Column(db.Integer)

    ldapobjecttypeobjectclasses = db.relationship("LDAPObjectTypeObjectClass",
                                     backref="ldapobjecttype",
                                     lazy='dynamic')




### Routez

@app.route('/')
@login_required
def home():
    # populate_people_group_redis()
    # populate_grouplist_redis()
    # populate_work_group_redis()
    return render_template('home.html')


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


@app.route('/change_password/<uid>', methods=['POST', 'GET'])
@login_required
def change_password(uid):
    """
    Change the password for a given UID
    """
    form=ChangePassForm(request.form)
    if request.method == 'POST' and form.validate():
        pre_modlist = []
        if get_group_from_member_uid(uid) == 'cines':
            nt_hash = hashlib.new(
                'md4',
                form.new_pass.data.encode('utf-16le')
            ).hexdigest().upper()
            pre_modlist = [('sambaPwdLastSet', str(int(time.time()))),
                           ('sambaNTPassword', nt_hash)]
        if uid != session['uid']:
            pre_modlist.append(('userPassword',
                                form.new_pass.data.encode('utf-8')))
            pre_modlist.append(('pwdReset', 'TRUE'))
            flash(u'Mot de passe pour {0} mis à jour avec succès.'.format(uid))
        else:
            ldap.change_passwd(uid, session['password'], form.new_pass.data)
            flash(
                u'Votre mot de passe a été mis à jour avec succès.'.format(uid)
            )
        ldap.update_uid_attribute(uid, pre_modlist)

        return redirect(url_for('home'))
    return render_template('change_password.html', form=form, uid=uid)


@app.route('/people/<group>')
@login_required
def show_group_memberz(group):
    memberz = get_people_group_memberz(group)
    return render_template('show_group_memberz.html',
                           memberz=memberz,
                           group=group)



@app.route('/details/<uid>')
@login_required
def get_account_detailz(uid):
    detailz = get_uid_detailz(uid)
    print(detailz)
    return render_template('show_detailz.html', account=detailz)

@app.route('/infoz')
@login_required
def infoz():
    return render_template('infoz.html', session = session)


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
    uid_attributez=uid_detailz.get_attributes()
    return render_template('show_page.html',
                           uid = uid,
                           uid_attributez=uid_attributez,
                           page_fieldz=page_fieldz,
                           is_active=is_active(uid_detailz))

@app.route('/edit_page/<page_label>', methods=('GET', 'POST'))
@app.route('/edit_page/')
@admin_login_required
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

        db.session.commit()

        raw_form = generate_edit_page_admin_form(page)
        form = raw_form['form']
        attr_label_list = raw_form['attr_label_list']

    return render_template('edit_page.html',
                           page=page,
                           attr_label_list = attr_label_list,
                           form=form)


@app.route('/lac_adminz/', methods=('GET', 'POST'))
@admin_login_required
def edit_lac_admin():
    form = SelectMemberzForm(request.form)

    populate_lac_admin_choices(form)

    memberz = [ get_uid_from_dn(dn) for dn in ldap.get_lac_admin_memberz() ]

    if request.method == 'POST':
        if form.selected_memberz.data is not None:
            memberz_to_add = []
            for member in form.selected_memberz.data:
                if member not in memberz:
                    print('ajout de {0}'.format(member))
                    memberz_to_add.append(ldap.get_full_dn_from_uid(member))
            if memberz_to_add:
                ldap.add_cn_attribute('lacadmin',
                                      [('member', member.encode('utf8'))
                                        for member in memberz_to_add]
                                   )
        if memberz is not None:
            memberz_to_del = []
            for member in memberz:
                if member not in form.selected_memberz.data:
                    print('suppression de {0}'.format(member))
                    memberz_to_del.append(ldap.get_full_dn_from_uid(member))
            if memberz_to_del:
                ldap.remove_cn_attribute('lacadmin',
                                          [('member', member.encode('utf8'))
                                           for member in memberz_to_del]
                                   )
        populate_lac_admin_choices(form)
    return render_template('lac_adminz.html',
                           form=form)

@app.route('/ldap_adminz/', methods=('GET', 'POST'))
@admin_login_required
def edit_ldap_admin():
    form = SelectMemberzForm(request.form)

    populate_ldap_admin_choices(form)

    memberz = [ get_uid_from_dn(dn) for dn in ldap.get_ldap_admin_memberz() ]

    if request.method == 'POST':
        if form.selected_memberz.data is not None:
            memberz_to_add = []
            for member in form.selected_memberz.data:
                if member not in memberz:
                    print('ajout de {0}'.format(member))
                    memberz_to_add.append(ldap.get_full_dn_from_uid(member))
            if memberz_to_add:
                ldap.add_cn_attribute('ldapadmin',
                                      [('member', member.encode('utf8'))
                                        for member in memberz_to_add]
                                   )
        if memberz is not None:
            memberz_to_del = []
            for member in memberz:
                if member not in form.selected_memberz.data:
                    print('suppression de {0}'.format(member))
                    memberz_to_del.append(ldap.get_full_dn_from_uid(member))
            if memberz_to_del:
                ldap.remove_cn_attribute('ldapadmin',
                                          [('member', member.encode('utf8'))
                                           for member in memberz_to_del]
                                   )
        populate_ldap_admin_choices(form)
    return render_template('ldap_adminz.html',
                           form=form)

@app.route('/add_page/', methods=('GET', 'POST'))
@admin_login_required
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
@admin_login_required
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
@admin_login_required
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
    if request.method == 'POST' and form.validate() :
        update_ldap_object_from_edit_form(form, attributes, uid)
    else:
        print(attributes)
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


@app.route('/select_edit_group_attributes/', methods=('GET', 'POST'))
@login_required
def select_edit_group_attributes():
    view_form = EditGroupViewForm(request.form)
    view_form.attr_form.available_attr.choices = [
        (attr.id, attr.label)
        for attr in LDAPAttribute.query.all()
    ]
    view_form.attr_form.selected_attr.choices = []





@app.route('/edit_group/', methods=('GET', 'POST'))
@login_required
def edit_group():
    page = Page.query.filter_by(label='edit_group').first()
    view_form = EditGroupViewForm(request.form)
    view_form.attr_form.available_attr.choices = [
        (attr.id, attr.label)
        for attr in Field.query.filter_by(page_id = page.id).all()
    ]
    view_form.attr_form.selected_attr.choices = []
    if 'edit_group_fieldz_id' in session:
        attrz_list = session['edit_group_fieldz_id']
    else:
        attrz_list = []

    if 'edit_group_memberz_uid' in session:
        groupz_memberz = session['edit_group_memberz_uid']
    else:
        groupz_memberz = []
    # print('attrz_list : {0}'.format(attrz_list))
    edit_form = generate_edit_group_form(page, attrz_list)['form']
    group_form = SelectGroupzForm(request.form)
    group_form.available_groupz.choices = get_groupz_list()
    group_form.selected_groupz.choices = []


    if request.method == 'POST':

        if view_form.attr_form.selected_attr.data:
            group_form = SelectGroupzForm(request.form)
            group_form.available_groupz.choices = get_groupz_list()
            group_form.selected_groupz.choices = []

            session[
                'edit_group_fieldz_id'
            ] = view_form.attr_form.selected_attr.data
            return render_template('edit_group.html',
                                   group_form=group_form)

        elif group_form.selected_groupz.data:
            groupz_id = group_form.selected_groupz.data
            groupz_label = [ get_posix_group_cn_by_gid(id)
                             for id in groupz_id ]
            groupz_memberz = get_posix_groupz_memberz(groupz_label)

            session[
                'edit_group_memberz_uid'
            ] = groupz_memberz

            fieldz = Field.query.filter(
                Field.id.in_(session['edit_group_fieldz_id'])
            ).all()
            print('fieldz {0}'.format(fieldz))

            raw_edit_form = generate_edit_group_form(
                page,
                session['edit_group_fieldz_id']
            )
            edit_form = raw_edit_form['form']


            return render_template('edit_group.html',
                                   edit_form=edit_form,
                                   fieldz=fieldz,
                                   attributez=[field.label.encode('utf-8')
                                                      for field in fieldz])

        elif edit_form.group_form.selected_groupz.data :
            fieldz = Field.query.filter(
                Field.id.in_(session['edit_group_fieldz_id'])
            ).all()
            pre_modlist = []
            for field in fieldz:
                pre_modlist.append(
                    (field.label,
                     getattr(edit_form, field.label).data.encode('utf-8'))
                )
            if edit_form.action.data == '0':
                for uid in groupz_memberz:
                    ldap.add_uid_attribute(uid, pre_modlist)
            elif edit_form.action.data == '1':
                for uid in groupz_memberz:
                    ldap.update_uid_attribute(uid, pre_modlist)
            flash(u'Les groupes {0} ont été mis à jour'.format(groupz_label))
            # if edit_form.backup.data:
            #     return get_backup_file(
            #         groupz_memberz,
            #         [field.label.encode('utf-8') for field in fieldz])
            return redirect(url_for('home'))
    return render_template('edit_group.html',
                           view_form=view_form)


@app.route('/edit_submission/<uid>', methods=('GET', 'POST'))
@login_required
def edit_submission(uid):
    form = EditSubmissionForm(request.form)
    form.wrk_group.choices = [
        (group, group)
        for group in get_submission_groupz_list()
    ]
    if request.method == 'POST':
        wrk_group = form.wrk_group.data
        is_submission = form.submission.data
        is_member = form.member.data
        if is_submission and is_member:
            add_to_group_if_not_member(wrk_group, [uid])
            set_submission(uid, wrk_group, '1')
        elif is_member and not is_submission:
            add_to_group_if_not_member(wrk_group, [uid])
            set_submission(uid, wrk_group, '0')
        elif not is_member:
            rem_from_group_if_member(wrk_group, [uid])
            set_submission(uid, wrk_group, '0')
        return redirect(url_for('show',
                                page = get_group_from_member_uid(uid),
                                uid = uid))

    return render_template('edit_submission.html',
                           form=form,
                           uid=uid)

@app.route('/edit_group_submission/', methods=('GET', 'POST'))
@login_required
def edit_group_submission():
    form = EditGroupSubmissionForm(request.form)
    form.submission_form.wrk_group.choices = [
        (group, group)
        for group in get_submission_groupz_list()
    ]
    form.group_form.available_groupz.choices = get_groupz_list()
    form.group_form.selected_groupz.choices = []

    if request.method == 'POST':
        groupz_id = form.group_form.selected_groupz.data
        groupz_label = [ get_posix_group_cn_by_gid(id)
                         for id in groupz_id ]
        groupz_memberz_uid = get_posix_groupz_memberz(groupz_label)


        wrk_group = form.submission_form.wrk_group.data
        is_submission = form.submission_form.submission.data
        is_member = form.submission_form.member.data

        if is_submission and is_member:
            add_to_group_if_not_member(wrk_group, groupz_memberz_uid)
            for uid in groupz_memberz_uid:
                set_submission(uid, wrk_group, '1')
        elif is_member and not is_submission:
            add_to_group_if_not_member(wrk_group, groupz_memberz_uid)
            for uid in groupz_memberz_uid:
                set_submission(uid, wrk_group, '0')
        elif not is_member:
            rem_from_group_if_member(wrk_group, groupz_memberz_uid)
            for uid in groupz_memberz_uid:
                set_submission(uid, wrk_group, '0')
        return redirect(url_for('home'))
    return render_template('edit_group_submission.html',
                           form=form)

@app.route('/toggle_account/<uid>')
@login_required
def toggle_account(uid):
    user = ldaphelper.get_search_results(get_uid_detailz(uid))[0]
    if is_active(user):
        disable_account(user)
    else:
        enable_account(user)
    return redirect(url_for('show',
                            page = get_group_from_member_uid(uid),
                            uid = uid))


@app.route('/edit_default_quota/')
@app.route('/edit_default_quota/<storage_cn>', methods=('GET', 'POST'))
@admin_login_required
def edit_default_quota(storage_cn=None):
    storagez = get_default_storage_list()
    storagez_labelz = [storage.get_attributes()['cn'][0]
                       for storage in storagez]

    if storage_cn is not None:
        storage = get_default_storage(storage_cn).get_attributes()
        form = EditDefaultQuotaForm(request.form)

        if request.method == 'POST' and form.validate():
            update_default_quota(storage_cn, form)
            return redirect(url_for('home'))
        set_default_quota_form_values(form, storage)
        return render_template('edit_default_quota.html',
                               form=form,
                               storage_cn=storage_cn)

    else:
        return render_template('edit_default_quota.html',
                               storagez=storagez_labelz)

@app.route('/edit_quota/')
@app.route('/edit_quota/<storage_cn>', methods=('GET', 'POST'))
@admin_login_required
def edit_quota(storage_cn=None):
    storagez = get_group_quota_list()
    storagez_labelz = [storage.get_attributes()['cn'][0]
                       for storage in storagez]

    if storage_cn is not None:
        storage = get_storage(storage_cn).get_attributes()
        form = EditQuotaForm(request.form)

        if request.method == 'POST' and form.validate():
            update_quota(storage_cn, form)
            return redirect(url_for('home'))
        set_quota_form_values(form, storage)
        return render_template('edit_quota.html',
                               form=form,
                               storage_cn=storage_cn)

    else:
        return render_template('edit_quota.html',
                               storagez=storagez_labelz)

@app.route('/add_quota/', methods=('GET', 'POST'))
@admin_login_required
def add_quota():
    form = CreateQuotaForm(request.form)

    default_storagez = get_default_storage_list()
    form.default_quota.choices = [
        (storage.get_attributes()['cn'][0],
         storage.get_attributes()['cn'][0])
        for storage in default_storagez ]
    form.group.choices = get_groupz_list()

    if request.method == 'POST' and form.validate():
        niou_cn = '{0}.{1}'.format(
                    form.default_quota.data,
                    form.group.data)

        default_storage = get_default_storage(
            form.default_quota.data).get_attributes()

        default_size_unit = get_attr(
            get_attr(SizeQuotaForm, 'unit'),'kwargs')['default']
        default_inode_unit = get_attr(
            get_attr(InodeQuotaForm, 'unit'),'kwargs')['default']

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
        group_full_dn = ldap.get_full_dn_from_cn(
            get_posix_group_cn_by_gid(form.group.data))
        full_dn = 'cn={0},{1}'.format(niou_cn,group_full_dn)
        ldap.add(full_dn, add_record)
        flash(u'Quota initialisé')
        return redirect(url_for('edit_quota',
                                storage_cn = niou_cn))

    return render_template('add_quota.html', form=form)

@app.route('/get_backup_file/<userz>/<attributez>')
@login_required
def get_backup_file(userz, attributez):
    userz = [user.encode('utf-8')
             for user in userz.split(',')]
    attributez = [attribute.encode('utf-8')
                  for attribute in attributez.split(',')]
    file_name = "backup_{0}.txt".format(
        datetime.now().strftime("%d%b%HH%M_%Ss"))
    file_content = " ".join(attributez)
    for user in userz:
        user_attr = ldaphelper.get_search_results(
            ldap.search(
                ldap_filter="(uid={0})".format(user),
                attributes=attributez
            )
        )[0].get_attributes()
        line = ",".join(["{0}={1}".format(key, value)
                for key, value in user_attr.iteritems()])
        line = ",".join(["uid={0}".format(user),line])
        file_content = "\n".join([file_content, line])
    response = make_response(file_content)
    response.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        file_name)
    return response

@app.route('/edit_file/', methods=('GET', 'POST'))
@login_required
def edit_file():

    page = Page.query.filter_by(label='edit_file').first()
    view_form = EditGroupViewForm(request.form)
    view_form.attr_form.available_attr.choices = [
        (attr.id, attr.label)
        for attr in Field.query.filter_by(page_id = page.id).all()
    ]
    view_form.attr_form.selected_attr.choices = []
    if 'edit_file_fieldz_id' in session:
        attrz_list = session['edit_file_fieldz_id']
    else:
        attrz_list = []

    if 'edit_file_memberz_uid' in session:
        userz = session['edit_file_memberz_uid']
    else:
        userz = []

    edit_form = generate_edit_group_form(page, attrz_list)['form']
    file_form = UserzFileForm(request.form)

    if request.method == 'POST':

        if view_form.attr_form.selected_attr.data:
            group_form = SelectGroupzForm(request.form)
            group_form.available_groupz.choices = get_groupz_list()
            group_form.selected_groupz.choices = []

            session[
                'edit_file_fieldz_id'
            ] = view_form.attr_form.selected_attr.data
            return render_template('edit_file.html',
                                   file_form=file_form)

        elif file_form.userz_file and edit_form.submited.data == 'False' :
            userz_file = request.files[file_form.userz_file.name]
            if userz_file and allowed_file(userz_file.filename):
                # filename = secure_filename(file.filename)
                userz = userz_file.read().split('\n')
            else:
                flash('Format du fichier incorrect')
                return render_template('edit_file.html',
                                       file_form=file_form)

            session[
                'edit_file_memberz_uid'
            ] = userz

            fieldz = Field.query.filter(
                Field.id.in_(session['edit_file_fieldz_id'])
            ).all()

            raw_edit_form = generate_edit_group_form(
                page,
                attrz_list
            )
            edit_form = raw_edit_form['form']
            edit_form.submited.data = 'True'
            return render_template('edit_file.html',
                                   edit_form=edit_form,
                                   fieldz=fieldz,
                                   attributez=[field.label.encode('utf-8')
                                                      for field in fieldz])

        elif edit_form.submited.data == 'True' :

            fieldz = Field.query.filter(
                Field.id.in_(attrz_list)
            ).all()
            pre_modlist = []
            for field in fieldz:
                pre_modlist.append(
                    (field.label,
                     getattr(edit_form, field.label).data.encode('utf-8'))
                )
            if edit_form.action.data == '0':
                for uid in userz:
                    ldap.add_uid_attribute(uid, pre_modlist)
            elif edit_form.action.data == '1':
                for uid in userz:
                    ldap.update_uid_attribute(uid, pre_modlist)
            flash(u'Les utilisateurs ont été mis à jour')
            return redirect(url_for('home'))


    return render_template('edit_file.html',
                           view_form=view_form)


@app.route('/edit_ldap_object_type/<ldap_object_type_label>',
           methods=('GET', 'POST'))
@login_required
def edit_ldap_object_type(ldap_object_type_label):
    if ldap_object_type_label is not None:
        ldap_object_type = LDAPObjectType.query.filter_by(
            label = ldap_object_type_label).first()
        selected_oc_choices = get_ot_oc_choices(ldap_object_type)
        ot_oc_id_list = [oc[0] for oc in selected_oc_choices]
        available_oc_choices = filter(
            None,
            [(oc.id,oc.label)
             if oc.id not in ot_oc_id_list
             and oc is not None
             else None for oc in LDAPObjectClass.query.all()]
        )

        form = LDAPObjectTypeForm(request.form)
        if request.method == 'POST':
            ldap_object_type.label = form.label.data
            ldap_object_type.description = form.description.data
            ldap_object_type.ranges = form.ranges.data
            ldap_object_type.apply_to = form.apply_to.data
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
            flash(u'{0} mis à jour'.format(ldap_object_type.description))
            return redirect(url_for('home'))
        form.label.data = ldap_object_type.label
        form.description.data = ldap_object_type.description
        form.ranges.data = ldap_object_type.ranges
        form.apply_to.data = ldap_object_type.apply_to
        form.object_classes.selected_oc.choices = selected_oc_choices
        form.object_classes.available_oc.choices = available_oc_choices

        return render_template('edit_ldap_object_type.html',
                               form=form)
    else:
        flash(u'Type d\'ID non trouvé')
        return redirect(url_for('show_ldap_object_types'))

@app.route('/add_ldap_object_type/', methods=('GET', 'POST'))
@login_required
def add_ldap_object_type():
    form = LDAPObjectTypeForm(request.form)
    if request.method == 'POST' and form.validate():
        ldap_object_type = LDAPObjectType()
        ldap_object_type.label = form.label.data
        # ldap_object_type.ranges = form.ranges.data
        db.session.add(ldap_object_type)
        db.session.commit()
        flash(u'Type d\'objet LDAP "{0}" ajouté'.format(ldap_object_type.label))
        return redirect(url_for('edit_ldap_object_type',
                                ldap_object_type_label= ldap_object_type.label))
    return render_template('add_ldap_object_type.html',
                               form=form)

@app.route('/delete_ldap_object_type/<ldap_object_type_label>')
@login_required
def delete_ldap_object_types(ldap_object_type_label):
    ldap_object_type = LDAPObjectType.query.filter_by(
        label=ldap_object_type_label
    ).delete()
    db.session.commit()
    flash(u'Objet {0} supprimé de la bdd'.format(ldap_object_type_label))
    return render_template('show_ldap_object_types.html')



@app.route('/show_ldap_object_types/')
@login_required
def show_ldap_object_types():
    ldap_object_types = LDAPObjectType.query.all()
    return render_template('show_ldap_object_types.html',
                           ldap_object_types=ldap_object_types)

### Helperz

def allowed_file(filename):
    print("filename : {0}".format(filename))
    print(filename.rsplit('.', 1)[1])

    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def set_default_quota_form_values(form, storage):
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

def set_quota_form_values(form, storage):
    default_inode_unit = form.cinesQuotaInodeHardTemp.unit.default
    default_size_unit = form.cinesQuotaSizeHardTemp.unit.default
    # default_storage_cn = get_default_storage_cn(storage['cn'][0])
    default_storage_cn = storage['cn'][0].split('.')[0]
    default_storage = get_default_storage(default_storage_cn).get_attributes()
    date_now = datetime.now()

    cinesQuotaSizeHardTemp = str(int(
        storage['cinesQuotaSizeHardTemp'][0] if
        'cinesQuotaSizeHardTemp' in storage
        else default_storage['cinesQuotaSizeHard'][0]
    ) / default_size_unit)
    cinesQuotaSizeSoftTemp = str(int(
        storage['cinesQuotaSizeSoftTemp'][0]if
        'cinesQuotaSizeSoftTemp' in storage
        else default_storage['cinesQuotaSizeSoft'][0]
    ) / default_size_unit)
    cinesQuotaInodeHardTemp = str(int(
        storage['cinesQuotaInodeHardTemp'][0]if
        'cinesQuotaInodeHardTemp' in storage
        else default_storage['cinesQuotaInodeHard'][0]
    ) / default_inode_unit)
    cinesQuotaInodeSoftTemp = str(int(
        storage['cinesQuotaInodeSoftTemp'][0]if
        'cinesQuotaInodeSoftTemp' in storage
        else default_storage['cinesQuotaInodeSoft'][0]
    ) / default_inode_unit)
    cinesQuotaSizeTempExpire = datetime.fromtimestamp(
        float(storage['cinesQuotaSizeTempExpire'][0])
    ) if 'cinesQuotaSizeTempExpire' in storage else date_now
    cinesQuotaInodeTempExpire =  datetime.fromtimestamp(
        float(storage['cinesQuotaInodeTempExpire'][0])
    ) if 'cinesQuotaInodeTempExpire' in storage else date_now

    # print('cinesQuotaSizeTempExpire {0}'.format(
    #     cinesQuotaSizeTempExpire))

    form.cinesQuotaSizeHardTemp.value.data= cinesQuotaSizeHardTemp
    form.cinesQuotaSizeSoftTemp.value.data= cinesQuotaSizeSoftTemp
    form.cinesQuotaInodeHardTemp.value.data= cinesQuotaInodeHardTemp
    form.cinesQuotaInodeSoftTemp.value.data= cinesQuotaInodeSoftTemp
    form.cinesQuotaSizeTempExpire.data = cinesQuotaSizeTempExpire
    form.cinesQuotaInodeTempExpire.data = cinesQuotaInodeTempExpire

def disable_account(user):
    user_attr = user.get_attributes()
    new_shadow_expire_datetime = datetime.now() - timedelta(days=1)
    new_shadow_expire = str(datetime_to_days_number(new_shadow_expire_datetime))
    ldap.update_uid_attribute(user_attr['uid'][0],
                              [('shadowExpire', new_shadow_expire)]
                          )
    flash(u'Compte {0} désactivé'.format(user_attr['uid'][0]))

def enable_account(user):
    user_uid = user.get_attributes()['uid'][0]
    if get_group_from_member_uid(user_uid) == 'ccc':
        new_shadow_expire_datetime = days_number_to_datetime(
            user.get_attributes()['cinesdaterenew'][0]
        ) + relativedelta(
            months = +app.config['SHADOW_DURATION']
        )
        new_shadow_expire = str(
            datetime_to_days_number(new_shadow_expire_datetime))
        ldap.update_uid_attribute(user_uid,
                                  [('shadowExpire', new_shadow_expire)]
        )
    else:
        ldap.remove_uid_attribute(user_uid,
                                  [('shadowExpire', None)])
    flash(u'Compte {0} activé'.format(user_uid))

def populate_lac_admin_choices(form):
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
    memberz = [ get_uid_from_dn(dn) for dn in ldap.get_ldap_admin_memberz() ]
    all_userz = get_all_users()
    selected_memberz = [ (uid, uid) for uid in memberz ]
    available_userz = [ (user.get_attributes()['uid'][0],
                         user.get_attributes()['uid'][0])
                        for user in all_userz
                        if user.get_attributes()['uid'][0] not in memberz]
    form.available_memberz.choices = available_userz
    form.selected_memberz.choices = selected_memberz

@app.before_first_request
def init_populate_grouplist_redis():
    populate_grouplist_redis()

def populate_grouplist_redis():
    grouplist = get_groupz_list()
    for (uid, group) in grouplist:
        r.hset('grouplist', uid, group)

@app.before_first_request
def init_populate_people_group_redis():
    populate_people_group_redis()


def populate_people_group_redis():
    for group in app.config['PEOPLE_GROUPS']:
        r.delete('groupz:{0}'.format(group))
        memberz = get_people_group_memberz(group)
        for member in memberz:
            r.sadd("groupz:{0}".format(group), member)



@app.before_first_request
def init_populate_work_group_redis():
    populate_work_group_redis()

@app.before_first_request
def init_populate_last_used_idz():
    populate_last_used_idz()

def populate_last_used_idz():
    ldap_otz = LDAPObjectType.query.all()
    for ldap_ot in ldap_otz:
        last_used_id = get_last_used_id(ldap_ot)
        # print('last_used_id : {0}'.format(last_used_id))
        ldap_ot.last_used_id = last_used_id
        db.session.add(ldap_ot)
    db.session.commit()

def populate_work_group_redis():
    for group in get_submission_groupz_list():
        r.delete('wrk_groupz:{0}'.format(group))
        memberz = get_work_group_memberz(group)
        for member in memberz:
            r.sadd("wrk_groupz:{0}".format(group), member)



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

def generate_edit_group_form(page, attributez):
    page_fieldz = dict(
        (row.label, row)
        for row in Field.query.filter_by(page_id = page.id).all()
    )

    class EditGroupForm(EditGroupBaseForm):
        pass

    attr_label_list = []
    print(attributez)
    for field_id in attributez:
        print('field_id {0}'.format(field_id))
        field = Field.query.filter_by(
            id = field_id
        ).first()
        attr_label_list.append(field.label)
        append_field_to_form(page_fieldz,
                             field.label,
                             EditGroupForm)

    form = EditGroupForm(request.form)
    return {'form': form }

def generate_edit_form(page, uid):
    page_fieldz = dict(
        (row.label.lower(), row)
        for row in Field.query.filter_by(page_id = page.id).all()
    )
    uid_attributez = ldaphelper.get_search_results(
        get_uid_detailz(uid)
    )[0].get_attributes()
    groupz_list = get_groupz_list()

    attributes = []
    class EditForm(Form):
        @classmethod
        def append_field(cls, name, field):
            setattr(cls, name, field)
            return cls

    for attr_name, attr_values in uid_attributez.iteritems():
        if attr_name in page_fieldz and page_fieldz[attr_name].edit:
            attributes.append(attr_name)
            append_fieldlist_to_form(page_fieldz, attr_name, EditForm)
    form = EditForm(request.form)
    return {'form' : form,
            'attributes': attributes}



def append_field_to_form(page_attrz, attr_name, form):
    date_formatz = ['Datetime', 'DaysNumber', 'GeneralizedTime']
    if page_attrz[attr_name].fieldtype.type == 'Text':
        setattr(form,
                attr_name,
                TextField(page_attrz[attr_name].description))
    elif page_attrz[attr_name].fieldtype.type in date_formatz:
        setattr(form,
                attr_name,
                DateField(page_attrz[attr_name].description))
    elif  page_attrz[attr_name].fieldtype.type == 'GIDNumber':
        setattr(form,
                attr_name,
                SelectField(page_attrz[attr_name].description,
                            choices=get_groupz_list()))
    elif page_attrz[attr_name].fieldtype.type == 'Submission':
        setattr(form,
                attr_name,
                FormField(EditSubmissionForm))

def append_fieldlist_to_form(page_attrz, attr_name, form):
    date_formatz = ['Datetime', 'DaysNumber', 'GeneralizedTime']
    if page_attrz[attr_name].fieldtype.type == 'Text':
        setattr(form,
                attr_name,
                FieldList(TextField(page_attrz[attr_name].description)))
    elif page_attrz[attr_name].fieldtype.type in date_formatz:
        setattr(form,
                attr_name,
                FieldList(DateField(page_attrz[attr_name].description)))
    elif  page_attrz[attr_name].fieldtype.type == 'GIDNumber':
        setattr(form,
                attr_name,
                FieldList(SelectField(page_attrz[attr_name].description,
                                      choices=get_groupz_list())))


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
    field_type = FieldType.query.filter_by(type='Text').first()
    page_attr = Field(label = attribute.label,
                      page = page,
                      ldapattribute = attribute,
                      fieldtype=field_type)
    db.session.add(page_attr)
    db.session.commit()
    return page_attr

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
def add_user_to_lac_admin(user):
    ldap.update_uid_attribute(user, pre_modlist)

def add_to_group_if_not_member(group, memberz_uid):
    populate_work_group_redis()
    memberz_dn = [ldap.get_full_dn_from_uid(uid)
                  for uid in memberz_uid]
    memberz_dn_filtered = [dn
                           for dn in memberz_dn
                           if dn not in r.smembers(
                                   "wrk_groupz:{0}".format(group))
    ]
    if memberz_dn_filtered:
        pre_modlist = [('uniqueMember', memberz_dn_filtered)]
        ldap.add_cn_attribute(group, pre_modlist)
        flash(u'Utilisateur(s) ajoutés au groupe')
    else:
        flash(u'Utilisateur(s) déjà membre(s) du groupe')

def rem_from_group_if_member(group, memberz_uid):
    populate_work_group_redis()
    memberz_dn = [ldap.get_full_dn_from_uid(uid)
                  for uid in memberz_uid]
    memberz_dn_filtered = [dn
                           for dn in memberz_dn
                           if dn in r.smembers(
                                   "wrk_groupz:{0}".format(group))
    ]
    if memberz_dn_filtered:
        pre_modlist = [('uniqueMember', memberz_dn_filtered)]
        ldap.remove_cn_attribute(group, pre_modlist)
        flash(u'Utilisateur(s) supprimé(s) du groupe')
    else:
        flash(u'Utilisateur(s) déjà supprimé(s) du groupe')


def get_default_storage_list():
    ldap_filter='(objectClass=cinesQuota)'
    attributes=['cn']
    base_dn='ou=quota,ou=system,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    storagez = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    return storagez

def get_group_quota_list():
    ldap_filter='(objectClass=cinesQuota)'
    attributes=['cn']
    base_dn='ou=groupePosix,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    storagez = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    return storagez


def get_default_storage(cn):
    ldap_filter='(&(objectClass=cinesQuota)(cn={0}))'.format(cn)
    attributes=['*']
    base_dn='ou=quota,ou=system,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    storage = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )[0]
    return storage

# def get_default_storage_cn(cn):
    # dn = ldap.get_full_dn_from_cn(cn)
    # m = re.search('(?<=cn={0},cn=)\w+'.format(cn), dn)
    # group_cn = m.group(0)
    # group_gid = get_gid_from_posix_group_cn(group_cn)
    # return cn.replace(group_gid, '')

def get_storage(cn):
    ldap_filter='(&(objectClass=cinesQuota)(cn={0}))'.format(cn)
    attributes=['*']
    base_dn='ou=groupePosix,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    storage = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )[0]
    return storage





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

def get_page_oc_choices(page):
    page_oc_list = PageObjectClass.query.filter_by(page_id=page.id).all()
    select_oc_choices = filter(None,[(oc.ldapobjectclass.id,
                                      oc.ldapobjectclass.label)
                                     for oc in page_oc_list ])
    return select_oc_choices

def get_ot_oc_choices(object_type):
    ot_oc_list = LDAPObjectTypeObjectClass.query.filter_by(
        ldapobjecttype_id=object_type.id).all()
    select_oc_choices = filter(None,[(oc.ldapobjectclass.id,
                                      oc.ldapobjectclass.label)
                                     for oc in ot_oc_list ])
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

def get_posix_groupz_memberz(group_list):
    memberz = []
    for group in group_list:
        memberz.extend(get_posix_group_memberz(group))
    return memberz

# def get_groupz_person_memberz(group_list):
#     memberz = []
#     for group in group_list:
#         memberz.extend(get_people_group_memberz(group))
#     return memberz

def get_posix_group_memberz(group):
    """
    List memberz of a group inherited from people ou
    """
    ldap_filter='(cn={0})'.format(group)
    attributes=['memberUid']
    base_dn='ou=groupePosix,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    print(base_dn)
    records = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    print(records)
    memberz = records[0].get_attributes()['memberUid']
    return memberz

def get_people_group_memberz(group):
    """
    List memberz of a group inherited from people ou
    """
    ldap_filter='(objectclass=inetOrgPerson)'
    attributes=['uid']
    base_dn='ou={0},ou=people,{1}'.format(group,app.config['LDAP_SEARCH_BASE'])

    records = ldaphelper.get_search_results(
        ldap.admin_search(base_dn,ldap_filter,attributes)
    )
    memberz = [ member.get_attributes()['uid'][0] for member in records]
    return memberz

def get_work_group_memberz(group):
    """
    List memberz of a group inherited from grTravail ou
    """
    ldap_filter='(objectclass=cinesGrWork)'
    attributes=['uniqueMember']
    base_dn='cn={0},ou=grTravail,{1}'.format(
        group,app.config['LDAP_SEARCH_BASE']
    )

    records = ldaphelper.get_search_results(
        ldap.admin_search(base_dn,ldap_filter,attributes)
    )
    memberz = []
    for member in records:
        memberz.extend(member.get_attributes()['uniqueMember'])
    return memberz

def get_groupz_list():
    ldap_filter = "(objectClass=posixGroup)"
    ldap_groupz = ldap.admin_search(ldap_filter=ldap_filter,
                                    attributes=['cn', 'gidNumber'])
    ldap_groupz  = ldaphelper.get_search_results(ldap_groupz)
    ldap_groupz_list = []
    for group in ldap_groupz:
        group_attrz = group.get_attributes()
        ldap_groupz_list.append((group_attrz['gidNumber'][0],
                                 group_attrz['cn'][0]))

    return ldap_groupz_list

def get_submission_groupz_list():
    ldap_filter = "(&(objectClass=cinesGrWork)(cinesGrWorkType=1))"
    ldap_groupz = ldaphelper.get_search_results(
        ldap.admin_search(ldap_filter=ldap_filter,
                         attributes=['cn'])
    )
    ldap_groupz_list = []
    for group in ldap_groupz:
        group_attrz = group.get_attributes()
        name = group_attrz['cn'][0]
        ldap_groupz_list.append(name)

    return ldap_groupz_list


def get_uid_detailz(uid):
    ldap_filter='(uid={0})'.format(uid)
    attributes=['*','+']
    detailz = ldap.search(ldap_filter=ldap_filter,attributes=attributes)
    return detailz

# def get_lac_admin_memberz():
#     ldap_filter='(cn=lacadmin)'
#     attributes=['member']
#     raw_resultz = ldaphelper.get_search_results(
#         ldap.search(ldap_filter=ldap_filter,attributes=attributes)
#     )
#     memberz = raw_resultz[0].get_attributes()['member']
#     return memberz

def get_uid_from_dn(dn):
    m = re.search('uid=(.+?),', dn)
    if m:
        return m.group(1)
    else:
        return ''

def get_all_users():
    base_dn='ou=people,dc=cines,dc=fr'
    ldap_filter='(objectclass=inetOrgPerson)'
    attributes=['*','+']
    userz = ldaphelper.get_search_results(
        ldap.search(ldap_filter=ldap_filter,
                    attributes=attributes,
                    base_dn=base_dn)
    )
    return userz

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

def is_active(user):
    user_attrz = user.get_attributes()
    if 'shadowExpire' in user_attrz and datetime.now()>days_number_to_datetime(
            user_attrz['shadowExpire'][0]
    ):
        return False
    else:
        return True


def set_submission(uid, group, state):
    old_cines_soumission = ldaphelper.get_search_results(
        ldap.search(
            ldap_filter='(uid={0})'.format(uid),
            attributes=['cinesSoumission']
        )
    )[0].get_attributes()['cinesSoumission'][0]
    new_cines_soumission = re.sub(r'(.*{0}=)\d(.*)'.format(group),
                                  r"\g<1>{0}\2".format(str(state)),
                                  old_cines_soumission)
    pre_modlist = [('cinesSoumission', new_cines_soumission)]
    ldap.update_uid_attribute(uid, pre_modlist)
    flash(u'Soumission mis à jour pour le groupe {0}'.format(group))

def update_default_quota(storage_cn, form):
    cinesQuotaSizeHard = str(
        int(
            form.cinesQuotaSizeHard.value.data
        ) * int(
            form.cinesQuotaSizeHard.unit.data)
    ).encode('utf-8')
    cinesQuotaSizeSoft = str(
        int(
            form.cinesQuotaSizeSoft.value.data
        ) * int(
            form.cinesQuotaSizeSoft.unit.data)
    ).encode('utf-8')
    cinesQuotaInodeHard = str(
        int(
            form.cinesQuotaInodeHard.value.data
        ) * int(
            form.cinesQuotaInodeHard.unit.data)
    ).encode('utf-8')
    cinesQuotaInodeSoft = str(
        int(
            form.cinesQuotaInodeSoft.value.data
        ) * int(
            form.cinesQuotaInodeSoft.unit.data)
    ).encode('utf-8')
    pre_modlist = [('cinesQuotaSizeHard', cinesQuotaSizeHard),
                   ('cinesQuotaSizeSoft', cinesQuotaSizeSoft),
                   ('cinesQuotaInodeHard', cinesQuotaInodeHard),
                   ('cinesQuotaInodeSoft', cinesQuotaInodeSoft)]
    ldap.update_cn_attribute(storage_cn, pre_modlist)


def update_quota(storage_cn, form):
    cinesQuotaSizeHardTemp = str(
        int(
            form.cinesQuotaSizeHardTemp.value.data
        ) * int(
            form.cinesQuotaSizeHardTemp.unit.data)
    ).encode('utf-8')
    cinesQuotaSizeSoftTemp = str(
        int(
            form.cinesQuotaSizeSoftTemp.value.data
        ) * int(
            form.cinesQuotaSizeSoftTemp.unit.data)
    ).encode('utf-8')
    cinesQuotaInodeHardTemp = str(
        int(
            form.cinesQuotaInodeHardTemp.value.data
        ) * int(
            form.cinesQuotaInodeHardTemp.unit.data)
    ).encode('utf-8')
    cinesQuotaInodeSoftTemp = str(
        int(
            form.cinesQuotaInodeSoftTemp.value.data
        ) * int(
            form.cinesQuotaInodeSoftTemp.unit.data)
    ).encode('utf-8')
    pre_modlist = [('cinesQuotaSizeHardTemp',
                    cinesQuotaSizeHardTemp),
                   ('cinesQuotaSizeSoftTemp',
                    cinesQuotaSizeSoftTemp),
                   ('cinesQuotaInodeHardTemp',
                    cinesQuotaInodeHardTemp),
                   ('cinesQuotaInodeSoftTemp',
                    cinesQuotaInodeSoftTemp),
                   ('cinesQuotaSizeSoftTempExpire',
                    form.cinesQuotaSizeSoftTempExpire.data.encode('utf-8')),
                   ('cinesQuotaInodeTempExpire',
                    form.cinesQuotaInodeTempExpire.data.encode('utf-8'))
    ]
    ldap.update_cn_attribute(storage_cn, pre_modlist)


# def get_soumission(uid, group):
#     submission = ldap.search(
#         ldap_filter='(uid={0})'.format(uid),
#         attributes=['cinesSoumission']
#     ).get_attributes()['cinesSoumission'][0]
#     m = re.search('(?<={0}=)\d'.format(group), submission)
#     return m.group(0)

def generalized_time_to_datetime(generalized_time):
    created_datetime = datetime.strptime(
        generalized_time, "%Y%m%d%H%M%SZ"
    )
    created_datetime = utc.localize(created_datetime)
    created_datetime = created_datetime.astimezone(
        timezone(app.config['TIMEZONE'])
    )
    return created_datetime

def datetime_to_days_number(datetime):
    return int(datetime.strftime("%s"))/86400

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

def get_gid_from_posix_group_cn(cn):
    for gid, group_cn in r.hgetall('grouplist').iteritems():
        if group_cn == cn:
            return gid

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
    app.run(host='0.0.0.0')
