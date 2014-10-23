drop table if exists ldap_auth_history;
create table ldap_auth_history (
    id integer primary key autoincrement,
    ldap_uid_number integer,
    ldap_uid varchar(50)
)
