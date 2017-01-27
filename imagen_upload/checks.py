# -*- coding: utf-8 -*-

# Copyright (c) 2016-2017 CEA
#
# This software is governed by the CeCILL license under French law and
# abiding by the rules of distribution of free software. You can use,
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty and the software's author, the holder of the
# economic rights, and the successive licensors have only limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading, using, modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean that it is complicated to manipulate, and that also
# therefore means that it is reserved for developers and experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and, more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.

import hashlib
import os
import re
import shutil
import traceback

from cubes.rql_upload.tools import get_or_create_logger
from imagen.sanity import cantab, imaging
from imagen import (MID_CSV, FT_CSV, SS_CSV, RECOG_CSV)
from imagen import (SEQUENCE_LOCALIZER_CALIBRATION,
                    SEQUENCE_T2, SEQUENCE_T2_FLAIR,
                    SEQUENCE_ADNI_MPRAGE,
                    SEQUENCE_MID, SEQUENCE_FT, SEQUENCE_SST,
                    SEQUENCE_B0_MAP, SEQUENCE_DTI,
                    SEQUENCE_RESTING_STATE)
from . import cati

VALIDATED_ADD_PATH_AFTER_TP = os.path.join('RAW', 'PSC1')

SID_ERROR_MESSAGE = ("<dl><dt>The subject ID is malformed.</dt>"
                     "<dd>12 decimal digits required.</dd></dl>")

UPLOAD_ALREADY_EXISTS = ("<dl><dt>A similar upload already exists.</dt>"
                         "<dd>Same subject ID and time point,"
                         " and upload not rejected.</dd>"
                         "<dd>Please contact an administrator if you want"
                         " to force the upload.</dd></dl>")

SYSTEM_ERROR_RAISED = ("<dl><dt>A system error raised.</dt>"
                       "<dd> Please send the following message"
                       " to imagendatabase@cea.fr.</dd></dl>")


def get_message_error(errors, filename, pattern, filepath):
    """ Generate a message error from error list regarding an uploaded file.


    Parameters:
        errors: error list
        filename: file name provide by user during upload
        pattern: pattern expected for file name
        filepath: file path used by CW for uploaded file
    """

    message = ''
    if errors:
        message += u'<dl>'
        message += u'<dt>File {} [{}]<dt>'.format(filename, pattern)
        for err in errors:
            message += u'<dd>'
            message += err.message
            if err.path and err.path != filename and err.path != filepath and err.path != os.path.basename(filepath):
                message += u' [{}]'.format(err.path)
            if err.sample:
                sample = repr(err.sample)
                if len(sample) > err._SAMPLE_LEN:
                    sample = sample[:err._SAMPLE_LEN] + '...'
                message += u' [{}]'.format(sample)
            message += u'</dd>'
        message += u'</dl>'
    return message.replace(os.path.basename(filepath), filename)


def is_PSC1(value):
    """ Checks if value is well-formatted (12 decimal digits)

    Parameters:
        value: PSC1 code.

    Return:
        Return True if value matches the pattern, False otherwise.
    """
    if re.match("^\d{12}$", value) is None:
        return False
    else:
        return True


def is_aldready_uploaded(connexion, posted, formname, uid):
    """ Checks if an equivalent upload is already done.
        To be equivalent an upload must have:
            a status different than 'Rejected' and
            an uploadfield with equal SID and
            an uploadfield with equal TIME_POINT

    Parameters:
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

    Parameters:
        connexion: connexion use to query
        posted: dictionnary of form posted fields
        upload: CWUpload entity
        files: UploafFile entities
        fields: UploafField entities

    Return:
        Return None if checks pass, error message otherwise
    """

    message = ''

    sid = posted['sid']
    tid = posted['time_point']
    date = posted['acquisition_date']

    # checks
    if not is_PSC1(sid):
        message += SID_ERROR_MESSAGE
    if is_aldready_uploaded(connexion, posted, upload.form_name, upload.eid):
        message += UPLOAD_ALREADY_EXISTS

    # Dimitri's sanity check
    psc1 = True
    errors = None
    for ufile in files:
        if ufile.name == 'cant':
            psc1, errors = cantab.check_cant_name(
                ufile.data_name, tid, sid)
            message += get_message_error(
                errors, ufile.data_name,
                u'cant_&lt;PSC1&gt;&lt;TP&gt;.cclar', ufile.data_name)
            filepath = ufile.get_file_path()
            psc1, errors = cantab.check_cant_content(filepath, tid, sid, date)
            message += get_message_error(
                errors, ufile.data_name,
                u'cant_&lt;PSC1&gt;&lt;TP&gt;.cclar', filepath)
        elif ufile.name == 'datasheet':
            psc1, errors = cantab.check_datasheet_name(
                ufile.data_name, tid, sid)
            message += get_message_error(
                errors, ufile.data_name,
                u'datasheet_&lt;PSC1&gt;&lt;TP&gt;.csv', ufile.data_name)
            filepath = ufile.get_file_path()
            psc1, errors = cantab.check_datasheet_content(
                filepath, tid, sid, date)
            message += get_message_error(
                errors, ufile.data_name,
                u'datasheet_&lt;PSC1&gt;&lt;TP&gt;.csv', filepath)
        elif ufile.name == 'detailed_datasheet':
            psc1, errors = cantab.check_detailed_datasheet_name(
                ufile.data_name, tid, sid)
            message += get_message_error(
                errors, ufile.data_name,
                u'detailed_datafunctionsheet_&lt;PSC1&gt;&lt;TP&gt;.csv',
                ufile.data_name)
            filepath = ufile.get_file_path()
            psc1, errors = cantab.check_detailed_datasheet_content(
                filepath, tid, sid, date)
            message += get_message_error(
                errors, ufile.data_name,
                u'detailed_datasheet_&lt;PSC1&gt;&lt;TP&gt;.csv', filepath)
        elif ufile.name == 'report':
            psc1, errors = cantab.check_report_name(
                ufile.data_name, tid, sid)
            message += get_message_error(
                errors, ufile.data_name,
                u'report_&lt;PSC1&gt;&lt;TP&gt;.html', ufile.data_name)
            filepath = ufile.get_file_path()
            psc1, errors = cantab.check_report_content(
                filepath, tid, sid, date)
            message += get_message_error(
                errors, ufile.data_name,
                u'report_&lt;PSC1&gt;&lt;TP&gt;.html', filepath)

    # return
    if message:
        return message
    else:
        return None


def asynchrone_check_cantab(repository):
    """ Copy uploaded cantab files from 'upload_dir' to 'validated_dir/...'
        and set status 'validated'

    Parameters:
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
                    to_file = os.path.join(validated_dir,
                                           tp, VALIDATED_ADD_PATH_AFTER_TP,
                                           centre, sid)
                    if not os.path.exists(to_file):
                        os.makedirs(to_file)
                    to_file = os.path.join(to_file, eUFile.data_name)
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

    Parameters:
        connexion: connexion use to query
        posted: dictionnary of form posted fields
        upload: CWUpload entity
        files: UploafFile entities
        fields: UploafField entities
    Return:
        Return None if checks pass, error message otherwise
    """

    message = ''

    sid = posted['sid']
    tid = posted['time_point']
    date = posted['acquisition_date']
    expected = {
        SEQUENCE_T2: posted['t2'],
        SEQUENCE_T2_FLAIR: posted['flair'],
        SEQUENCE_ADNI_MPRAGE: posted['adni_mprage'],
        SEQUENCE_MID: posted['mid'],
        MID_CSV: posted['mid'],
        SEQUENCE_FT: posted['ft'],
        FT_CSV: posted['ft'],
        SEQUENCE_SST: posted['ss'],
        SS_CSV: posted['ss'],
        SEQUENCE_B0_MAP: posted['b0'],
        SEQUENCE_DTI: posted['dti'],
        SEQUENCE_RESTING_STATE: posted['rs'],
        RECOG_CSV: posted['recog'],
    }

    # checks
    if not is_PSC1(sid):
        message += SID_ERROR_MESSAGE
    if is_aldready_uploaded(connexion, posted, upload.form_name, upload.eid):
        message += UPLOAD_ALREADY_EXISTS

    # Dimitri's sanity check
    psc1 = True
    errors = None
    filepath = files[0].get_file_path()
    psc1, errors = imaging.check_zip_name(files[0].data_name, tid, sid)
    message += get_message_error(
        errors, files[0].data_name,
        u'&lt;PSC1&gt;&lt;TP&gt;.zip', files[0].data_name)
    psc1, errors = imaging.check_zip_content(filepath, tid, sid, date, expected)
    message += get_message_error(
        errors, files[0].data_name,
        u'&lt;PSC1&gt;&lt;TP&gt;.zip', filepath)

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

    Parameters:
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
                    to_file = os.path.join(validated_dir,
                                           tp, VALIDATED_ADD_PATH_AFTER_TP,
                                           centre, sid)
                    if not os.path.exists(to_file):
                        os.makedirs(to_file)
                    to_file = os.path.join(to_file, entity.upload_files[0].data_name)
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
