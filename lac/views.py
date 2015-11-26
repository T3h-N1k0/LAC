# coding: utf-8
from lac import app
from flask_ldap import LDAP, login_required, admin_login_required
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response
from flask.ext.sqlalchemy import SQLAlchemy
# from flask_debugtoolbar import DebugToolbarExtension
from werkzeug import secure_filename
from flask_bootstrap import Bootstrap
from sqlalchemy import Table, Column, Integer, ForeignKey, func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from wtforms import Form, BooleanField, TextField, SelectMultipleField, SelectField, PasswordField,validators, FormField, FieldList, DateField, TextAreaField
from ldap import SCOPE_BASE,schema
import binascii
import re
import os
import time
from lac.data_modelz import *
from lac.formz import *
from lac.cache import Cache
from lac.form_manager import FormManager
from lac.converter import Converter
from lac.engine import Engine
from lac.helperz import *
from jinja2 import evalcontextfilter, Markup, escape

### Routez
ldap = LDAP(app)
cache = Cache(app)
converter = Converter(app)
fm = FormManager(app)
lac = Engine(app)
r = cache.r

ALLOWED_EXTENSIONS = set(['txt', 'csv'])

# Add login URL associated with login function
app.add_url_rule('/login', 'login', ldap.login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', ldap.logout, methods=['GET', 'POST'])

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/search_user', methods=['POST', 'GET'])
@login_required
def search_user():
    """
    Search for a posixAccount in the entire LDAP tree
    """
    form = fm.generate_search_user_form()
    search_resultz=""
    if request.method == 'POST' and form.validate():
        search_resultz = lac.get_resultz_from_search_user_form(form)
    return render_template('search_user.html',
                           userz=search_resultz,
                           form=form,
                           attributes=lac.get_search_user_fieldz(),
                           timestamp=time.strftime("%Y%m%d_%H%M") )


@app.route('/search_group', methods=['POST', 'GET'])
@login_required
def search_group():
    """
    Search for a posixAccount in the entire LDAP tree
    """
    form = fm.generate_search_group_form()
    search_resultz=""
    if request.method == 'POST' and form.validate():
        search_resultz = lac.get_resultz_from_search_group_form(form)
    return render_template('search_group.html',
                           groupz=search_resultz,
                           form=form,
                           attributes=lac.get_search_group_fieldz(),
                           timestamp=time.strftime("%Y%m%d_%H%M") )


@app.route('/change_password/<uid>', methods=['POST', 'GET'])
@login_required
def change_password(uid):
    """
    Change the password for a given UID
    """
    form=ChangePassForm(request.form)
    pwd_policy = ldap.get_user_pwd_policy(uid)
    pwd_min_length = pwd_policy['pwdMinLength'][0]
    if request.method == 'POST' and form.validate():
        lac.update_password_from_form(form, uid)
    return render_template('change_password.html',
                           form=form,
                           uid=uid,
                           pwd_min_length=pwd_min_length)

@app.route('/people/<group>')
@login_required
def show_group_memberz(group):
    memberz = r.smembers("people_groupz:{0}".format(group))
    memberz_count = len(memberz)
    return render_template('show_group_memberz.html',
                           memberz=memberz,
                           group=group,
                           memberz_count=memberz_count)

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
    page_fieldz = Field.query.filter_by(
        page_id = page.id,
        display=True
    ).order_by(Field.priority).all()
    uid_detailz = ldap.get_uid_detailz(uid)
    if uid_detailz is None:
        return redirect(url_for('home'))
    uid_attributez = uid_detailz.get_attributes()
    if 'cinesIpClient' in uid_attributez:
        uid_attributez['cinesIpClient'] = [
            ip for ip in uid_attributez['cinesIpClient'][0].split(";")
        ]
    group_princ = cache.get_posix_group_cn_by_gid(uid_attributez['gidNumber'][0])
    work_groupz = ldap.get_work_groupz_from_member_uid(uid)
    sec_groupz = [ group for group in ldap.get_posix_groupz_from_member_uid(uid)
                   if group[0] != group_princ]
    if 'cinesSoumission' in uid_attributez:
        submission_list = get_list_from_submission_attr(
            uid_attributez['cinesSoumission'][0])
    else:
        submission_list = []
    blockz =sorted(
        set(
            [field.block for field in page_fieldz]
        )
    )
    return render_template('show_user.html',
                           uid = uid,
                           dn=dn,
                           blockz=blockz,
                           uid_attributez=uid_attributez,
                           page_fieldz=page_fieldz,
                           is_active=lac.is_active(uid_detailz),
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
    raw_form = fm.generate_edit_page_admin_form(page)
    form = raw_form['form']
    attr_label_list = raw_form['attr_label_list']
    if request.method == 'POST' :
        lac.update_page_from_form(page, raw_form)
        raw_form = fm.generate_edit_page_admin_form(page)
        form = raw_form['form']
        attr_label_list = raw_form['attr_label_list']
    return render_template('edit_page.html',
                           page=page,
                           attr_label_list = attr_label_list,
                           form=form)

@app.route('/lac_adminz/', methods=('GET', 'POST'))
@admin_login_required
def edit_lac_admin():
    form = fm.generate_edit_lac_admin_form()
    if request.method == 'POST':
        lac.update_lac_admin_from_form(form)
        fm.populate_lac_admin_choices(form)
    return render_template('lac_adminz.html',
                           form=form)

@app.route('/ldap_adminz/', methods=('GET', 'POST'))
@admin_login_required
def edit_ldap_admin():
    form = fm.generate_edit_lac_admin_form()
    if request.method == 'POST':
        lac.update_ldap_admin_from_form(form)
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
    subschema = ldap.get_subschema()
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
    subschema = ldap.get_subschema()
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
    return redirect(url_for('home'))

@app.route('/hello/')
@app.route('/hello/<name>')
@login_required
def hello(name=None):
    return render_template('test.html', name=session['uid'])

@app.route('/add_user/<page_label>', methods=('GET', 'POST'))
@login_required
def add_user(page_label):
    page = Page.query.filter_by(label = page_label).first()
    fieldz = Field.query.filter_by(page_id = page.id,edit = True).order_by(
        Field.priority
    ).all()
    edit_form = fm.generate_add_user_form(page)
    edit_blockz =sorted(set([field.block for field in fieldz]))
    if request.method == 'POST' and edit_form.validate():
        lac.create_ldap_object_from_add_user_form(
            edit_form,
            fieldz,
            page)
        if app.config['PROD_FLAG']:
            lac.upsert_otrs_user(edit_form.uid.data)
        return redirect(url_for('show_user',
                                page=page_label,
                                uid = edit_form.uid.data))
    else:
        fm.set_edit_user_form_values(edit_form,fieldz)
        return render_template('add_user.html',
                               page=page.label,
                               fieldz=fieldz,
                               edit_blockz=edit_blockz,
                               edit_form=edit_form)
    return render_template('add_user.html',
                           add_form=add_form,
                           page=page_label)

@app.route('/edit_user/<page>/<uid>', methods=('GET', 'POST'))
@login_required
def edit_user(page,uid):
    dn = ldap.get_full_dn_from_uid(uid)
    page = Page.query.filter_by(label=page).first()
    form = fm.generate_edit_user_form(page)
    edit_fieldz = Field.query.filter_by(
        page_id = page.id,
        edit = True
    ).order_by(Field.priority).all()
    edit_blockz =sorted(
        set(
            [field.block for field in edit_fieldz]
        )
    )
    show_fieldz = Field.query.filter_by(
        page_id = page.id,
        display=True
    ).order_by(Field.priority).all()
    show_blockz =sorted(
        set(
            [field.block for field in show_fieldz]
        )
    )
    uid_detailz = ldap.get_uid_detailz(uid)
    if uid_detailz is None:
        return redirect(url_for('home'))
    uid_attributez = uid_detailz.get_attributes()
    if 'cinesIpClient' in uid_attributez:
        uid_attributez['cinesIpClient'] = [
            ip for ip in uid_attributez['cinesIpClient'][0].split(";")
        ]
    if request.method == 'POST':
        lac.update_ldap_object_from_edit_user_form(form, edit_fieldz, uid, page)
        cache.update_work_groupz_memberz(
            uid,
            form.wrk_groupz.selected_groupz.data,
            ldap.get_work_groupz_from_member_uid(uid)
        )
        if page.label in app.config['OTRS_ACCOUNT'] and app.config['PROD_FLAG']:
            lac.upsert_otrs_user(uid)
        return redirect(url_for('show_user', page=page.label, uid=uid))
    else:
        fm.set_edit_user_form_values(form, edit_fieldz, uid)
    return render_template('edit_user.html',
                           form=form,
                           page=page,
                           uid=uid,
                           dn=dn,
                           edit_fieldz=edit_fieldz,
                           show_fieldz=show_fieldz,
                           show_blockz=show_blockz,
                           edit_blockz=edit_blockz,
                           uid_attributez=uid_attributez)

@app.route('/delete_user/<uid>', methods=('GET', 'POST'))
@login_required
def delete_user(uid):
    user_dn = ldap.get_full_dn_from_uid(uid)
    dn = ldap.get_full_dn_from_uid(uid)
    posix_groupz = ldap.get_posix_groupz_from_member_uid(uid)
    work_groupz = ldap.get_work_groupz_from_member_uid(uid)
    if request.method == 'POST':
        lac.remove_user_from_all_groupz(uid, posix_groupz, work_groupz)
        if app.config['PROD_FLAG']:
            lac.delete_otrs_user(uid)
        ldap.delete(user_dn)
        cache.populate_grouplist()
        cache.populate_people_group()
        cache.populate_work_group()
        flash(u'Utilisateur {0} supprimé'.format(uid))
        return redirect(url_for('home'))
    return render_template(
        'delete_user.html',
        groupz=[group[0] for group in posix_groupz] + work_groupz,
        uid=uid,
        dn=user_dn)

@app.route('/select_work_groups/<uid>', methods=('GET', 'POST'))
@login_required
def select_work_groups(uid):
    form = fm.generate_select_work_group_form(uid)
    if request.method == 'POST':
        for group in form.selected_groupz.data:
            cache.add_to_work_group_if_not_member(group, [uid])
        for group in actual_work_groupz:
            if group not in form.selected_groupz.data:
                cache.rem_from_workgroup_if_member(group, [uid])
        flash(u'Groupes de travail mis à jour')
        return redirect(url_for('show_user',
                                page=cache.get_group_from_member_uid(uid),
                                uid=uid))
    return render_template('select_work_groups.html',
                           form=form,
                           uid=uid)

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

@app.route('/add_group/<page_label>', methods=('GET', 'POST'))
@login_required
def add_group(page_label=None):
    if page_label in app.config['C4_TYPE_GROUPZ']:
        add_form = fm.generate_add_c4_group_form()
    elif page_label == 'grProjet':
        add_form = fm.generate_add_project_group_form()
    else:
        add_form = fm.generate_add_group_form()
    if request.method == 'POST':
        if add_form.cn.data and add_form.validate():
            if lac.create_ldap_object_from_add_group_form(add_form, page_label):
                return redirect(url_for("show_group",
                                        branch=page_label,
                                        cn=add_form.cn.data))
            else :
                return redirect(url_for("add_group",
                                        page_label = page_label))
    return render_template('add_group.html',
                           add_form=add_form,
                           page_label=page_label)

@app.route('/edit_group/<branch>/<group_cn>', methods=('GET', 'POST'))
@login_required
def edit_group(branch, group_cn):
    dn = ldap.get_group_full_dn(branch, group_cn)
    page = Page.query.filter_by(label=branch).first()
    form = fm.generate_edit_group_form(page, branch, group_cn)
    fieldz = Field.query.filter_by(
        page_id = page.id,
        edit = True
    ).order_by(Field.priority).all()
    blockz =sorted(
        set(
            [field.block for field in fieldz]
        )
    )
    if request.method == 'POST':
        if branch == 'grCcc':
            ressource = C4Ressource.query.filter_by(
                code_projet = group_cn).first()
            if ressource:
                comite = ressource.comite.ct
            else:
                comite = ''
            lac.update_group_memberz_cines_c4(branch, group_cn, comite)
        lac.update_ldap_object_from_edit_group_form(form,page,group_cn)
        flash(u'Groupe {0} mis à jour'.format(group_cn))
        return redirect(url_for("show_group",
                                branch=branch,
                                cn=group_cn))
    fm.set_edit_group_form_values(form, fieldz, branch, group_cn)
    #print(form.filesystem.type)
    return render_template('edit_group.html',
                           form=form,
                           page=page,
                           dn=dn,
                           group_cn=group_cn,
                           fieldz=fieldz,
                           blockz=blockz)

@app.route('/delete_group/<branch>/<cn>')
@login_required
def delete_group(branch, cn):
    if ldap.get_posix_group_memberz(branch, cn):
        flash(u'Le groupe n\'est pas vide.\nImpossible de supprimer le groupe.')
    else:
        dn = ldap.get_group_full_dn(branch, cn)
        ldap.delete(dn)
        cache.populate_grouplist()
        cache.populate_people_group()
        cache.populate_work_group()
        flash(u'Groupe {0} supprimé'.format(cn))
        return redirect(url_for('home'))
    return redirect(url_for('show_group',
                            branch=branch,
                            cn=cn))

@app.route('/add_workgroup/', methods=('GET', 'POST'))
@login_required
def add_workgroup():
    page = Page.query.filter_by(label = 'grTravail').first()
    fieldz = Field.query.filter_by(page_id = page.id,edit = True).order_by(
        Field.priority
    ).all()
    blockz =sorted(set([field.block for field in fieldz]))
    add_form = fm.generate_add_workgroup_form(fieldz)
    if request.method == 'POST':
        if add_form.validate():
            if lac.create_ldap_object_from_add_workgroup_form(
                    add_form):
                return redirect(url_for("show_workgroup",
                                        cn=add_form.cn.data))
            else :
                return redirect(url_for("add_workgroup"))
    return render_template('add_workgroup.html',
                           fieldz=fieldz,
                           blockz=blockz,
                           add_form=add_form)

@app.route('/show_workgroup/<cn>')
@login_required
def show_workgroup(cn):
    page = Page.query.filter_by(label = "grTravail").first()
    page_fieldz = Field.query.filter_by(
        page_id = page.id,
        display=True
    ).order_by(Field.priority).all()
    ldap_filter='(cn={0})'.format(cn)
    attributes=['*','+']
    base_dn='ou=grTravail,{0}'.format(
        app.config['LDAP_SEARCH_BASE']
    )
    cn_detailz = ldap.search(ldap_filter=ldap_filter,
                              attributes=attributes,
                              base_dn=base_dn)
    if not cn_detailz:
        flash(u'Groupe non trouvé')
        return redirect(url_for('show_workgroups'))
    cn_attributez=cn_detailz[0].get_attributes()
    if 'uniqueMember' in cn_attributez:
        cn_attributez['uniqueMember'] = [get_uid_from_dn(member)
                                         for member in sorted(
                                                 cn_attributez['uniqueMember'])]
    if 'cinesGrWorkType' in cn_attributez:
        cn_attributez['cinesGrWorkType'] = [
            'Oui' if cn_attributez['cinesGrWorkType'][0] == '1' else "Non"]
    dn = cn_attributez['entryDN'][0]
    blockz =sorted(
        set(
            [field.block for field in page_fieldz]
        )
    )
    return render_template('show_workgroup.html',
                           blockz=blockz,
                           cn = cn,
                           dn=dn,
                           cn_attributez=cn_attributez,
                           page_fieldz=page_fieldz
    )

@app.route('/show_group/<branch>/<cn>')
@login_required
def show_group(branch, cn):
    page = Page.query.filter_by(label = branch).first()
    page_fieldz = Field.query.filter_by(
        page_id = page.id,
        display=True
    ).order_by(Field.priority).all()
    ldap_filter='(cn={0})'.format(cn)
    attributes=['*','+']
    base_dn='ou={0},ou=groupePosix,{1}'.format(
        branch,
        app.config['LDAP_SEARCH_BASE']
    )
    cn_detailz = ldap.search(ldap_filter=ldap_filter,
                              attributes=attributes,
                              base_dn=base_dn)
    if not cn_detailz:
        flash(u'Groupe non trouvé')
        return redirect(url_for('show_groups',
                                branch=branch))
    cn_attributez=cn_detailz[0].get_attributes()
    if 'memberUid' in cn_attributez:
        cn_attributez['memberUid'] = sorted(cn_attributez['memberUid'])
    principal_memberz = ldap.get_posix_group_principal_memberz_from_gid(
            cn_attributez['gidNumber'][0]
        )
    dn = cn_attributez['entryDN'][0]
    default_storagez_labelz = [storage.get_attributes()['cn'][0]
                       for storage in ldap.get_default_storage_list()]
    kustom_storagez_labelz = [
        storage.get_attributes()['cn'][0]
        for storage in ldap.get_group_quota_list()
        if storage.get_attributes()['cn'][
                0
        ].split('.')[1] == cn_attributez['gidNumber'][0]
    ]
    quotaz = []
    for storage in default_storagez_labelz:
        if kustom_storagez_labelz:
            for kustom_storage in kustom_storagez_labelz:
                if storage in kustom_storage:
                    quotaz.append((storage, kustom_storage))
        else:
            quotaz.append((storage, None))
    if branch == 'grCcc':
        ressource = C4Ressource.query.filter_by(code_projet = cn).first()
        projet = C4Projet.query.filter_by(
            code_projet = cn).first()
        code_personne = projet.code_personne if projet else ""
        manager = C4Personne.query.filter_by(
            code_personne=code_personne).first()
        bull_computed = db.session.query(
            func.sum(C4OCCIGEN.walltime * C4OCCIGEN.nbcoeurs) / 3600
        ).filter_by(grpunix=cn).group_by(C4OCCIGEN.grpunix).first()
        ibm_computed = db.session.query(
            func.sum(C4IBM.walltime * C4IBM.nbcoeurs) / 3600
        ).filter_by(grpunix=cn).group_by(C4IBM.grpunix).first()
        if ibm_computed:
            ibm_computed = int(ibm_computed[0])
        if bull_computed:
            bull_computed = int(bull_computed[0])
    else:
        ressource = None
        manager = None
        bull_computed = None
        ibm_computed = None
    blockz =sorted(
        set(
            [field.block for field in page_fieldz]
        )
    )
    return render_template('show_group.html',
                           blockz=blockz,
                           cn = cn,
                           dn=dn,
                           cn_attributez=cn_attributez,
                           page_fieldz=page_fieldz,
                           branch=branch,
                           ressource=ressource,
                           manager=manager,
                           bull_computed=bull_computed,
                           ibm_computed=ibm_computed,
                           principal_memberz=principal_memberz,
                           quotaz=quotaz)

@app.route('/show_groups/<branch>')
@login_required
def show_groups(branch):
    groupz = [group.get_attributes()['cn'][0]
              for group in  ldap.get_posix_groupz(branch)]
    groupz_count = len(groupz)
    return render_template('show_groupz.html',
                           groupz=groupz,
                           branch=branch,
                           groupz_count=groupz_count)


@app.route('/show_workgroups/')
@login_required
def show_workgroups():
    groupz = ldap.get_work_groupz()
    groupz_count = len(groupz)
    return render_template('show_workgroupz.html',
                           groupz=groupz,
                           groupz_count=groupz_count)

@app.route('/edit_workgroup/<group_cn>', methods=('GET', 'POST'))
@login_required
def edit_workgroup(group_cn):
    dn = "cn={0},ou=grTravail,,{1}".format(
        group_cn,
        app.config['LDAP_SEARCH_BASE']
    )
    page = Page.query.filter_by(label='grTravail').first()
    form = fm.generate_edit_workgroup_form(page, group_cn)
    fieldz = Field.query.filter_by(
        page_id = page.id,
        edit = True
    ).order_by(Field.priority).all()
    blockz =sorted(
        set(
            [field.block for field in fieldz]
        )
    )
    if request.method == 'POST':
        lac.update_ldap_object_from_edit_workgroup_form(form,page,group_cn)
        flash(u'Groupe {0} mis à jour'.format(group_cn))
        return redirect(url_for("show_workgroup",
                                cn=group_cn))
    fm.set_edit_workgroup_form_values(form, fieldz, group_cn)
    return render_template('edit_workgroup.html',
                           form=form,
                           page=page,
                           dn=dn,
                           group_cn=group_cn,
                           fieldz=fieldz,
                           blockz=blockz)

@app.route('/delete_workgroup/<cn>')
@login_required
def delete_workgroup(cn):
    if ldap.get_workgroup_memberz(cn):
        flash(u'Le groupe n\'est pas vide.\nImpossible de supprimer le groupe.')
    else:
        dn = "cn={0},ou=grTravail,,{1}".format(
            cn,
            app.config['LDAP_SEARCH_BASE']
        )
        ldap.delete(dn)
        cache.populate_grouplist()
        cache.populate_people_group()
        cache.populate_work_group()
        flash(u'Groupe de travail {0} supprimé'.format(cn))
        return redirect(url_for('home'))
    return redirect(url_for('show_workgroup',
                            cn=cn))

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
    edit_form = fm.generate_kustom_batch_edit_form(page, attrz_list)
    group_form = SelectGroupzForm(request.form)
    group_form.available_groupz.choices = ldap.get_posix_groupz_choices()
    group_form.selected_groupz.choices = []
    if request.method == 'POST':
        if view_form.attr_form.selected_attr.data:
            group_form = SelectGroupzForm(request.form)
            group_form.available_groupz.choices = ldap.get_posix_groupz_choices()
            group_form.selected_groupz.choices = []
            session[
                'edit_by_group_fieldz_id'
            ] = view_form.attr_form.selected_attr.data
            return render_template('edit_by_group.html',
                                   group_form=group_form)
        elif group_form.selected_groupz.data:
            groupz_id = group_form.selected_groupz.data
            groupz_infoz = [
                (ldap.get_branch_from_posix_group_gidnumber(id),
                 cache.get_posix_group_cn_by_gid(id))
                for id in groupz_id
            ]
            groupz_memberz = ldap.get_posix_groupz_memberz(groupz_infoz)
            session[
                'edit_by_group_memberz_uid'
            ] = groupz_memberz
            fieldz = Field.query.filter(
                Field.id.in_(session['edit_by_group_fieldz_id'])
            ).all()
            print('fieldz {0}'.format(fieldz))
            edit_form = fm.generate_kustom_batch_edit_form(
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
        for group in ldap.get_submission_groupz_list()
    ]
    uid_attributez=ldap.get_uid_detailz(uid).get_attributes()
    if 'cinesSoumission' in uid_attributez:
        submission_list = get_list_from_submission_attr(
            uid_attributez['cinesSoumission'][0])
    else:
        submission_list = []
    work_groupz = {}
    for group in ldap.get_submission_groupz_list():
        is_member = dn in r.smembers( "wrk_groupz:{0}".format(group))
        is_submission = (group, '1') in submission_list
        work_groupz[group] = {'is_member': is_member,
                              'is_submission': is_submission}
    if request.method == 'POST':
        lac.update_user_submission(uid, form)
        return redirect(url_for('show_user',
                                page = cache.get_group_from_member_uid(uid),
                                uid = uid))
    return render_template('edit_submission.html',
                           form=form,
                           dn=dn,
                           uid=uid,
                           work_groupz=work_groupz)

@app.route('/edit_group_submission/', methods=('GET', 'POST'))
@login_required
def edit_group_submission():
    form = fm.generate_edit_group_submission()
    if request.method == 'POST':
        lac.update_group_submission(form)
        return redirect(url_for('home'))
    return render_template('edit_group_submission.html',
                           form=form)

@app.route('/toggle_account/<uid>')
@login_required
def toggle_account(uid):
    user = ldap.get_uid_detailz(uid)
    if lac.is_active(user):
        lac.disable_account(user)
    else:
        lac.enable_account(user)
    return redirect(url_for('show_user',
                            page = cache.get_group_from_member_uid(uid),
                            uid = uid))

@app.route('/edit_default_quota/')
@app.route('/edit_default_quota/<storage_cn>', methods=('GET', 'POST'))
@admin_login_required
def edit_default_quota(storage_cn=None):
    storagez_labelz = [storage.get_attributes()['cn'][0]
                       for storage in ldap.get_default_storage_list()]
    if storage_cn is not None:
        dn = ldap.get_full_dn_from_cn(storage_cn)
        storage = ldap.get_default_storage(storage_cn).get_attributes()
        form = EditDefaultQuotaForm(request.form)
        if request.method == 'POST' and form.validate():
            update_default_quota(storage_cn, form)
            return redirect(url_for('home'))
        fm.set_default_quota_form_values(form, storage)
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
    if storage_cn is not None:
        dn = ldap.get_full_dn_from_cn(storage_cn)
        storage = ldap.get_storage(storage_cn).get_attributes()
        form = EditQuotaForm(request.form)
        if request.method == 'POST' and form.validate():
            update_quota(storage, form)
            return redirect(url_for('home'))
        default_fieldz = fm.set_quota_form_values(form, storage)
        return render_template('edit_quota.html',
                               form=form,
                               dn=dn,
                               storage_cn=storage_cn,
                               default_fieldz=default_fieldz)
    else:
        return render_template('edit_quota.html',
                               storagez=lac.get_storagez_labelz())

@app.route('/add_quota/', methods=('GET', 'POST'))
@app.route('/add_quota/<storage>/<group>', methods=('GET', 'POST'))
@admin_login_required
def add_quota(storage=None, group=None):
    form = fm.generate_create_quota_form()
    if storage and group:
        create_ldap_quota(storage, group)
        return redirect(
            url_for('edit_quota',
                    storage_cn = '{0}.{1}'.format(storage, group)))
    if (request.method == 'POST' and form.validate()):
        niou_cn = '{0}.{1}'.format(
            form.default_quota.data,
            form.group.data)
        create_ldap_quota(form.default_quota.data, form.group.data)
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
    response = lac.generate_backup_file_response(userz, attributez)
    return response

@app.route('/edit_file/', methods=('GET', 'POST'))
@login_required
def edit_file():
    page = Page.query.filter_by(label='edit_file').first()
    if 'edit_file_fieldz_id' in session:
        attrz_list = session['edit_file_fieldz_id']
    else:
        attrz_list = []
    if 'edit_file_memberz_uid' in session:
        userz = session['edit_file_memberz_uid']
    else:
        userz = []
    edit_form = fm.generate_kustom_batch_edit_form(page, attrz_list)
    file_form = UserzFileForm(request.form)
    view_form = fm.generate_edit_file_view_form(page)
    if request.method == 'POST':
        if view_form.attr_form.selected_attr.data:
            session['edit_file_fieldz_id'] = view_form.attr_form.selected_attr.data
            return render_template('edit_file.html',file_form=file_form)
        elif file_form.userz_file and edit_form.submited.data == 'False' :
            userz_file = request.files[file_form.userz_file.name]
            if userz_file and allowed_file(userz_file.filename):
                userz = userz_file.read().split('\n')
            else:
                flash('Format du fichier incorrect')
                return render_template('edit_file.html',
                                       file_form=file_form)
            session['edit_file_memberz_uid'] = userz
            fieldz = Field.query.filter(Field.id.in_(attrz_list)).all()
            edit_form = fm.generate_kustom_batch_edit_form(
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
            update_users_by_file(edit_form, attrz_list)
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
        form = LDAPObjectTypeForm(request.form)
        if request.method == 'POST':
            print(form.apply_to.data)
            lac.create_ldap_object_from_add_object_type_form(form,
                                                             ldap_object_type)
            return redirect(url_for('home'))
        fm.set_edit_ldap_object_type_form_valuez(ldap_object_type, form)
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
                 for ppolicy in ldap.get_all_ppolicies()]
    return render_template('show_ppolicies.html',
                           ppolicies=ppolicies)

@app.route('/add_ppolicy/', methods=('GET', 'POST'))
@login_required
def add_ppolicy():
    form = AddPolicyForm(request.form)
    if request.method == 'POST' and form.validate():
        cn = form.cn.data.encode('utf-8')
        lac.add_ppolicy(cn)
        return redirect(url_for('edit_ppolicy',ppolicy_label= cn))
    return render_template('add_ppolicy.html',form=form)

@app.route('/edit_ppolicy/<ppolicy_label>',
           methods=('GET', 'POST'))
@login_required
def edit_ppolicy(ppolicy_label):
    page = Page.query.filter_by(label = 'ppolicy').first()
    form = fm.generate_edit_ppolicy_form_class(page)(request.form)
    fieldz = Field.query.filter_by(page_id = page.id,edit = True).all()
    fieldz_labelz = [field.label for field in fieldz]
    if request.method == 'POST' and form.validate() :
        lac.update_ldap_object_from_edit_ppolicy_form(form,
                                                  fieldz_labelz,
                                                  ppolicy_label)
        return redirect(url_for('home'))
    else:
        fm.set_edit_ppolicy_form_values(form, fieldz_labelz, ppolicy_label)
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
    raw_logz = ldap.get_uid_logz(uid)
    print(raw_logz[0])
    logz = []
    for raw_log in raw_logz:
        log_attrz = raw_log.get_attributes()
        if 'reqMod' in log_attrz:
            raw_new_valuez = log_attrz['reqMod']
        if 'reqOld' in log_attrz:
            raw_old_valuez = log_attrz['reqOld']
        new_valuez_dict = lac.get_dict_from_raw_log_valuez(raw_new_valuez)
        old_valuez_dict = lac.get_dict_from_raw_log_valuez(raw_old_valuez)
        log = {'modified_by': log_attrz['reqAuthzID'][0],
               'modified_date': converter.generalized_time_sec_to_datetime(
                   log_attrz['reqStart'][0] ),
               'new_valuez': new_valuez_dict,
               'old_valuez': old_valuez_dict}
        logz.append(log)
    ordered_logz = sorted(logz, key=lambda k: k['modified_date'], reverse=True)
    return render_template('show_history.html',
                               uid = uid,
                               logz=ordered_logz)

@app.route('/refresh_cache')
@login_required
def refresh_cache():
    cache.populate_grouplist()
    cache.populate_people_group()
    cache.populate_work_group()
    return redirect(url_for('home'))

### Funkz to load at app startup

@app.before_first_request
def init_populate_grouplist():
    cache.populate_grouplist()

@app.before_first_request
def init_populate_people_group():
    cache.populate_people_group()

@app.before_first_request
def init_populate_work_group():
    cache.populate_work_group()

@app.before_first_request
def init_populate_last_used_idz():
    lac.populate_last_used_idz()

def get_attr(form, name):
    return getattr(form, name)

def get_type(obj):
    return str(type(obj))

# jinja funkz

app.jinja_env.globals.update(get_attr=get_attr)

app.jinja_env.globals.update(
    get_cinesdaterenew_from_uid=lac.get_cinesdaterenew_from_uid)


app.jinja_env.globals.update(get_type=get_type)

app.jinja_env.globals.update(
    get_branch_from_posix_group_gidnumber=ldap.get_branch_from_posix_group_gidnumber
)

app.jinja_env.globals.update(
    get_branch_from_posix_group_dn=ldap.get_branch_from_posix_group_dn
)

app.jinja_env.globals.update(
    get_group_from_member_uid=cache.get_group_from_member_uid
)

app.jinja_env.globals.update(
    get_posix_group_cn_by_gid=cache.get_posix_group_cn_by_gid
)

app.jinja_env.globals.update(
    convert_to_display_mode = converter.to_display_mode
)



_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

@app.template_filter()
@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p
                          for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result
