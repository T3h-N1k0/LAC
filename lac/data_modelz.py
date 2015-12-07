from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta, date
from lac import db

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
    mandatory = db.Column(db.Boolean())
    restrict = db.Column(db.Boolean())
    display_mode = db.Column(db.String(50), unique=True)
    priority = db.Column(db.Integer)
    block = db.Column(db.String(1))
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
                 mandatory=False,
                 multivalue=False,
                 restrict=False,
                 priority=False,
                 block=False):
        self.label = label
        self.description = description
        self.display = display
        self.edit = edit
        self.restrict = restrict
        self.page = page
        self.ldapattribute = ldapattribute
        self.fieldtype = fieldtype
        self.mandatory = mandatory
        self.multivalue = multivalue
        self.priority = priority
        self.block = block

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
    uid = db.Column(db.String(200))
    uid_number = db.Column(db.Integer, unique=True)
    firstname = db.Column(db.String(200))
    lastname = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone_number = db.Column(db.String(20))
    deletion_timestamp = db.Column(db.Date())
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
                            db.ForeignKey(
                                'PROJET{0}.code_projet'.format(
                                    datetime.now().strftime('%Y'))))
    demande_uc_ibm = db.Column(db.Integer)
    demande_uc_occigen = db.Column(db.Integer)
    accorde_uc_ibm = db.Column(db.Integer)
    accorde_uc_occigen = db.Column(db.Integer)

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


class C4OCCIGEN(db.Model):
    __bind_key__ = 'gescpt'
    __tablename__ = 'OCCIGEN'
    grpunix = db.Column(db.String(255), primary_key=True)
    walltime = db.Column(db.Float())
    nbcoeurs = db.Column(db.Integer)


class C4IBM(db.Model):
    __bind_key__ = 'gescpt'
    __tablename__ = 'IBM{0}'.format(datetime.now().strftime('%Y'))
    grpunix = db.Column(db.String(255), primary_key=True)
    walltime = db.Column(db.Float())
    nbcoeurs = db.Column(db.Integer)


def get_attr_from_oc_id_list(oc_id_list):
    oc_attr_list = LDAPObjectClassAttribute.query.filter(
        LDAPObjectClassAttribute.ldapobjectclass_id.in_(oc_id_list)
    ).all()
    oc_attr_id_list = [oc_attr.ldapattribute_id for oc_attr in oc_attr_list]
    attr_list = LDAPAttribute.query.filter(
        LDAPAttribute.id.in_(oc_attr_id_list)
    ).all()
    return attr_list
