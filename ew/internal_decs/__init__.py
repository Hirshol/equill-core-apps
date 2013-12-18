#!/usr/bin/env python
"""Useful internal_dec common code and constants live in this module
@author: Samantha Atkins
"""
INBOX_DOC_ID = 'Inbox_Document'
TEMPLATES_DOC_ID = "Templates_Document"
SETTINGS_DOC_ID = "Settings_Document"
LOGIN_DOC_ID = "Login"
PROVISION_DOC_ID = "NotProvisioned"
LEGAL_DOC_ID = "Legal"
REGULATORY_DOC_ID = "Regulatory"
LICENSE_DOC_ID = "License"

def get_inbox():
    import pdb, sdk.document
    return sdk.document.Document.at_path('/data/inbox/Inbox_Document')

def get_templates():
    import pdb, sdk.document
    return sdk.document.Document.at_path('/data/inbox/Templates_Document')

