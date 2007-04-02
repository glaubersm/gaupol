# Copyright (C) 2005-2007 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# Gaupol is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Gaupol; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301, USA.


"""Decorators for testing methods and functions."""


import copy
import functools
import time


def benchmark(function):
    """Decorator for benchmarking functions and methods."""

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        a = time.time()
        value = function(*args, **kwargs)
        z = time.time()
        print "%.3f %s" % (z - a, function.__name__)
        return value

    return wrapper

def reversion_test(function):
    """Decorator for testing reversions of one action."""

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        project = args[0].project
        data = (
            project.times,
            project.frames,
            project.main_texts,
            project.tran_texts,)
        a = copy.deepcopy(data)
        value = function(*args, **kwargs)
        z = copy.deepcopy(data)
        assert z != a
        for i in range(2):
            project.undo()
            assert data == a
            project.redo()
            assert data == z
        return value

    return wrapper
