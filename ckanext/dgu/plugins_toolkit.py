'''Handy wrapper for ckan.plugin.toolkit to make the attributes importable,
as is normal for Python.
'''
import ckan.plugins.toolkit as t

_ = t._
c = t.c
request = t.request
render = t.render
render_text = t.render_text
asbool = t.asbool
asint = t.asint
aslist = t.aslist
literal = t.literal

get_action = t.get_action
check_access = t.check_access
ObjectNotFound = t.ObjectNotFound
NotAuthorized = t.NotAuthorized
ValidationError = t.ValidationError

CkanCommand = t.CkanCommand

# class functions
render_snippet = t.render_snippet
add_template_directory = t.add_template_directory
add_public_directory = t.add_public_directory
requires_ckan_version = t.requires_ckan_version
check_ckan_version = t.check_ckan_version
CkanVersionException = t.CkanVersionException
