# -*- coding: utf-8 -*-

# Copyright (c) 2014-2016 CEA
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

"""cubicweb-imagen-upload specific hooks and operations"""

from cubicweb.server.hook import Hook


class ServerStartupHook(Hook):
    """
        Update repository cache with groups from indexation to ease LDAP
        synchronisation
    """
    __regid__ = 'imagen.update_cache_hook'
    events = ('server_startup', 'server_maintenance')

    def __call__(self):
        # get session

        # update repository cache
        with self.repo.internal_cnx() as cnx:
            rset = cnx.execute("Any X WHERE X is CWGroup")
            for egroup in rset.entities():
                if egroup.name in ["guests", "managers", "users", "owners"]:
                    continue
                self.repo._extid_cache[
                    'cn={0},ou=Groups,dc=imagen2,dc=cea,dc=fr'.format(
                        egroup.name)] = egroup.eid
