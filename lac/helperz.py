import re


def get_uid_from_dn(dn):
    m = re.search('uid=(.+?),', dn)
    if m:
        return m.group(1)
    else:
        return ''

def get_list_from_submission_attr(sub_attr):
    sub_list = []
    for group in sub_attr.split(';'):
        split_group = group.split('=')
        if split_group != ['']:
            sub_list.append((split_group[0],split_group[1]))
    return sub_list
