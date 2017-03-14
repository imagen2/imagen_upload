# -*- coding: utf-8 -*-

# Copyright (c) 2017 CEA
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

# CW imports
from cubicweb.web.views.startup import IndexView

# Cubes import
from cubes.piws.views.startup import PIWSIndexView


class IMAGENIndexView(IndexView):
    """ Class that defines the piws index view.
    """

    def call(self, **kwargs):
        """ Create the 'index' like page of our site.
        """
        # Get the card that contains some text description about this site
        self.w(u"<h2>Welcome to the Imagen follow-up 3 upload portal<h2>")
        rset = self._cw.execute("Any X WHERE X is Card, X title 'index'")


def registration_callback(vreg):
    vreg.register_and_replace(IMAGENIndexView, PIWSIndexView)
