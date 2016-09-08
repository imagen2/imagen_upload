# -*- coding: utf-8 -*-
##########################################################################
# NSAp - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from datetime import datetime
import os

LOGGER = None
CATI_WORFLOW_DIRECTORY = None
SENT_FILE = 'sent.csv'
RESPONSE_FILE = 'response.csv'
DONE_FILE = 'done.csv'
LINE_SEP = '\n'
COL_SEP = ';'


##############################################################################
def is_system_OK():
    """ Return True if all needs files are readable and writable, otherwise
        log the missing permissions and return False.
    """

    # check root directory
    if not os.path.exists(CATI_WORFLOW_DIRECTORY):
        os.makedirs(CATI_WORFLOW_DIRECTORY)
    # check sent, response and done files (exists, readable, writable)
    paths = [
        get_sent_file_path(),
        get_response_file_path(),
        get_done_file_path()
    ]
    message = ''
    for path in paths:
        if not os.access(path, os.F_OK):
            open(path, 'a').close()
        if not os.access(path, os.R_OK):
            message += "{} has not read access.\n".format(path)
        if not os.access(path, os.W_OK):
            message += "{} has not write access.\n".format(path)

   # log and return
    if message != '':
        LOGGER.critical(message)
        return False
    else:
        return True


##############################################################################
def get_sent_file_path():
    """ Build and return the file path containing the list of sent files """

    return "{0}/{1}".format(CATI_WORFLOW_DIRECTORY, SENT_FILE)


##############################################################################
def get_response_file_path():
    """ Build and return the file path containing the list of cati responses.
    """

    return "{0}/{1}".format(CATI_WORFLOW_DIRECTORY, RESPONSE_FILE)


##############################################################################
def get_done_file_path():
    """ Build and return the file path containing
        the list of done files (sent and response).
    """

    return "{0}/{1}".format(CATI_WORFLOW_DIRECTORY, DONE_FILE)


##############################################################################
def read_sent_file():
    """ Read the file containing the list of sent files and return
        a dictionnary with :
        - sent file name as key
        - sent time as value
        The row file format is 2 values separated by the COL_SEP value
        and endding by the LINE_SEP value.
    """

    sent = {}
    lines = [line.rstrip(LINE_SEP) for line in open(get_sent_file_path())]
    for line in lines:
        split = line.split(COL_SEP)
        sent[split[0]] = split[1]
    return sent


##############################################################################
def read_response_file():
    """ Read the file containing the list of cati responses return
        a dictionnary with :
        - sent file name as key
        - status and optionnal rejected message as value.
        The status values must be 'Rejected' or 'Validated'.
        The row file format is 2 or 3 values separated by the COL_SEP value
        and endding by the LINE_SEP value.
    """
    responses = {}

    lines = [line.rstrip(LINE_SEP) for line in open(get_response_file_path())]
    for line in lines:
        split = line.split(COL_SEP, 1)
        responses[split[0]] = split[1]
    return responses


##############################################################################
def has_sent(entry):
    """ Return True if entry sent, False otherwize.

    Pameters:
        entry: Representing the file name
    """

    sent = read_sent_file()
    return entry in sent.keys()


##############################################################################
def get_response(entry):
    """ Return a list containing status and optionnal rejected message,
        None otherwise.,

    Pameters:
        entry: Representing the file name
    """
    responses = read_response_file()
    if not entry in responses.keys():
        return None
    else:
        return responses[entry].split(COL_SEP)


##############################################################################
def add_sent(entry):
    """ Add an entry and time
        in the file containing the list of sent entries

    Pameters:
        entry: Representing the file name
    """
    if not has_sent(entry):
        with open(get_sent_file_path(), 'a') as sentfile:
            sentfile.write("{0}{1}{2}{3}".format(
                entry, COL_SEP, datetime.now(), LINE_SEP)
            )


##############################################################################
def send_file_by_sftp(filepath, fields):
    print 'cati.send_file_by_sftp NOT IMPLEMENTED'


##############################################################################
def send_entry(entry, filepath, fields):
    """ Send the file reprensenting by filepath to cati repository

    Pameters:
        entry: Representing the file name
        filepath: the file to send (path and file name generated by cubicweb)
        fields: dictionnary of upload fields
    """

    if not has_sent(entry):
        try:
            send_file_by_sftp(filepath, fields)
            add_sent(entry)
            LOGGER.info("{} sent to cati".format(entry))
        except BaseException as e:
            LOGGER.critical("{} not sent to cati cause {}".format(entry, e))


##############################################################################
def set_done(entry):
    """ Add to the done entries file the entry with sent time and response.
        Remove also entry in sent and response files

    Pameters:
        entry: Representing the file name
    """

    sent = read_sent_file()
    responses = read_response_file()
    if entry in sent.keys() and entry in responses.keys():
        with open(get_done_file_path(), 'a') as entryfile:
            entryfile.write("{0}{1}{2}{3}{4}{5}{6}{7}".format(
                datetime.now(), COL_SEP,
                entry, COL_SEP,
                sent[entry], COL_SEP,
                responses[entry], LINE_SEP)
            )
        value = sent.pop(entry)
        with open(get_sent_file_path(), 'w') as entryfile:
            for key, value in sent.items():
                entryfile.write("{0}{1}{2}{3}".format(
                    entry, COL_SEP, value, LINE_SEP)
                )
        value = responses.pop(entry)
        with open(get_response_file_path(), 'w') as entryfile:
            for key, value in sent.items():
                entryfile.write("{0}{1}{2}{3}".format(
                    entry, COL_SEP, value, LINE_SEP)
                )
