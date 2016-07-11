# -*- coding: utf-8 -*-
##########################################################################
# NSAp - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import hashlib
import os
import re
import shutil
import traceback

from cubes.rql_upload.tools import get_or_create_logger
from imagen.sanity import cantab, imaging
from . import cati

SID_ERROR_MESSAGE = ("- The subject ID is malformed."
                     " [12 decimal digits required]<br/>")

UPLOAD_ALREADY_EXISTS = ("- A similar upload already exists."
                         " [Same subject ID and time point "
                         " and not rejected upload]."
                         " Please contact an administrator if you want"
                         " to force the upload.<br/>")

SYSTEM_ERROR_RAISED = ("- A system error raised."
                       " Please send the following message"
                       " to an administrator.")


def get_message_error(flag, errors):
    """ Generate a message error from error list.


    Pameters:
        flag: True or False. True mean 'has errors'
        errors: error list
    """

    message = ''
    if not flag:
        for err in errors:
            message += err.__str__()
            message += u'<br/>'
    return message


def is_PSC1(value):
    """ Cheks if  value is well formated (12 decimal digits)

    Pameters:
        value: a value reprsenting a PSC1

    Return:
        Return True value match with the pattern, False otherwise
    """
    if re.match("^\d{12}$", value) is None:
        return False
    else:
        return True


def is_aldready_uploaded(connexion, posted, formname, uid):
    """ Checks if an equivalent upload is already done.
        To be equivalent an upload must have:
            a status different than 'Rejected' and
            a uploadfield with equal SID and
            a uploadfield with equal TIME_POINT

    Pameters:
        connexion: connexion use to query
        posted: dictionnary of form posted fields
        formname: form name
        uid: current created CWUpload id

    Return:
        Return True if an equivalent upload is already done, False otherwise
    """
    rql = ("Any COUNT(X) WHERE X is CWUpload,"
           " NOT X eid '{}',"
           " X form_name ILIKE '{}',"
           " NOT X status 'Rejected',"
           " X upload_fields F1, F1 name 'sid', F1 value '{}',"
           " X upload_fields F2, F2 name 'time_point', F2 value '{}'"
           )
    rql = rql.format(
        uid,
        formname,
        posted['sid'],
        posted['time_point']
    )
    rset = connexion.execute(rql)
    if rset.rows[0][0] == 0L:
        return False
    else:
        return True


def synchrone_check_cantab(connexion, posted, upload, files, fields):
    """ Call is_PSC1 and is_aldready_uploaded methods first.
        Then call methods of imagen.sanity.cantab
        than checks name file and content

    Pameters:
        connexion: connexion use to query
        posted: dictionnary of form posted fields
        upload: CWUpload entity
        files: UploafFile entities
        fields: UploafField entities

    Return:
        Return None if checks pass, error message otherwise
    """

    message = ''
    # checks
    # checks
    if not is_PSC1(posted['sid']):
        message += SID_ERROR_MESSAGE
    if is_aldready_uploaded(connexion, posted, upload.form_name, upload.eid):
        message += UPLOAD_ALREADY_EXISTS

    #dimitri check
    sid = posted['sid']
    tid = posted['time_point']
    psc1 = True
    errors = None
    for ufile in files:
        if ufile.name == 'cant':
            psc1, errors = cantab.check_cant_name(
                ufile.data_name, sid, tid)
            message += get_message_error(psc1, errors)
            psc1, errors = cantab.check_cant_content(
                ufile.get_file_path(), sid, tid)
            message += get_message_error(psc1, errors)
        elif ufile.name == 'datasheet':
            psc1, errors = cantab.check_datasheet_name(
                ufile.data_name, sid, tid)
            message += get_message_error(psc1, errors)
            psc1, errors = cantab.check_datasheet_content(
                ufile.get_file_path(), sid, tid)
            message += get_message_error(psc1, errors)
        elif ufile.name == 'detailed_datasheet':
            psc1, errors = cantab.check_detailed_datasheet_name(
                ufile.data_name, sid, tid)
            message += get_message_error(psc1, errors)
            psc1, errors = cantab.check_detailed_datasheet_content(
                ufile.get_file_path(), sid, tid)
            message += get_message_error(psc1, errors)
        elif ufile.name == 'report':
            psc1, errors = cantab.check_report_name(
                ufile.data_name, sid, tid)
            message += get_message_error(psc1, errors)
            psc1, errors = cantab.check_report_content(
                ufile.get_file_path(), sid, tid)
            message += get_message_error(psc1, errors)

    # return
    if message:
        return message
    else:
        return None


def asynchrone_check_cantab(repository):
    """ Copy uploaded cantab files from 'upload_dir' to 'validated_dir/...'
        and set status 'validated'

    Pameters:
        upload: A cubicweb repository object
    """

    logger = get_or_create_logger(repository.vreg.config)
    validated_dir = repository.vreg.config["validated_directory"]

    rql = ("Any X WHERE X is CWUpload,"
           " X form_name ILIKE 'cantab', X status 'Quarantine'")
    with repository.internal_cnx() as cnx:
        rset = cnx.execute(rql)
        for entity in rset.entities():
            try:
                sid = entity.get_field_value('sid')
                centre = entity.get_field_value('centre')
                tp = entity.get_field_value('time_point')
                for eUFile in entity.upload_files:
                    from_file = eUFile.get_file_path()
                    to_file = u'{0}/{1}/{2}/{3}/AdditionnalData'.format(
                        validated_dir, tp, centre, sid)
                    if not os.path.exists(to_file):
                        os.makedirs(to_file)
                    to_file = to_file + "/{}".format(eUFile.data_name)
                    shutil.copy2(from_file, to_file)
                    sha1 = unicode(
                        hashlib.sha1(open(to_file, 'rb').read()).hexdigest())
                    if sha1 == eUFile.data_sha1hex:
                        os.remove(from_file)
                        os.symlink(to_file, from_file)
                        logger.info(
                            ("Copy from '{}' to '{}'"
                             ", delete and create symlink".format(
                                 from_file, to_file)))
                    else:
                        logger.critical(
                            "Incorrect copy from '{}' to '{}'".format(
                                from_file, to_file))
                rql = ("SET X status 'Validated'"
                       " WHERE X is CWUpload, X eid '{}'".format(entity.eid))
                cnx.execute(rql)
            except:
                stacktrace = traceback.format_exc()
                stacktrace = stacktrace.replace('"', "'").replace("'", "\\'")
                logger.critical("A system error raised")
                rql = ("SET X status 'Rejected', X error '{} <br/> {}'"
                       " WHERE X is CWUpload, X eid '{}'".format(
                           SYSTEM_ERROR_RAISED,
                           stacktrace,
                           entity.eid))
                cnx.execute(rql)
        cnx.commit()


def synchrone_check_rmi(connexion, posted, upload, files, fields):
    """ Call is_PSC1 and is_aldready_uploaded methods first.
        Then call methods of imagen.sanity.imaging
        than checks name file and content

    Pameters:
        connexion: connexion use to query
        posted: dictionnary of form posted fields
        upload: CWUpload entity
        files: UploafFile entities
        fields: UploafField entities
    Return:
        Return None if checks pass, error message otherwise
    """

    message = ''
    # checks
    if not is_PSC1(posted['sid']):
        message += SID_ERROR_MESSAGE
    if is_aldready_uploaded(connexion, posted, upload.form_name, upload.eid):
        message += UPLOAD_ALREADY_EXISTS

    #dimitri check
    sid = posted['sid']
    tid = posted['time_point']
    psc1 = True
    errors = None
    psc1, errors = imaging.check_zip_name(files[0].data_name, sid, tid)
    message += get_message_error(psc1, errors)
    psc1, errors = imaging.check_zip_content(
        files[0].get_file_path(), sid, tid)
    message += get_message_error(psc1, errors)

    # return
    if message:
        return message
    else:
        return None


def asynchrone_check_rmi(repository):
    """ For each 'Quarantine' CWUpload,
        send the file to cati repository if not already sent.
        Retrieve a response from cati.
        If there is a response then define status and error message to
        CWUpload following response content

    Pameters:
        upload: A cubicweb repository object
    """

    config = repository.vreg.config
    logger = get_or_create_logger(config)
    validated_dir = config["validated_directory"]

    cati.LOGGER = logger
    cati.CATI_WORFLOW_DIRECTORY = config["cati_workflow_directory"]
    if not cati.is_system_OK():
        return

    rql = ("Any X WHERE X is CWUpload,"
           " X form_name ILIKE 'MRI', X status 'Quarantine'")
    with repository.internal_cnx() as cnx:
        rset = cnx.execute(rql)
        for entity in rset.entities():
            args = {f.name: f.value for f in entity.upload_fields}
            sid = args['sid']
            centre = args['centre']
            tp = args['time_point']
            try:
                # send uploaded file to cati
                cati.send_entry(
                    entity.upload_files[0].data_name,
                    entity.upload_files[0].get_file_path(),
                    args
                )
                # retrieve response from cati
                response = cati.get_response(entity.upload_files[0].data_name)
                if response is None:
                    continue
                if response[0] == "Rejected":
                    rql = ("SET X status 'Rejected', X error '{}'"
                           " WHERE X is CWUpload, X eid {}".format(
                               response[1], entity.eid))
                else:
                    from_file = entity.upload_files[0].get_file_path()
                    to_file = u'{0}/{1}/{2}/{3}'.format(
                        validated_dir, tp, centre, sid)
                    if not os.path.exists(to_file):
                        os.makedirs(to_file)
                    to_file = to_file + "/{}".format(
                        entity.upload_files[0].data_name)
                    shutil.copy2(from_file, to_file)
                    sha1 = unicode(
                        hashlib.sha1(open(to_file, 'rb').read()).hexdigest())
                    if sha1 == entity.upload_files[0].data_sha1hex:
                        os.remove(from_file)
                        os.symlink(to_file, from_file)
                        logger.info(
                            ("Copy from '{}' to '{}'"
                             ", delete and create symlink".format(
                                 from_file, to_file)))
                    else:
                        logger.critical(
                            "Incorrect copy from '{}' to '{}'".format(
                                from_file, to_file))
                    rql = ("SET X status 'Validated'"
                           " WHERE X is CWUpload, X eid '{}'".format(
                               entity.eid))
                cati.set_done(entity.upload_files[0].data_name)
                cnx.execute(rql)
            except:
                stacktrace = traceback.format_exc()
                stacktrace = stacktrace.replace('"', "'").replace("'", "\\'")
                logger.critical("A system error raised")
                rql = ("SET X status 'Rejected', X error '{} <br/> {}'"
                       " WHERE X is CWUpload, X eid '{}'".format(
                           SYSTEM_ERROR_RAISED,
                           stacktrace,
                           entity.eid))
                cnx.execute(rql)
        cnx.commit()
