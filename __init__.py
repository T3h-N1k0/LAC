# -*- coding: utf-8 -*-
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response
from flask.ext.ldap import LDAP, login_required, admin_login_required
from flask.ext.sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug import secure_filename
from flask_bootstrap import Bootstrap
from sqlalchemy import Table, Column, Integer, ForeignKey, func
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
# from data_modelz import *
# Custom modulez
from formz import *

__author__ = "Nicolas CHATELAIN"
__copyright__ = "Copyright 2014, Nicolas CHATELAIN @ CINES"
__license__ = "GPL"


app = Flask(__name__)
ldap = LDAP(app)

app.config.from_object('config')

app.config['SQLALCHEMY_BINDS'] = {
    'lac': app.config['LAC_DB_URI'],
    'otrs': app.config['OTRS_DB_URI'],
    'gescli': app.config['GESCLI_DB_URI'],
    'gescpt': app.config['GESCPT_DB_URI']

}
db = SQLAlchemy(app)
Bootstrap(app)

utc = pytz.utc
r = redis.Redis('localhost')

# Add login URL associated with login function
app.add_url_rule('/login', 'login', ldap.login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', ldap.logout, methods=['GET', 'POST'])


ALLOWED_EXTENSIONS = set(['txt', 'csv'])


### Data Model

# One to many : LDAPObjectClass (1)---(n) LDAPAttributes
# Many to one : LDAPObjectClass (n)---(1) PageObjectClass
# Many to one : LDAPObjectClass (n)---(1) LDAPObjectType
class LDAPObjectClass(db.Model):
    __bind_key__ = 'lac'
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
    __bind_key__ = 'lac'
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
    __bind_key__ = 'lac'
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
    __bind_key__ = 'lac'
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
    __bind_key__ = 'lac'
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
    __bind_key__ = 'lac'
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
    __bind_key__ = 'lac'
    __tablename__ = 'fieldtype'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(80))

    fields = db.relationship('Field',
                          backref='fieldtype',
                          lazy='dynamic')

# Many to one : LDAPObjectTypeObjectClass (n)---(1) LDAPObjectType
# Many to one : LDAPObjectTypeObjectClass (n)---(1) LDAPObjectClass
class LDAPObjectTypeObjectClass(db.Model):
    __bind_key__ = 'lac'
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
    __bind_key__ = 'lac'
    __tablename__ = 'ldapobjecttype'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(50))
    ranges = db.Column(db.String(200))
    apply_to = db.Column(db.String(20))
    last_used_id = db.Column(db.Integer)
    ppolicy = db.Column(db.String(50))

    ldapobjecttypeobjectclasses = db.relationship("LDAPObjectTypeObjectClass",
                                     backref="ldapobjecttype",
                                     lazy='dynamic')


class Filesystem(db.Model):
    __bind_key__ = 'lac'
    __tablename__ = 'filesystem'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(50))

    def __init__(self, label, description):
        self.description = description
        self.label = label

class Shell(db.Model):
    __bind_key__ = 'lac'
    __tablename__ = 'shell'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(50), unique=True)
    label = db.Column(db.String(50))

    def __init__(self, label, path):
        self.path = path
        self.label = label

class User(db.Model):
    __bind_key__ = 'lac'
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(200), unique=True)
    binds = db.relationship('UserBind',
                            backref="user",
                            lazy='dynamic',
                            order_by='desc(UserBind.time)')

class UserBind(db.Model):
    __bind_key__ = 'lac'
    __tablename__ = 'userbind'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('user.id',
                                               onupdate="CASCADE",
                                               ondelete="CASCADE"))
    time = db.Column(db.DateTime)


class OTRSCustomerUser(db.Model):
    __bind_key__ = 'otrs'
    __tablename__ = 'customer_user'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(200), unique=True)
    email = db.Column(db.String(150))
    customer_id = db.Column(db.String(150))
    # pw = db.Column(db.String(64))
    # title = db.Column(db.String(50))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(150))
    # fax = db.Column(db.String(150))
    # mobile = db.Column(db.String(150))
    # street = db.Column(db.String(150))
    # zip = db.Column(db.String(200))
    # city = db.Column(db.String(200))
    # country = db.Column(db.String(200))
    comments = db.Column(db.String(250))
    valid_id = db.Column(db.Integer)
    create_time = db.Column(db.DateTime)
    # create_by = db.Column(db.Integer)
    # change_time = db.Column(db.DateTime)
    # change_by = db.Column(db.Integer)


class OTRSTicket(db.Model):
    __bind_key__ = 'otrs'
    __tablename__ = 'ticket'
    id = db.Column(db.Integer, primary_key=True)
    customer_user_id = db.Column(db.String(250))

class OTRSUser(db.Model):
    __bind_key__ = 'otrs'
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    valid_id = db.Column(db.Integer)
    login = db.Column(db.String(200), unique=True)
    change_time = db.Column(db.DateTime)

class C4Ressource(db.Model):
    __bind_key__ = 'gescli'
    __tablename__ = 'RESSOURCE{0}'.format(datetime.now().strftime('%Y'))
    code_dossier_ressource = db.Column(db.String(15), primary_key=True)
    code_comite = db.Column(db.Integer, db.ForeignKey('COMITE.code_comite'))
    code_projet = db.Column(db.String(8),
                            db.ForeignKey('PROJET.code_projet'))
    demande_uc_ibm = db.Column(db.Integer)
    demande_uc_sgi = db.Column(db.Integer)
    accorde_uc_ibm = db.Column(db.Integer)
    accorde_uc_sgi = db.Column(db.Integer)

class C4Comite(db.Model):
    __bind_key__ = 'gescli'
    __tablename__ = 'COMITE'
    code_comite = db.Column(db.Integer, primary_key=True)
    ct = db.Column(db.String(8))
    intitule_comite = db.Column(db.String(80))
    ressources = db.relationship('C4Ressource', backref='comite',
                                 lazy='dynamic')

class C4Personne(db.Model):
    __bind_key__ = 'gescli'
    __tablename__ = 'PERSONNE'
    code_personne = db.Column(db.Integer, primary_key=True)
    nom_personne = db.Column(db.String(30))
    prenom_personne = db.Column(db.String(30))
    code_adresse = db.Column(db.Integer,
                             db.ForeignKey('ADRESSE.code_adresse'))
    code_qualite = db.Column(db.String(8),
                             db.ForeignKey('QUALITE.code_qualite'))
    code_profil = db.Column(db.String(15),
                            db.ForeignKey('PROFIL.code_profil'))
    telephone_personne  = db.Column(db.String(20))
    fax_personne = db.Column(db.String(20))
    bal_personne = db.Column(db.String(50))
    projets = db.relationship('C4Projet', backref='personne',
                              lazy='dynamic')

class C4Adresse(db.Model):
    __bind_key__ = 'gescli'
    __tablename__ = 'ADRESSE'
    code_adresse = db.Column(db.Integer, primary_key=True)
    laboratoire_adresse = db.Column(db.String(50))
    organisme_adresse = db.Column(db.String(50))
    adresse1_adresse = db.Column(db.String(50))
    adresse2_adresse = db.Column(db.String(50))
    cdpostal_adresse = db.Column(db.String(10))
    ville_adresse = db.Column(db.String(50))
    pays_adresse = db.Column(db.String(20))
    personnes = db.relationship('C4Personne', backref='adresse',
                                 lazy='dynamic')

class C4Qualite(db.Model):
    __bind_key__ = 'gescli'
    __tablename__ = 'QUALITE'
    code_qualite = db.Column(db.String(8), primary_key=True)
    libelle_qualite = db.Column(db.String(50))
    personnes = db.relationship('C4Personne', backref='qualite',
                                 lazy='dynamic')

class C4Profil(db.Model):
    __bind_key__ = 'gescli'
    __tablename__ = 'PROFIL'
    code_profil = db.Column(db.String(15), primary_key=True)
    libelle_profil = db.Column(db.String(50))
    personnes = db.relationship('C4Personne', backref='profil',
                                lazy='dynamic')

class C4Projet(db.Model):
    __bind_key__ = 'gescli'
    __tablename__ = 'PROJET{0}'.format(datetime.now().strftime('%Y'))
    code_projet = db.Column(db.String(8), primary_key=True)
    code_personne = db.Column(db.Integer,
                              db.ForeignKey('PERSONNE.code_personne'))
    intitule_projet = db.Column(db.String(50))

    # ressources = db.relationship('C4Ressource',
    #                              backref='projet',
    #                              lazy='dynamic',
    #                              uselist=False)


class C4SGI(db.Model):
    __bind_key__ = 'gescpt'
    __tablename__ = 'SGI{0}'.format(datetime.now().strftime('%Y'))
    grpunix = db.Column(db.String(255), primary_key=True)
    walltime = db.Column(db.Float())
    nbcoeurs = db.Column(db.Integer)


class C4IBM(db.Model):
    __bind_key__ = 'gescpt'
    __tablename__ = 'IBM{0}'.format(datetime.now().strftime('%Y'))
    grpunix = db.Column(db.String(255), primary_key=True)
    walltime = db.Column(db.Float())
    nbcoeurs = db.Column(db.Integer)


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
        if form.ip.data :
            filter_list.append("(cinesIpClient={0})".vormat(form.ip.data))
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
    pwd_policy = get_user_pwd_policy(uid)
    pwd_min_length = pwd_policy['pwdMinLength'][0]
    # pwd_max_age =



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
            return redirect(url_for('show_user',
                                    page= get_group_from_member_uid(uid),
                                    uid=uid))
        else:
            ldap.change_passwd(uid, session['password'], form.new_pass.data)
            flash(
                u'Votre mot de passe a été mis à jour avec succès.'.format(uid)
            )
            return redirect(url_for('home'))

        ldap.update_uid_attribute(uid, pre_modlist)

    return render_template('change_password.html',
                           form=form,
                           uid=uid,
                           pwd_min_length=pwd_min_length)


@app.route('/people/<group>')
@login_required
def show_group_memberz(group):
    memberz = r.smembers("groupz:{0}".format(group))
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


@app.route('/show_user/<page>/<uid>')
@login_required
def show_user(page, uid):
    dn = ldap.get_full_dn_from_uid(uid)
    page = Page.query.filter_by(label = page).first()
    page_fieldz = dict(
        (row.label.lower(), row)
        for row in Field.query.filter_by(page_id = page.id).all()
    )
    raw_detailz = get_uid_detailz(uid)
    if not raw_detailz:
        flash(u'Utilisateur non trouvé')
        return redirect(url_for('home'))
    uid_detailz = ldaphelper.get_search_results(raw_detailz)[0]
    uid_attributez=uid_detailz.get_attributes()
    work_groupz = get_work_groupz_from_member_uid(uid)
    sec_groupz = get_posix_groupz_from_member_uid(uid)
    if 'cinesSoumission' in uid_attributez:
        submission_list = get_list_from_submission_attr(
            uid_attributez['cinesSoumission'][0])
    else:
        submission_list = []
    return render_template('show_user.html',
                           uid = uid,
                           dn=dn,
                           uid_attributez=uid_attributez,
                           page_fieldz=page_fieldz,
                           is_active=is_active(uid_detailz),
                           work_groupz=work_groupz,
                           sec_groupz=sec_groupz,
                           submission_list=submission_list)

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



@app.route('/add_user/<page_label>/<uid>', methods=('GET', 'POST'))
@app.route('/add_user/', methods=('GET', 'POST'))
@login_required
def add_user(page_label=None,uid=None):
    pages = Page.query.all()
    ldap_object_types = LDAPObjectType.query.all()

    existing_userz = [
        user.get_attributes()['uid'][0] for user in get_all_users()]

    set_validators_to_form_field(
        AddUserForm, 'uid',[validators.NoneOf(existing_userz)])

    add_form = AddUserForm(request.form)
    add_form.group.choices = get_posix_groupz_choices()
    add_form.ldap_object_type.choices = [
        (ldap_object_type.id,
         ldap_object_type.label)
        for ldap_object_type in ldap_object_types
        if ldap_object_type.apply_to == "user"]


    if request.method == 'POST':
        if add_form.ldap_object_type.data:
            page_label = LDAPObjectType.query.filter_by(
                id = add_form.ldap_object_type.data
            ).first().label
        print(page_label)
        ldap_object_type = LDAPObjectType.query.filter_by(
            label = page_label
        ).first()
        page = Page.query.filter_by(
            label = ldap_object_type.label
        ).first()
        fieldz = Field.query.filter_by(page_id = page.id,edit = True).all()
        fieldz_labelz = [field.label for field in fieldz]
        EditForm = generate_edit_user_form_class(page)
        edit_form = EditForm(request.form)

        if add_form.uid.data and add_form.validate():
            print("group from form {0}".format(add_form.ldap_object_type.data))
            set_edit_user_form_values(edit_form,fieldz)
            return render_template('add_user.html',
                                   page=page.label,
                                   uid=add_form.uid.data,
                                   fieldz=fieldz,
                                   edit_form=edit_form)

        elif uid:
            create_ldap_object_from_add_user_form(
                edit_form,
                fieldz_labelz,
                uid,
                page)

            if app.config['PROD_FLAG']:
                upsert_otrs_user(uid)
            return redirect(url_for('show_user',
                                    page=page_label,
                                    uid = uid))
    return render_template('add_user.html',
                           add_form=add_form)

@app.route('/edit_user/<page>/<uid>', methods=('GET', 'POST'))
@login_required
def edit_user(page,uid):
    dn = ldap.get_full_dn_from_uid(uid)
    page = Page.query.filter_by(label=page).first()
    EditForm = generate_edit_user_form_class(page)
    form = EditForm(request.form)
    fieldz = Field.query.filter_by(page_id = page.id,edit = True).all()
    fieldz_labelz = [field.label for field in fieldz]


    if request.method == 'POST':
        update_ldap_object_from_edit_user_form(form,fieldz_labelz,uid)

        for group in form.wrk_groupz.selected_groupz.data:
            add_to_group_if_not_member(group, [uid])
        for group in get_work_groupz_from_member_uid(uid):
            if group not in form.wrk_groupz.selected_groupz.data:
                rem_from_group_if_member(group, [uid])

        if page.label in app.config['OTRS_ACCOUNT'] and app.config['PROD_FLAG']:
            upsert_otrs_user(uid)
        return redirect(url_for('show_user', page=page.label, uid=uid))
    else:
        set_edit_user_form_values(form, fieldz, uid)
    return render_template('edit_user.html',
                           form=form,
                           page=page,
                           uid=uid,
                           dn=dn,
                           fieldz=fieldz)

@app.route('/delete_user/<uid>', methods=('GET', 'POST'))
@login_required
def delete_user(uid):
    groupz = get_posix_groupz_from_member_uid(uid)
    dn = ldap.get_full_dn_from_uid(uid)
    if request.method == 'POST':
        user_dn = ldap.get_full_dn_from_uid(uid)
        ldap.delete(user_dn)
        for group in groupz:
            # group_dn = ldap.get_full_dn_from_cn(group)
            pre_modlist = [('memberUid', uid.encode('utf-8'))]
            ldap.remove_cn_attribute(group,pre_modlist)

        if app.config['PROD_FLAG']:
            delete_otrs_user(uid)
        flash(u'Utilisateur {0} supprimé'.format(uid))
        return redirect(url_for('home'))

    return render_template('delete_user.html',
                           groupz=groupz,
                           uid=uid,
                           dn=dn)

@app.route('/select_work_groups/<uid>', methods=('GET', 'POST'))
@login_required
def select_work_groups(uid):
    form = generate_select_work_group_form(uid)

    if request.method == 'POST':
        for group in form.selected_groupz.data:
            add_to_group_if_not_member(group, [uid])
        for group in actual_work_groupz:
            if group not in form.selected_groupz.data:
                rem_from_group_if_member(group, [uid])
        flash(u'Groupes de travail mis à jour')
        return redirect(url_for('show_user',
                                page=get_group_from_member_uid(uid),
                                uid=uid))
    return render_template('select_work_groups.html',
                           form=form,
                           uid=uid)

# @app.route('/select_edit_group_attributes/', methods=('GET', 'POST'))
# @login_required
# def select_edit_group_attributes():
#     view_form = EditGroupViewForm(request.form)
#     view_form.attr_form.available_attr.choices = [
#         (attr.id, attr.label)
#         for attr in LDAPAttribute.query.all()
#     ]
#     view_form.attr_form.selected_attr.choices = []

@app.route('/select_group_type/', methods=('GET', 'POST'))
@login_required
def select_group_type():
    ldap_object_types = LDAPObjectType.query.all()
    form = SelectGroupTypeForm(request.form)
    form.group_type.choices = [(ot.label, ot.description)
                                   for ot in ldap_object_types
                                   if ot.apply_to == 'group']

    if request.method == 'POST':
        return redirect(url_for('add_group',
                                page_label = form.group_type.data))


# @app.route('/add_group/', methods=('GET', 'POST'))
@app.route('/add_group/<page_label>', methods=('GET', 'POST'))
@login_required
def add_group(page_label=None):
    pages = Page.query.all()

    if page_label in app.config['C4_TYPE_GROUPZ']:
        add_form = AddC4GroupForm(request.form)
        add_form.cn.choices = get_c4_groupz_choices()
    else:
        existing_groupz = [
            group.get_attributes()['cn'][0] for group in get_all_groups()]

        set_validators_to_form_field(
            AddGenericGroupForm, 'cn',[validators.NoneOf(existing_groupz)])
        add_form = AddGenericGroupForm(request.form)
    add_form.filesystem.choices = get_filesystem_choices()

    if request.method == 'POST':
        if add_form.cn.data and add_form.validate():
            create_ldap_object_from_add_group_form(add_form)
            return redirect(url_for("home"))
    return render_template('add_group.html',
                           add_form=add_form)

@app.route('/edit_group/<branch>/<group_cn>', methods=('GET', 'POST'))
@login_required
def edit_group(branch, group_cn):
    dn = ldap.get_full_dn_from_cn(group_cn)
    page = Page.query.filter_by(label=branch).first()
    form = generate_edit_group_form(page)
    fieldz = Field.query.filter_by(page_id = page.id,
                                   edit = True).all()

    if request.method == 'POST':
        update_ldap_object_from_edit_group_form(form,page,group_cn)
        flash(u'Groupe {0} mis à jour'.format(group_cn))
        return redirect(url_for('show_groups', branch=page.label))
    else:
        set_edit_group_form_values(form, fieldz, group_cn)

    if branch == 'grCcc':
        comite = C4Ressource.query.filter_by(
            code_projet = group_cn).first().comite.ct
        update_group_memberz_cines_c4(group_cn, comite)

    return render_template('edit_group.html',
                           form=form,
                           page=page,
                           dn=dn,
                           group_cn=group_cn,
                           fieldz=fieldz)

@app.route('/delete_group/<branch>/<cn>')
@login_required
def delete_group(branch, cn):
    if get_posix_group_memberz(cn):
        flash(u'Le groupe n\'est pas vide.\nImpossible de supprimer le groupe.')
    else:
        dn = ldap.get_full_dn_from_cn(cn)
        ldap.delete(dn)
        flash(u'Groupe {0} supprimé'.format(cn))
    return redirect(url_for('show_group',
                            branch=branch,
                            cn=cn))


@app.route('/show_group/<branch>/<cn>')
@login_required
def show_group(branch, cn):
    dn = ldap.get_full_dn_from_cn(cn)
    page = Page.query.filter_by(label = branch).first()
    page_fieldz = dict(
        (row.label.lower(), row)
        for row in Field.query.filter_by(page_id = page.id).all()
    )
    ldap_filter='(cn={0})'.format(cn)
    attributes=['*','+']
    raw_detailz = ldap.search(ldap_filter=ldap_filter,attributes=attributes)
    if not raw_detailz:
        flash(u'Groupe non trouvé')
        return redirect(url_for('show_groups',
                                branch=branch))
    cn_attributez=ldaphelper.get_search_results(raw_detailz)[0].get_attributes()
    if branch == 'grCcc':
        ressource = C4Ressource.query.filter_by(code_projet = cn).first()
        code_personne = C4Projet.query.filter_by(
            code_projet = cn).first().code_personne
        manager = C4Personne.query.filter_by(
            code_personne=code_personne).first()
        sgi_computed = db.session.query(
            func.sum(C4SGI.walltime * C4SGI.nbcoeurs) / 3600
        ).filter_by(grpunix=cn).group_by(C4SGI.grpunix).first()
        ibm_computed = db.session.query(
            func.sum(C4IBM.walltime * C4IBM.nbcoeurs) / 3600
        ).filter_by(grpunix=cn).group_by(C4IBM.grpunix).first()
        if ibm_computed:
            ibm_computed = int(ibm_computed[0])
        if sgi_computed:
            sgi_computed = int(sgi_computed[0])
    else:
        ressource = None
        manager = None
        sgi_computed = None
        ibm_computed = None
        # update_group_memberz_cines_c4(cn, comite.ct)
    return render_template('show_group.html',
                           cn = cn,
                           dn=dn,
                           cn_attributez=cn_attributez,
                           page_fieldz=page_fieldz,
                           branch=branch,
                           ressource=ressource,
                           manager=manager,
                           sgi_computed=sgi_computed,
                           ibm_computed=ibm_computed)

# @app.route('/delete_group/<cn>', methods=('GET', 'POST'))
# @login_required
# def delete_group(cn):
#     group_dn = ldap.get_full_dn_from_cn(cn)
#     ldap.delete(group_dn)
#     flash(u'Groupe {0} supprimé'.format(cn))
#     return redirect(url_for('home'))

@app.route('/show_groups/<branch>')
# @app.route('/show_groups/')
@login_required
def show_groups(branch):
    # print(branch)
    groupz = [group.get_attributes()['cn'][0]
              for group in  get_posix_groupz(branch)]
    return render_template('show_groupz.html',
                           groupz=groupz,
                           branch=branch)


@app.route('/edit_by_group/', methods=('GET', 'POST'))
@login_required
def edit_by_group():
    page = Page.query.filter_by(label='edit_by_group').first()
    view_form = EditGroupViewForm(request.form)
    view_form.attr_form.available_attr.choices = [
        (attr.id, attr.label)
        for attr in Field.query.filter_by(page_id = page.id).all()
    ]
    view_form.attr_form.selected_attr.choices = []
    if 'edit_by_group_fieldz_id' in session:
        attrz_list = session['edit_by_group_fieldz_id']
    else:
        attrz_list = []

    if 'edit_by_group_memberz_uid' in session:
        groupz_memberz = session['edit_by_group_memberz_uid']
    else:
        groupz_memberz = []
    # print('attrz_list : {0}'.format(attrz_list))
    edit_form = generate_kustom_batch_edit_form(page, attrz_list)
    group_form = SelectGroupzForm(request.form)
    group_form.available_groupz.choices = get_posix_groupz_choices()
    group_form.selected_groupz.choices = []


    if request.method == 'POST':

        if view_form.attr_form.selected_attr.data:
            group_form = SelectGroupzForm(request.form)
            group_form.available_groupz.choices = get_posix_groupz_choices()
            group_form.selected_groupz.choices = []

            session[
                'edit_by_group_fieldz_id'
            ] = view_form.attr_form.selected_attr.data
            return render_template('edit_by_group.html',
                                   group_form=group_form)

        elif group_form.selected_groupz.data:
            groupz_id = group_form.selected_groupz.data
            groupz_label = [ get_posix_group_cn_by_gid(id)
                             for id in groupz_id ]
            groupz_memberz = get_posix_groupz_memberz(groupz_label)

            session[
                'edit_by_group_memberz_uid'
            ] = groupz_memberz

            fieldz = Field.query.filter(
                Field.id.in_(session['edit_by_group_fieldz_id'])
            ).all()
            print('fieldz {0}'.format(fieldz))

            edit_form = generate_kustom_batch_edit_form(
                page,
                session['edit_by_group_fieldz_id']
            )

            return render_template('edit_by_group.html',
                                   edit_form=edit_form,
                                   fieldz=fieldz,
                                   attributez=[field.label.encode('utf-8')
                                                      for field in fieldz])

        elif edit_form.action.data :
            fieldz = Field.query.filter(
                Field.id.in_(session['edit_by_group_fieldz_id'])
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
            flash(u'Les groupes ont été mis à jour')
            # if edit_form.backup.data:
            #     return get_backup_file(
            #         groupz_memberz,
            #         [field.label.encode('utf-8') for field in fieldz])
            return redirect(url_for('home'))
    return render_template('edit_by_group.html',
                           view_form=view_form)


@app.route('/edit_submission/<uid>', methods=('GET', 'POST'))
@login_required
def edit_submission(uid):
    dn = ldap.get_full_dn_from_uid(uid)
    form = EditSubmissionForm(request.form)
    form.wrk_group.choices = [
        (group, group)
        for group in get_submission_groupz_list()
    ]
    raw_detailz = get_uid_detailz(uid)
    if not raw_detailz:
        flash(u'Utilisateur non trouvé')
        return redirect(url_for('home'))
    uid_detailz = ldaphelper.get_search_results(raw_detailz)[0]
    uid_attributez=uid_detailz.get_attributes()
    if 'cinesSoumission' in uid_attributez:
        submission_list = get_list_from_submission_attr(
            uid_attributez['cinesSoumission'][0])
    else:
        submission_list = []

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
                           dn=dn,
                           uid=uid,
                           submission_list=submission_list)

@app.route('/edit_group_submission/', methods=('GET', 'POST'))
@login_required
def edit_group_submission():
    form = EditGroupSubmissionForm(request.form)
    form.submission_form.wrk_group.choices = [
        (group, group)
        for group in get_submission_groupz_list()
    ]
    form.group_form.available_groupz.choices = get_posix_groupz_choices()
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
    return redirect(url_for('show_user',
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
        dn = ldap.get_full_dn_from_cn(storage_cn)
        storage = get_default_storage(storage_cn).get_attributes()
        form = EditDefaultQuotaForm(request.form)

        if request.method == 'POST' and form.validate():
            update_default_quota(storage_cn, form)
            return redirect(url_for('home'))
        set_default_quota_form_values(form, storage)
        return render_template('edit_default_quota.html',
                               form=form,
                               dn=dn,
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
        dn = ldap.get_full_dn_from_cn(storage_cn)
        storage = get_storage(storage_cn).get_attributes()
        form = EditQuotaForm(request.form)

        if request.method == 'POST' and form.validate():
            update_quota(storage, form)
            return redirect(url_for('home'))
        default_fieldz = set_quota_form_values(form, storage)
        return render_template('edit_quota.html',
                               form=form,
                               dn=dn,
                               storage_cn=storage_cn,
                               default_fieldz=default_fieldz)

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
    form.group.choices = get_posix_groupz_choices()

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


@app.route('/delete_quota/<storage_cn>')
@login_required
def delete_quota(storage_cn):
    storage_dn = ldap.get_full_dn_from_cn(storage_cn)
    ldap.delete(storage_dn)
    flash(u'Quota {0} supprimé'.format(storage_cn))
    return redirect(url_for('edit_quota'))

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

    edit_form = generate_kustom_batch_edit_form(page, attrz_list)
    file_form = UserzFileForm(request.form)

    if request.method == 'POST':

        if view_form.attr_form.selected_attr.data:
            group_form = SelectGroupzForm(request.form)
            group_form.available_groupz.choices = get_posix_groupz_choices()
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

            edit_form = generate_kustom_batch_edit_form(
                page,
                attrz_list
            )
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
        ppolicy_choices = [(ppolicy.get_attributes()['cn'][0],
                            ppolicy.get_attributes()['cn'][0])
                           for ppolicy in get_all_ppolicies()
        ]
        ppolicy_choices.append(('', 'Aucune'))
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
                set_group_ppolicy(ldap_object_type.label,
                                  ldap_object_type.ppolicy)
            flash(u'{0} mis à jour'.format(ldap_object_type.description))
            return redirect(url_for('home'))
        form.label.data = ldap_object_type.label
        form.description.data = ldap_object_type.description
        form.ranges.data = ldap_object_type.ranges
        form.apply_to.data = ldap_object_type.apply_to
        form.ppolicy.data = ldap_object_type.ppolicy
        form.ppolicy.choices = ppolicy_choices
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
    form = AddObjectTypeForm(request.form)
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
    return redirect(url_for('show_ldap_object_types'))



@app.route('/show_ldap_object_types/')
@login_required
def show_ldap_object_types():
    ldap_object_types = LDAPObjectType.query.all()
    return render_template('show_ldap_object_types.html',
                           ldap_object_types=ldap_object_types)


@app.route('/show_ppolicies/')
@login_required
def show_ppolicies():
    ppolicies = [ppolicy.get_attributes()['cn'][0]
                 for ppolicy in get_all_ppolicies()]
    return render_template('show_ppolicies.html',
                           ppolicies=ppolicies)

@app.route('/add_ppolicy/', methods=('GET', 'POST'))
@login_required
def add_ppolicy():
    form = AddPolicyForm(request.form)
    if request.method == 'POST' and form.validate():
        cn = form.cn.data.encode('utf-8')
        dn = "cn={0},ou=policies,ou=system,{1}".format(
            cn,
            app.config['LDAP_SEARCH_BASE'])
        add_record=[('cn',[cn]),
                    ('pwdAttribute', ['userPassword']),
                    ('objectClass', ['device', 'pwdPolicy'])]
        if ldap.add(dn, add_record):
            flash(u'PPolicy {0} ajoutée'.format(cn))
        return redirect(url_for('edit_ppolicy',
                                ppolicy_label= cn))
    return render_template('add_ppolicy.html',
                           form=form)


@app.route('/edit_ppolicy/<ppolicy_label>',
           methods=('GET', 'POST'))
@login_required
def edit_ppolicy(ppolicy_label):
    page = Page.query.filter_by(label = 'ppolicy').first()
    form = generate_edit_ppolicy_form_class(page)(request.form)
    fieldz = Field.query.filter_by(page_id = page.id,edit = True).all()
    fieldz_labelz = [field.label for field in fieldz]

    if request.method == 'POST' and form.validate() :
        update_ldap_object_from_edit_ppolicy_form(form,
                                                  fieldz_labelz,
                                                  ppolicy_label)
        return redirect(url_for('home'))
    else:
        set_edit_ppolicy_form_values(form, fieldz_labelz, ppolicy_label)

    return render_template('edit_ppolicy.html',
                           form=form,
                           page=page,
                           ppolicy_label=ppolicy_label,
                           fieldz=fieldz)
@app.route('/show_filesystems')
@login_required
def show_filesystems():
    filesystems = Filesystem.query.all()
    return render_template('show_filesystems.html',
                           filesystems=filesystems)

@app.route('/add_filesystem',methods=('GET', 'POST'))
@login_required
def add_filesystem():
    add_form = FilesystemForm(request.form)
    if request.method == 'POST' and add_form.validate():
        filesystem = Filesystem(add_form.label.data,
                                add_form.description.data)
        db.session.add(filesystem)
        db.session.commit()
        flash(u'{0} créé'.format(add_form.label.data))
        return redirect(url_for('show_filesystems'))
    return render_template('add_filesystem.html',
                           form = add_form)


@app.route('/edit_filesystem/<fs_label>',methods=('GET', 'POST'))
@login_required
def edit_filesystem(fs_label):
    filesystem = Filesystem.query.filter_by(label = fs_label).first()
    add_form = FilesystemForm(request.form)
    if request.method == 'POST' and add_form.validate():
        filesystem.label = add_form.label.data,
        filesystem.description = add_form.description.data
        db.session.add(filesystem)
        db.session.commit()
        flash(u'{0} mis à jour'.format(add_form.label.data))
        return redirect(url_for('show_filesystems'))
    add_form.description.data = filesystem.description
    add_form.label.data = filesystem.label
    return render_template('edit_filesystem.html',
                           form = add_form,
                           filesystem = filesystem)

@app.route('/delete_filesystem/<fs_label>')
@login_required
def delete_filesystem(fs_label):
    Filesystem.query.filter_by(label = fs_label).delete()
    db.session.commit()
    flash(u'Système de fichier {0} supprimé'.format(fs_label))
    return redirect(url_for('show_filesystems'))


@app.route('/show_shells')
@login_required
def show_shells():
    shells = Shell.query.all()
    return render_template('show_shells.html',
                           shells=shells)

@app.route('/add_shell',methods=('GET', 'POST'))
@login_required
def add_shell():
    add_form = ShellForm(request.form)
    if request.method == 'POST' and add_form.validate():
        shell = Shell(add_form.label.data,
                      add_form.path.data)
        db.session.add(shell)
        db.session.commit()
        flash(u'{0} créé'.format(add_form.label.data))
        return redirect(url_for('show_shells'))
    return render_template('add_shell.html',
                           form = add_form)


@app.route('/edit_shell/<shell_label>',methods=('GET', 'POST'))
@login_required
def edit_shell(shell_label):
    shell = Shell.query.filter_by(label = shell_label).first()
    add_form = ShellForm(request.form)
    if request.method == 'POST' and add_form.validate():
        shell.label = add_form.label.data,
        shell.path = add_form.path.data
        db.session.add(shell)
        db.session.commit()
        flash(u'{0} mis à jour'.format(add_form.label.data))
        return redirect(url_for('show_shells'))
    add_form.path.data = shell.path
    add_form.label.data = shell.label
    return render_template('edit_shell.html',
                           form = add_form,
                           shell = shell)

@app.route('/delete_shell/<shell_label>')
@login_required
def delete_shell(shell_label):
    Shell.query.filter_by(label = fs_label).delete()
    db.session.commit()
    flash(u'Shell {0} supprimé'.format(shell_label))
    return redirect(url_for('show_shells'))

@app.route('/show_bind_history/<uid>')
@login_required
def show_bind_history(uid):
    user = User.query.filter_by(uid=uid).first()
    return render_template('show_bind_history.html',
                           user = user)

@app.route('/show_history/<uid>')
@login_required
def show_history(uid):
    raw_logz = get_uid_logz(uid)
    print(raw_logz[0])
    logz = []
    for raw_log in raw_logz:
        log_attrz = raw_log.get_attributes()
        if 'reqMod' in log_attrz:
            raw_new_valuez = log_attrz['reqMod']
        if 'reqOld' in log_attrz:
            raw_old_valuez = log_attrz['reqOld']
        new_valuez_dict = get_dict_from_raw_log_valuez(raw_new_valuez)
        old_valuez_dict = get_dict_from_raw_log_valuez(raw_old_valuez)
        log = {'modified_by': log_attrz['reqAuthzID'][0],
               'modified_date': generalized_time_sec_to_datetime(
                   log_attrz['reqStart'][0] ),
               'new_valuez': new_valuez_dict,
               'old_valuez': old_valuez_dict}
        logz.append(log)
    ordered_logz = sorted(logz, key=lambda k: k['modified_date'], reverse=True)

    return render_template('show_history.html',
                               uid = uid,
                               logz=ordered_logz)

    ### Helperz

def get_dict_from_raw_log_valuez(raw_valuez):
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
                attr_value = generalized_time_to_datetime(
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

def get_default_quota_form_value(storage, default_storage, form, field_name):
    default_inode_unit = form.cinesQuotaInodeHardTemp.unit.default
    default_size_unit = form.cinesQuotaSizeHardTemp.unit.default

    if field_name in storage:
        stored_value = storage[field_name][0]
        default = False
    else:
        stored_value = default_storage[
            app.config['QUOTA_FIELDZ'][field_name]['default']
        ][0]
        default = True

    display_value = int(stored_value) / (
        default_size_unit if app.config[
            'QUOTA_FIELDZ'][field_name]['type'] == 'size'
        else default_inode_unit
    )

    return (display_value, default)

def set_quota_form_values(form, storage):
    default_storage_cn = storage['cn'][0].split('.')[0]
    default_storage = get_default_storage(default_storage_cn).get_attributes()
    date_now = datetime.now()

    default_fieldz = []
    cinesQuotaSizeHard = get_default_quota_form_value(
        storage,
        default_storage,
        form,
        'cinesQuotaSizeHard')
    cinesQuotaSizeSoft = get_default_quota_form_value(
        storage,
        default_storage,
        form,
        'cinesQuotaSizeSoft')
    cinesQuotaInodeHard = get_default_quota_form_value(
        storage,
        default_storage,
        form,
        'cinesQuotaInodeHard')
    cinesQuotaInodeSoft = get_default_quota_form_value(
        storage,
        default_storage,
        form,
        'cinesQuotaInodeSoft')
    cinesQuotaSizeHardTemp = get_default_quota_form_value(
        storage,
        default_storage,
        form,
        'cinesQuotaSizeHardTemp')
    cinesQuotaSizeSoftTemp = get_default_quota_form_value(
        storage,
        default_storage,
        form,
        'cinesQuotaSizeSoftTemp')
    cinesQuotaInodeHardTemp = get_default_quota_form_value(
        storage,
        default_storage,
        form,
        'cinesQuotaInodeHardTemp')
    cinesQuotaInodeSoftTemp = get_default_quota_form_value(
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


def get_c4_groupz_choices():
    existing_groupz = [
        group.get_attributes()['cn'][0] for group in get_all_groups()]
    c4_projectz = C4Projet.query.all()
    c4_groupz_choices = [(project.code_projet, project.code_projet)
                         for project in c4_projectz
                         if project.code_projet not in existing_groupz]
    return c4_groupz_choices

@app.before_first_request
def init_populate_grouplist_redis():
    populate_grouplist_redis()

def populate_grouplist_redis():
    grouplist = get_posix_groupz_choices()
    for (uid, group) in grouplist:
        r.hset('grouplist', uid, group)

@app.before_first_request
def init_populate_people_group_redis():
    populate_people_group_redis()


def populate_people_group_redis():
    for branch in app.config['BRANCHZ']:
        people_group = branch['account']
        print(people_group)
        r.delete('groupz:{0}'.format(people_group))
        memberz = get_people_group_memberz(people_group)
        for member in memberz:
            r.sadd("groupz:{0}".format(people_group), member)



@app.before_first_request
def init_populate_work_group_redis():
    populate_work_group_redis()

@app.before_first_request
def init_populate_last_used_idz():
    populate_last_used_idz()

def populate_last_used_idz():
    ignore_ot_list = ['reserved', 'grLight', 'grPrace']
    ldap_otz = LDAPObjectType.query.all()
    for ldap_ot in ldap_otz:
        if ldap_ot.label not in ignore_ot_list:
            last_used_id = get_last_used_id(ldap_ot)
            id_range = get_range_list_from_string(ldap_ot.ranges)
            if int(last_used_id) not in id_range:
                last_used_id = id_range[0]
            ldap_ot.last_used_id = last_used_id
            db.session.add(ldap_ot)
    db.session.commit()

def populate_work_group_redis():
    for group in get_work_groupz():
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


def create_ldap_object_from_add_group_form(form):
    ot = LDAPObjectType.query.filter_by(label = form.group_type.data).first()
    cn = form.cn.data.encode('utf-8')
    description = form.description.data.encode('utf-8')
    filesystem = form.filesystem.data.encode('utf-8')
    id_number = str(get_next_id_from_ldap_ot(ot))
    object_classes = [oc_ot.ldapobjectclass.label.encode('utf-8') for oc_ot in
                      LDAPObjectTypeObjectClass.query.filter_by(
                          ldapobjecttype_id = ot.id).all()]

    full_dn = "cn={0},ou={1},ou=groupePosix,{2}".format(cn,
                                         ot.label,
                                         app.config['LDAP_SEARCH_BASE'])
    add_record = [('cn', [cn]),
                  ('description', [description]),
                  ('gidNumber', [id_number]),
                  ('fileSystem', [filesystem]),
                  ('objectClass', object_classes)]

    # print(add_record)
    if ldap.add(full_dn, add_record):
        flash(u'Groupe créé')


def create_ldap_object_from_add_user_form(form, fieldz_labelz, uid, page):
    ldap_ot = LDAPObjectType.query.filter_by(
        label=page.label
    ).first()
    ldap_ot_ocz = LDAPObjectTypeObjectClass.query.filter_by(
        ldapobjecttype_id = ldap_ot.id
    ).all()
    ot_oc_list = [oc.ldapobjectclass.label.encode('utf-8')
                  for oc in ldap_ot_ocz]

    form_attributez = []
    for field_label in fieldz_labelz:
        form_field_values = [entry.data.encode('utf-8')
                             for entry in getattr(form, field_label).entries]
        print('form_field_values : {0}'.format(form_field_values))
        if field_label != 'cinesUserToPurge':
            form_attributez.append((field_label, form_field_values))

    uid_number = get_next_id_from_ldap_ot(ldap_ot)
    add_record = [('uid', [uid.encode('utf-8')]),
                  ('uidNumber', [str(uid_number).encode('utf-8')]),
                  ('objectClass', ot_oc_list)]

    add_record.extend(form_attributez)
    add_record.append(
        ('homeDirectory', "/home/{0}".format(uid).encode('utf-8')))

    if 'cinesusr' in ot_oc_list:
        add_record.append(
            ('cinesSoumission', [get_initial_submission()])
        )

    if 'sambaSamAccount' in ot_oc_list:
        add_record.append(
            ('sambaSID', "{0}-{1}".format(get_sambasid_prefix(),
                                                 uid_number))
        )

    if ldap_ot.ppolicy != '':
        add_record.append(
            ('pwdPolicySubentry',
             'cn={0},ou=policies,ou=system,{1}'.format(
                 ldap_ot.ppolicy,
                 app.config['LDAP_SEARCH_BASE'])
            )
        )

    parent_dn = get_people_dn_from_ou(ldap_ot.label)
    full_dn = "uid={0};{1}".format(uid,parent_dn)
    if ldap.add(full_dn, add_record):
        ldap_ot.last_used_id= uid_number
        db.session.add(ldap_ot)
        db.session.commit()
        r.sadd("groupz:{0}".format(page.label), uid)
    else:
        flash(u'L\'utilisateur n\'a pas été créé')

    return True


def get_next_id_from_ldap_ot(ldap_ot):
    id_range = get_range_list_from_string(ldap_ot.ranges)
    next_index = id_range.index(ldap_ot.last_used_id)+1
    while 1:
        test_id = id_range[next_index]
        ldap_filter = '(uidNumber={0})'.format(test_id)
        raw_result = ldap.search(ldap_filter=ldap_filter,
                                 attributes = ['uidNumber'])
        if not raw_result:
            return test_id
        next_index += 1

def get_range_list_from_string(rangez_string):
    rangez = rangez_string.split(';')
    rangez_lst = []
    for range_string in rangez:
        if range_string != '':
            range_split = range_string.split('-')
            rangez_lst.extend(range(
                int(range_split[0]),
                int(range_split[1])+1))
    return sorted(set(rangez_lst))

def get_last_used_id(ldap_ot):
    attributes=['gidNumber'] if ldap_ot.apply_to == 'group' else ['uidNumber']
    if ldap_ot.apply_to == 'group':
        ldap_filter = '(objectClass=posixGroup)'
    else:
        ldap_filter = '(objectClass=posixAccount)'
    base_dn='ou={0},ou={1},{2}'.format(
        ldap_ot.label,
        'groupePosix' if ldap_ot.apply_to == 'group' else 'people',
        app.config['LDAP_SEARCH_BASE']
    )
    # print(base_dn)
    raw_resultz = ldap.search(base_dn,ldap_filter,attributes)
    if raw_resultz:
        resultz = ldaphelper.get_search_results(
        raw_resultz
        )
    else:
        return 0
    # print('{0} results : {1}'.format(
    #     ldap_ot.label,
    #     resultz))

    max_id= 0
    for result in resultz:
        result_id = int(result.get_attributes()[attributes[0]][0])
        if result_id > max_id:
            max_id = result_id
    return str(max_id)

def get_filesystem_choices():
    filesystems = Filesystem.query.all()
    fs_choices = [ (fs.label, fs.description) for fs in filesystems]
    return fs_choices

def update_ldap_object_from_edit_ppolicy_form(form, attributes, cn):
    ppolicy_attrz = get_ppolicy(cn).get_attributes()
    pre_modlist = []
    for attr in attributes:
        field_value = getattr(form, attr).data.encode('utf-8')
        print('form_field_value : {0}'.format(field_value))
        if attr not in ppolicy_attrz or ppolicy_attrz[attr][0] != field_value:
            # if attr == 'pwdMustChange':
            #     pre_modlist.append((attr, [True if field_value else False]))
            # else:
            pre_modlist.append((attr, [field_value]))
    print(pre_modlist)
    ldap.update_cn_attribute(cn, pre_modlist)

def update_ldap_object_from_edit_user_form(form, attributes, uid):
    uid_attributez = ldaphelper.get_search_results(
        get_uid_detailz(uid)
    )[0].get_attributes()
    pre_modlist = []
    for attr in attributes:
        if attr == 'cinesUserToPurge':
            form_values = [entry.data
                           for entry in getattr(form, attr).entries]
        else:
            form_values = [entry.data.encode('utf-8')
                           for entry in getattr(form, attr).entries]
        # print('form_values : {0}'.format(form_values))
        if attr not in uid_attributez or uid_attributez[attr] != form_values:
            if form_values == [''] or (attr == 'cinesUserToPurge'
                                       and True not in form_values):
                form_values = None
            if (
                    attr == 'cinesUserToPurge'
                    and form_values
                    and True in form_values
            ):
                form_values = ['1']
            pre_modlist.append((attr, form_values))
    # print(pre_modlist)
    ldap.update_uid_attribute(uid, pre_modlist)

def upsert_otrs_user(uid):
    user_attrz = ldaphelper.get_search_results(
        get_uid_detailz(uid)
    )[0].get_attributes()
    otrs_user = OTRSCustomerUser.query.filter_by(login = uid).first()
    if not otrs_user:
        otrs_user = OTRSCustomerUser(login = uid)

    if 'telephoneNumber' in user_attrz:
        telephone_number = ';'.join(
            [phone for phone in user_attrz['telephoneNumber']])
    else:
        telephone_number = ''
    user_type = LDAPObjectType.query.filter_by(
        label = get_group_from_member_uid(uid)
    ).first().description
    first_gr_name = get_posix_group_cn_by_gid(user_attrz['gidNumber'][0])
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

def delete_otrs_user(uid):
    date = datetime.now().strftime("%Y%m%d%H%M")
    disabled_login = "".join(['ZDEL', date, "_", uid])
    # print(disabled_login)
    otrs_user = OTRSCustomerUser.query.filter_by(login = uid).first()
    otrs_user.login = disabled_login
    otrs_user.valid_id = 2
    db.session.add(otrs_user)

    otrs_ticketz = OTRSTicket.query.filter_by(customer_user_id = uid).all()
    for ticket in otrs_ticketz:
        ticket.customer_user_id = disabled_login
        db.session.add(ticket)

    if is_cines_group(uid):
        OTRSUser.query.filter_by(login=uid).update(
            {
                'valid_id': 2,
                'login': disabled_login,
                'change_time': datetime.now()
            }, synchronize_session=False
        )
    db.session.commit()

def update_ldap_object_from_edit_group_form(form, page, group_cn):
    ldap_filter='(&(cn={0})(objectClass=posixGroup))'.format(group_cn)
    attributes=['*','+']
    detailz = ldap.search(ldap_filter=ldap_filter,attributes=attributes)
    group_attributez = ldaphelper.get_search_results(
        detailz
    )[0].get_attributes()
    pagefieldz = Field.query.filter_by(page_id = page.id,
                                       edit = True).all()
    pre_modlist = []
    for field in pagefieldz:
        form_field_values = [entry.data.encode('utf-8')
                             for entry in getattr(form, field.label).entries]
        print('form_field_values : {0}'.format(form_field_values))
        if group_attributez[field.label] != form_field_values:
            pre_modlist.append((field.label, form_field_values))
    print(pre_modlist)
    ldap.update_cn_attribute(group_cn, pre_modlist)

def generate_kustom_batch_edit_form(page, attributez):
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
        append_field_to_form(field,
                             EditGroupForm)

    form = EditGroupForm(request.form)
    return form

def generate_edit_group_form(page):
    page_fieldz = Field.query.filter_by(page_id = page.id).all()

    class EditGroupForm(EditGroupBaseForm):
        pass

    for field in page_fieldz:
        # print('field label {0}'.format(field.label))
        append_fieldlist_to_form(field,
                                 EditGroupForm)
    return EditGroupForm(request.form)

def generate_select_work_group_form(uid):
    actual_work_groupz = get_work_groupz_from_member_uid(uid)
    available_work_groupz = get_work_groupz()
    selected_choices = [(group, group) for group in actual_work_groupz]
    available_choices = [(group, group) for group in available_work_groupz
                         if group not in actual_work_groupz]
    form = SelectGroupzForm(request.form)
    form.available_groupz.choices = available_choices
    form.selected_groupz.choices = selected_choices

    return form

def generate_edit_user_form_class(page):
    page_fieldz = Field.query.filter_by(page_id = page.id,
                                        edit = True).all()
    class EditForm(Form):
        wrk_groupz = FormField(SelectGroupzForm, label=u"Groupes de travail")

    for field in page_fieldz:
        append_fieldlist_to_form(field, EditForm)

    return EditForm

def generate_edit_ppolicy_form_class(page):
    page_fieldz = Field.query.filter_by(page_id = page.id,
                                        edit = True).all()
    class EditForm(Form):
        pass

    for field in page_fieldz:
        append_field_to_form(field, EditForm)

    return EditForm


def set_edit_group_form_values(form, fieldz, cn=None):
    if cn:
        ldap_filter='(cn={0})'.format(cn)
        attributes=['*','+']
        detailz = ldap.search(ldap_filter=ldap_filter,attributes=attributes)

        group_attributez = ldaphelper.get_search_results(
            detailz
        )[0].get_attributes()
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
                    convert_to_display_mode(field_value,
                                            field.fieldtype.type))
        else:
            form_field.append_entry()


def set_edit_user_form_values(form, fieldz, uid=None):
    actual_work_groupz = get_work_groupz_from_member_uid(uid)
    available_work_groupz = get_work_groupz()
    selected_choices = [(group, group) for group in actual_work_groupz]
    available_choices = [(group, group) for group in available_work_groupz
                         if group not in actual_work_groupz]

    form.wrk_groupz.available_groupz.choices = available_choices
    form.wrk_groupz.selected_groupz.choices = selected_choices

    if uid:
        uid_attributez = ldaphelper.get_search_results(
            get_uid_detailz(uid)
        )[0].get_attributes()
    else:
        uid_attributez = {}

    for field in fieldz:
        form_field = getattr(form, field.label)
        while(len(form_field.entries)>0):
            form_field.pop_entry()
        if field.label in uid_attributez and len(uid_attributez[field.label]):
            for field_value in uid_attributez[field.label]:
                print(field_value)
                form_field.append_entry(
                    convert_to_display_mode(field_value,
                                            field.fieldtype.type))
        else:
            form_field.append_entry()



def set_edit_ppolicy_form_values(form, fieldz_namez, ppolicy_cn=None):
    if ppolicy_cn:
        ppolicy_attz = get_ppolicy(ppolicy_cn).get_attributes()
    else:
        ppolicy_attz = {}

    for field_name in fieldz_namez:
        field = getattr(form, field_name)
        if field_name in ppolicy_attz and len(ppolicy_attz[field_name]):
            for field_value in ppolicy_attz[field_name]:
                field.data = field_value.decode('utf-8')

def append_field_to_form(field, form):
    date_formatz = ['Datetime', 'DaysNumber', 'GeneralizedTime']
    if field.fieldtype.type == 'Text':
        setattr(form,
                field.label,
                TextField(field.description))
    elif field.fieldtype.type in date_formatz:
        setattr(form,
                field.label,
                DateField(field.description))
    elif  field.fieldtype.type == 'GIDNumber':
        setattr(form,
                field.label,
                SelectField(field.description,
                            choices=get_posix_groupz_choices()))
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

def append_fieldlist_to_form(field, form):
    date_formatz = ['Datetime', 'DaysNumber', 'GeneralizedTime']
    if field.fieldtype.type == 'Text':
        setattr(form,
                field.label,
                FieldList(TextField(field.description)))
    elif field.fieldtype.type in date_formatz:
        setattr(form,
                field.label,
                FieldList(DateField(field.description)))
    elif  field.fieldtype.type == 'GIDNumber':
        setattr(form,
                field.label,
                FieldList(SelectField(field.description,
                                      choices=get_posix_groupz_choices())))
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


def generate_edit_page_admin_form(page):

    # selection des attributs hérités des object classes
    select_oc_choices = get_page_oc_choices(page)

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
    # print('memberz_dn_filtered {0}'.format(memberz_dn_filtered))
    # print(memberz_dn)
    if memberz_dn_filtered:
        pre_modlist = [('uniqueMember', memberz_dn_filtered)]
        group_dn = get_wrk_group_dn_from_cn(group)
        ldap.add_dn_attribute(group_dn, pre_modlist)
    #     flash(u'Utilisateur(s) ajoutés au groupe')
    # else:
    #     flash(u'Utilisateur(s) déjà membre(s) du groupe')

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
        group_dn = get_wrk_group_dn_from_cn(group)
        ldap.remove_dn_attribute(group_dn, pre_modlist)
    #     flash(u'Utilisateur(s) supprimé(s) du groupe')
    # else:
    #     flash(u'Utilisateur(s) déjà supprimé(s) du groupe')


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

def get_uid_logz(uid):
    dn = ldap.get_full_dn_from_uid(uid)
    ldap_filter="(&(objectClass=auditModify)(reqDN={0}))".format(dn)
    attributes=['*']
    base_dn=app.config['LDAP_LOG_BASE']
    logz = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    return logz

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
    for branch in app.config['BRANCHZ']:
        people_group = branch['account']
        if uid in r.smembers("groupz:{0}".format(people_group)):
            return people_group
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
    # print(ldap_filter)
    # print(base_dn)
    records = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    # print(records)
    group_attrz= records[0].get_attributes()
    if 'memberUid' in group_attrz:
        memberz = group_attrz['memberUid']
    else:
        memberz = []
    return memberz


def get_posix_groupz_from_member_uid(uid):
    ldap_filter='(&(objectClass=posixGroup)(memberUid={0}))'.format(uid)
    attributes=['cn', 'entryDN']
    base_dn='ou=groupePosix,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    groupz_obj = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    groupz = []
    for group in groupz_obj:
        group_attrz = group.get_attributes()
        cn = group_attrz['cn'][0]
        dn = group_attrz['entryDN'][0]
        branch = get_branch_from_posix_group_dn(dn)
        groupz.append(
            (cn, branch))
    return groupz

def  get_branch_from_posix_group_dn(dn):
    search_pattern = "cn=(.+?),ou=(.+?),"
    m = re.search(search_pattern, dn)
    if m:
        return m.group(2)
    else:
        return ''

def get_work_groupz_from_member_uid(uid):
    dn = ldap.get_full_dn_from_uid(uid)
    ldap_filter='(&(objectClass=cinesGrWork)(uniqueMember={0}))'.format(dn)
    attributes=['cn']
    base_dn='ou=grTravail,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    groupz_obj = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    print('groupz_obj {0}'.format(groupz_obj))
    groupz = []
    for group in groupz_obj:
        groupz.append(group.get_attributes()['cn'][0])
    return groupz

def get_wrk_group_dn_from_cn(cn):
    ldap_filter='(&(objectClass=cinesGrWork)(cn={0}))'.format(cn)
    attributes = ['entryDN']
    base_dn='ou=grTravail,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    group_obj = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )[0]
    dn = group_obj.get_attributes()['entryDN'][0]
    return dn


def get_people_dn_from_ou(ou):
    ldap_filter='(ou={0})'.format(ou)
    attributes=['entryDN']
    base_dn='ou=people,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    records = ldaphelper.get_search_results(
        ldap.search(base_dn,ldap_filter,attributes)
    )
    full_dn = records[0].get_attributes()['entryDN'][0]
    return full_dn

def get_people_group_memberz(group):
    """
    List memberz of a group inherited from people ou
    """
    ldap_filter='(objectclass=inetOrgPerson)'
    attributes=['uid']
    base_dn='ou={0},ou=people,{1}'.format(group,app.config['LDAP_SEARCH_BASE'])

    raw_result = ldap.admin_search(base_dn,ldap_filter,attributes)
    if raw_result:
        records = ldaphelper.get_search_results(
            raw_result
        )
    else:
        return None

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

def get_posix_groupz(branch=None):
    # print(branch)
    ldap_filter = "(objectClass=posixGroup)"
    base_dn = 'ou=groupePosix,{0}'.format(app.config['LDAP_SEARCH_BASE'])

    if branch:
        base_dn = ''.join(['ou={0},'.format(branch), base_dn])
    # print(base_dn)
    groupz = ldaphelper.get_search_results(
        ldap.admin_search(base_dn=base_dn,
                          ldap_filter=ldap_filter,
                          attributes=['cn', 'gidNumber']))
    return groupz

def get_work_groupz():
    ldap_filter = "(objectClass=cinesGrWork)"
    base_dn = 'ou=grTravail,{0}'.format(app.config['LDAP_SEARCH_BASE'])
    groupz = ldaphelper.get_search_results(
        ldap.admin_search(base_dn=base_dn,
                          ldap_filter=ldap_filter,
                          attributes=['cn']))
    return [group.get_attributes()['cn'][0] for group in groupz]

def get_posix_groupz_choices():
    ldap_groupz = get_posix_groupz()
    ldap_groupz_list = []
    for group in ldap_groupz:
        group_attrz = group.get_attributes()
        ldap_groupz_list.append((group_attrz['gidNumber'][0],
                                 group_attrz['cn'][0]))
    return ldap_groupz_list

def get_shellz_choices():
    shellz = Shell.query.all()
    shellz_choices = [ (shell.path, shell.label) for shell in shellz ]
    return shellz_choices

def get_list_from_submission_attr(sub_attr):
    sub_list = []
    for group in sub_attr.split(';'):
        split_group = group.split('=')
        if split_group != ['']:
            sub_list.append((split_group[0],split_group[1]))
    return sub_list

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

def get_initial_submission():
    submission_groupz_list = get_submission_groupz_list()
    initial_submission = ''.join([
        '{0}=0;'.format(submission_group)
        for submission_group in submission_groupz_list
    ])
    return initial_submission

def get_user_pwd_policy(uid):
    ldap_filter = "(&(objectClass=posixAccount)(uid={0}))".format(uid)
    user = ldaphelper.get_search_results(
        ldap.admin_search(ldap_filter=ldap_filter,
                          attributes=['pwdPolicySubentry'])
    )[0].get_attributes()
    if 'pwdPolicySubentry' in user:
        subentry_filter = '(entryDN={0})'.format(user['pwdPolicySubentry'][0])
    else:
        subentry_filter = '(&(objectClass=pwdPolicy)(cn=passwordDefault))'
    base_dn = 'ou=policies,ou=system,{0}'.format(app.config['LDAP_SEARCH_BASE'])
    pwd_policy = ldaphelper.get_search_results(
        ldap.admin_search(ldap_filter=subentry_filter,
                         attributes=['*'])
    )[0].get_attributes()
    return pwd_policy

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
    base_dn = "ou=people,{0}".format(app.config['LDAP_SEARCH_BASE'])
    ldap_filter='(objectclass=inetOrgPerson)'
    attributes=['*','+']
    userz = ldaphelper.get_search_results(
        ldap.search(ldap_filter=ldap_filter,
                    attributes=attributes,
                    base_dn=base_dn)
    )
    return userz

def get_all_groups():
    base_dn = "{0}".format(app.config['LDAP_SEARCH_BASE'])
    ldap_filter='(objectclass=posixGroup)'
    attributes=['*','+']
    groupz = ldaphelper.get_search_results(
        ldap.search(ldap_filter=ldap_filter,
                    attributes=attributes,
                    base_dn=base_dn)
    )
    return groupz

def get_all_ppolicies():
    base_dn = "ou=policies,ou=system,{0}".format(app.config['LDAP_SEARCH_BASE'])
    ldap_filter='(objectclass=pwdPolicy)'
    attributes=['*','+']
    userz = ldaphelper.get_search_results(
        ldap.search(ldap_filter=ldap_filter,
                    attributes=attributes,
                    base_dn=base_dn)
    )
    return userz

def get_ppolicy(ppolicy_label):
    base_dn = "ou=policies,ou=system,{0}".format(app.config['LDAP_SEARCH_BASE'])
    ldap_filter='(&(objectclass=pwdPolicy)(cn={0}))'.format(ppolicy_label)
    attributes=['*','+']
    ppolicy = ldaphelper.get_search_results(
        ldap.search(ldap_filter=ldap_filter,
                    attributes=attributes,
                    base_dn=base_dn)
    )[0]
    return ppolicy

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

def set_group_ppolicy(group, ppolicy):
    memberz = get_people_group_memberz(group)
    ppolicy_value = 'cn={0},ou=policies,ou=system,{1}'.format(
        ppolicy,
        app.config['LDAP_SEARCH_BASE']) if ppolicy != '' else None
    pre_modlist= [('pwdPolicySubentry',
                   ppolicy_value)]

    for member in memberz:
        ldap.update_uid_attribute(member, pre_modlist)

def update_default_quota(storage_cn, form):
    cinesQuotaSizeHard = get_quota_value_from_form(
        form,
        'cinesQuotaSizeHard')
    cinesQuotaSizeSoft = get_quota_value_from_form(
        form,
        'cinesQuotaSizeSoft')
    cinesQuotaInodeHard = get_quota_value_from_form(
        form,
        'cinesQuotaInodeHard')
    cinesQuotaInodeSoft = get_quota_value_from_form(
        form,
        'cinesQuotaInodeSoft')
    pre_modlist = [('cinesQuotaSizeHard', cinesQuotaSizeHard),
                   ('cinesQuotaSizeSoft', cinesQuotaSizeSoft),
                   ('cinesQuotaInodeHard', cinesQuotaInodeHard),
                   ('cinesQuotaInodeSoft', cinesQuotaInodeSoft)]
    ldap.update_cn_attribute(storage_cn, pre_modlist)

def get_quota_value_from_form(form, quota):
    field = getattr(form, quota)
    value = str(
        int(
            field.value.data
        ) * int(
            field.unit.data)
    ).encode('utf-8')
    return value

def update_quota(storage, form):
    default_storage_cn = storage['cn'][0].split('.')[0]
    default_storage = get_default_storage(default_storage_cn).get_attributes()

    pre_modlist = []

    for field_name in app.config['QUOTA_FIELDZ']:
        form_value = get_quota_value_from_form(
            form,
            field_name)
        default_field = app.config['QUOTA_FIELDZ'][field_name]['default']
        if (
                form_value != default_storage[default_field][0]
                and (field_name not in storage
                     or  form_value != storage[field_name][0])
        ):
            print('form_value : {0} field_name : {1}  default_storage[default_field] : {2}'.format(form_value, field_name,  default_storage[default_field]))
            pre_modlist.append((field_name, form_value))


    cinesQuotaSizeTempExpire = datetime_to_timestamp(
        form.cinesQuotaSizeTempExpire.data
    ).encode('utf-8')
    if cinesQuotaSizeTempExpire != storage['cinesQuotaSizeTempExpire']:
        pre_modlist.append(('cinesQuotaSizeTempExpire',
                            cinesQuotaSizeTempExpire))

    cinesQuotaInodeTempExpire = datetime_to_timestamp(
        form.cinesQuotaInodeTempExpire.data
    ).encode('utf-8')

    if cinesQuotaInodeTempExpire != storage['cinesQuotaInodeTempExpire']:
        pre_modlist.append(('cinesQuotaInodeTempExpire',
                            cinesQuotaInodeTempExpire))
    ldap.update_cn_attribute(storage['cn'][0], pre_modlist)

def update_group_memberz_cines_c4(group, comite):
    memberz_uid = get_posix_group_memberz(group)
    if len(memberz_uid)>1:
        ldap_filter = '(&(objectClass=posixAccount)(|{0}))'.format(
            ''.join(['(uid={0})'.format(uid) for uid in memberz_uid]))
    elif len(memberz_uid)==1:
        ldap_filter = '(&(objectClass=posixAccount)(uid={0}))'.format(
            memberz_uid[0])
    else:
        return
    memberz = ldaphelper.get_search_results(ldap.search(
        ldap_filter=ldap_filter,
        attributes=['cinesC4', 'dn', 'uid', 'gidNumber']
    ))
    for member in memberz:
        member_attrz = member.get_attributes()
        if (
                is_ccc_group(member_attrz['uid'][0])
                and is_principal_group(member_attrz, group)
                and (
                    'cinesC4' not in member_attrz
                     or member_attrz['cinesC4'][0] != comite
                )
        ):
            print(u"{0} mis à jour à : {1}".format(member_attrz['uid'][0],
                                                    comite))
            ldap.update_uid_attribute(
                member_attrz['uid'][0],
                [('cinesC4', comite.encode('utf-8'))])


def is_ccc_group(member):
    return 'ccc' == get_group_from_member_uid(member['uid'][0])

def is_cines_group(uid):
    return 'cines' == get_group_from_member_uid(uid)

def is_principal_group(member, group):
    return get_posix_group_cn_by_gid(member['gidNumber'][0]) == group


def generalized_time_to_datetime(generalized_time):
    created_datetime = datetime.strptime(
        generalized_time, "%Y%m%d%H%M%SZ"
    )
    created_datetime = utc.localize(created_datetime)
    created_datetime = created_datetime.astimezone(
        timezone(app.config['TIMEZONE'])
    )
    return created_datetime



def generalized_time_sec_to_datetime(generalized_time):
    created_datetime = datetime.strptime(
        generalized_time, "%Y%m%d%H%M%S.%fZ"
    )
    created_datetime = utc.localize(created_datetime)
    created_datetime = created_datetime.astimezone(
        timezone(app.config['TIMEZONE'])
    )
    return created_datetime

def datetime_to_timestamp(date):
    # return (date_time  - datetime(1970, 1, 1)).total_seconds()
    return str(int(time.mktime(
        datetime.strptime(str(date), "%Y-%m-%d").timetuple()
    )))

def datetime_to_days_number(datetime):
    return int(datetime.strftime("%s"))/86400

def days_number_to_datetime(nb):
    return datetime.fromtimestamp(
        # 86400 == nombre de secondes par jour
        int(nb) * 86400
    )

def convert_to_display_mode(value, display_mode):
    # print(value)
    # print(display_mode)
    if display_mode in  ('Text', 'Filesystem', 'Shell') :
        # value = value.decode('utf-8')
        return value.decode('utf-8')
    elif display_mode == 'Datetime' :
        return value.strftime(
            app.config['DATE_FORMAT'])
    elif display_mode == 'Generalizedtime' :
        return generalized_time_to_datetime(value)# .strftime(
            # app.config['DATE_FORMAT'])
    elif display_mode == 'GIDNumber' :
        return get_posix_group_cn_by_gid(value)
    elif display_mode == 'DaysNumber' :
        return days_number_to_datetime(value)# .strftime(
            # app.config['DATE_FORMAT'])
    elif display_mode == 'Checkbox' :
        if value == True:
            return "Oui"
        else:
            return "Non"

app.jinja_env.globals.update(
    convert_to_display_mode = convert_to_display_mode
)


def set_validators_to_form_field(form, field, validators):
    form_field_kwargs = get_attr(
        get_attr(form, field),'kwargs')

    # print(get_attr(form, field))
    # if 'validators' in form_field_kwargs:
    #     form_field_kwargs['validators'].extend(validators)
    # else:
    form_field_kwargs['validators'] = validators

    # print(form_field_kwargs['validators'])
def get_gid_from_posix_group_cn(cn):
    for gid, group_cn in r.hgetall('grouplist').iteritems():
        if group_cn == cn:
            return gid

def get_posix_group_cn_by_gid(gid):
    return r.hget('grouplist', gid)

# def get_groupz_from_member_uid(uid):
#     groupz = []
#     full_dn = ldap.get_full_dn_from_uid(uid)
#     for group in app.config['PEOPLE_GROUPS']:
#         for member in r.smembers("groupz:{0}".format(group)):
#             if uid == member:
#                 print("group {0}".format(member))
#                 groupz.append(group)
#     for group in get_submission_groupz_list():
#         for member in r.smembers("wrk_groupz:{0}".format(group)):
#             if full_dn == member:
#                 print("wrk_group {0}".format(member))
#                 groupz.append(group)
#     return groupz

app.jinja_env.globals.update(
    get_posix_group_cn_by_gid=get_posix_group_cn_by_gid
)

def get_sambasid_prefix():
    base_dn = app.config['LDAP_SEARCH_BASE']
    ldap_filter='(sambaDomainName={0})'.format(app.config['SAMBA_DOMAIN_NAME'])
    attributes=['sambaSID']
    samba_domain_name = ldaphelper.get_search_results(
        ldap.search(ldap_filter=ldap_filter,
                    attributes=attributes,
                    base_dn=base_dn)
    )[0]
    sambasid_prefix = samba_domain_name.get_attributes()['sambaSID'][0]
    return sambasid_prefix

### Run !

if __name__ == '__main__':
    app.debug = app.config['DEBUG']
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    toolbar = DebugToolbarExtension(app)
    decoder = PythonLDAPDecoder(app.config['ENCODING'])
    app.run(host='0.0.0.0')
