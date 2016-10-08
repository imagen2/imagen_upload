#! /usr/bin/env python
##########################################################################
# NSAp - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import

# CW import
from cubicweb.web.views.primary import PrimaryView
from cubicweb.predicates import is_instance
from cubes.rql_upload.views.primary import CWUploadPrimaryView


class Imagen_CWUploadPrimaryView(PrimaryView):
    """
    """

    __select__ = PrimaryView.__select__ & is_instance("CWUpload")

    def call(self, rset=None):
        eUpload = self.cw_rset.get_entity(0, 0)
        self.w(u'<div class="page-header">')
        self.w(u'<h2>')
        if eUpload.status == 'Quarantine':
            self.w(u"<span class='glyphicon glyphicon-cog' />")
        elif eUpload.status == 'Rejected':
            self.w(u"<span class='glyphicon glyphicon-remove' />")
        elif eUpload.status == 'Validated':
            self.w(u"<span class='glyphicon glyphicon-ok' />")
        else:
            self.w(u"<span class='glyphicon glyphicon-cloud-upload' />")
        self.w(u' {}</h2>'.format(eUpload.dc_title()))
        self.w(u'</div>')

        self.w(u'<div>')
        self.w(u'<h3>Status</h3>')
        self.w(u'<b>{}</b>'.format(eUpload.status))
        print 'error: {}'.format(eUpload.error)
        if eUpload.error:
            self.w(u'<div class="panel panel-danger">{}</div>'.format(
                eUpload.error))
        self.w(u'</div>')

        self.w(u'<div>')
        self.w(u'<h3>Fields</h3>')
        self.w(u'<table class="upload-table">')
        self.w(u'<tr><th>Name</th><th>Value</th></tr>')
        for eField in sorted(eUpload.upload_fields,
                             key=lambda field: field.name):
            self.w(u'<tr><td>{0}</td><td>{1}</td></tr>'.format(
                   eField.label, eField.value))
        self.w(u'</table>')
        self.w(u'</div>')

        self.w(u'<div>')
        self.w(u'<h3>Files</h3>')
        self.w(u'<table class="upload-table">')
        self.w(u'<tr><th>Name</th><th>SHA1</th></tr>')
        for eFile in sorted(eUpload.upload_files,
                            key=lambda field: field.name):
            self.w(u'<tr><td>{0}</td><td>{1}</td></tr>'.format(
                   eFile.data_name, eFile.data_sha1hex))
        self.w(u'</table>')
        self.w(u'</div>')


def registration_callback(vreg):
    """ Register the tuned primary views.
    """

    vreg.register_and_replace(Imagen_CWUploadPrimaryView, CWUploadPrimaryView)
