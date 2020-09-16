# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "hemtech"
app_title = "Hemtech"
app_publisher = "FinByz Tech Pvt Ltd"
app_description = "Custom App for Hemtech"
app_icon = "octicon octicon-globe"
app_color = "#770515"
app_email = "info@finbyz.com"
app_license = "GPL 3.0"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hemtech/css/hemtech.css"
# app_include_js = "/assets/hemtech/js/hemtech.js"


# include js, css files in header of web template
# web_include_css = "/assets/hemtech/css/hemtech.css"
# web_include_js = "/assets/hemtech/js/hemtech.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "hemtech.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "hemtech.install.before_install"
# after_install = "hemtech.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hemtech.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

override_whitelisted_methods = {
	"frappe.core.page.permission_manager.permission_manager.get_roles_and_doctypes": "hemtech.permission.get_roles_and_doctypes",
	"frappe.core.page.permission_manager.permission_manager.get_permissions": "hemtech.permission.get_permissions",
	"frappe.core.page.permission_manager.permission_manager.add": "hemtech.permission.add",
	"frappe.core.page.permission_manager.permission_manager.update": "hemtech.permission.update",
	"frappe.core.page.permission_manager.permission_manager.remove": "hemtech.permission.remove",
	"frappe.core.page.permission_manager.permission_manager.reset": "hemtech.permission.reset",
	"frappe.core.page.permission_manager.permission_manager.get_users_with_role": "hemtech.permission.get_users_with_role",
	"frappe.core.page.permission_manager.permission_manager.get_standard_permissions": "hemtech.permission.get_standard_permissions"
}

doc_events = {
	"Manufacturer": {
		"validate": "hemtech.api.mn_validate",
		"onload": "hemtech.api.mn_onload",
		"on_trash": "hemtech.api.mn_on_trash"
	},
	"Delivery Note": {
		"before_naming": "hemtech.api.before_naming"
	},
	"Sales Invoice": {
		"before_naming": "hemtech.api.before_naming"
	},
	"Purchase Invoice": {
		"before_naming": "hemtech.api.before_naming"
	},
	"Purchase Order": {
		"before_naming": "hemtech.api.before_naming"
	},
	"Purchase Receipt": {
		"before_naming": "hemtech.api.before_naming"
	},
	"Fiscal Year": {
		'before_save': 'hemtech.api.fiscal_before_save'
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"hemtech.tasks.all"
# 	],
# 	"daily": [
# 		"hemtech.tasks.daily"
# 	],
# 	"hourly": [
# 		"hemtech.tasks.hourly"
# 	],
# 	"weekly": [
# 		"hemtech.tasks.weekly"
# 	]
# 	"monthly": [
# 		"hemtech.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "hemtech.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hemtech.event.get_events"
# }

