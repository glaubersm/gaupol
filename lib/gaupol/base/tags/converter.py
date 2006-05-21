# Copyright (C) 2005 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gaupol is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gaupol; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Conversions between tags of different subtitle formats."""


try:
    from psyco.classes import *
except ImportError:
    pass

import re

from gaupol.base.tags.classes import *
from gaupol.constants         import Format


class TagConverter(object):

    """
    Conversions between tags of different subtitle formats.

    Tag conversions are done via an internal format, which has a HTML style
    syntax. All essential tags are converted and troublesome tags, such as
    position, and rare tags are removed.
    """

    def __init__(self, from_format, to_format):

        self._from_regexs = []
        self._to_regexs   = []

        from_format_name = Format.CLASS_NAMES[from_format]
        to_format_name   = Format.CLASS_NAMES[  to_format]

        # Regular expression patterns
        from_tags = eval(from_format_name).decode_tags
        to_tags   = eval(  to_format_name).encode_tags

        PATTERN, FLAGS, REPL, COUNT = 0, 1, 2, 3

        # Compile regular expressions.
        for entry in from_tags:
            regex = re.compile(entry[PATTERN], entry[FLAGS])
            try:
                count = entry[COUNT]
            except IndexError:
                count = 1
            self._from_regexs.append([regex, entry[REPL], count])
        for entry in to_tags:
            regex = re.compile(entry[PATTERN], entry[FLAGS])
            try:
                count = entry[COUNT]
            except IndexError:
                count = 1
            self._to_regexs.append([regex, entry[REPL], count])

        # Arbitrary functions
        self._pre_decode  = eval(from_format_name).pre_decode
        self._post_decode = eval(from_format_name).post_decode
        self._pre_encode  = eval(to_format_name).pre_encode
        self._post_encode = eval(to_format_name).post_encode

    def convert_tags(self, text):
        """Convert subtitle tags in text."""

        if not text:
            return text

        REGEX, REPL, COUNT = 0, 1, 2

        # Convert to internal format ("decode").
        text = self._pre_decode(text)
        for entry in self._from_regexs:
            for i in range(entry[COUNT]):
                text = entry[REGEX].sub(entry[REPL], text)
        text = self._post_decode(text)

        # Convert to desired format ("encode").
        text = self._pre_encode(text)
        for entry in self._to_regexs:
            for i in range(entry[COUNT]):
                text = entry[REGEX].sub(entry[REPL], text)
        text = self._post_encode(text)

        return text


if __name__ == '__main__':

    from gaupol.test import Test

    class TestTagConverter(Test):

        def test_micro_dvd_to_subrip(self):

            converter = TagConverter(Format.MICRODVD, Format.SUBRIP)

            original = '{y:biu}Whenever there are famines,\n' \
                       'people will have problems.'
            result   = '<b><i><u>Whenever there are famines,</u></i></b>\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

            original = '{Y:i}Whenever there are famines,\n' \
                       'people will have problems.'
            result   = '<i>Whenever there are famines,\n' \
                       'people will have problems.</i>'
            assert converter.convert_tags(original) == result

            original = '{c:$rrggbb}Whenever there are famines,\n' \
                       'people will have problems.'
            result   = 'Whenever there are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

        def test_subrip_to_micro_dvd(self):

            converter = TagConverter(Format.SUBRIP, Format.MICRODVD)

            original = '<i>Whenever there are famines,</i>'
            result   = '{Y:i}Whenever there are famines,'
            assert converter.convert_tags(original) == result

            original = '<i>Whenever</i> there are famines,'
            result   = '{y:i}Whenever there are famines,'
            assert converter.convert_tags(original) == result

            original = '<i>Whenever there are famines,</i>\n' \
                       '<i>people will have problems.</i>'
            result   = '{Y:i}Whenever there are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

        def test_mpl2_to_subrip(self):

            converter = TagConverter(Format.MPL2, Format.SUBRIP)

            original = '/Whenever there are famines,\n' \
                       '/people will have problems.'
            result   = '<i>Whenever there are famines,</i>\n' \
                       '<i>people will have problems.</i>'
            assert converter.convert_tags(original) == result

            original = '_Whenever there are famines,\n' \
                       'people will have problems.'
            result   = '<u>Whenever there are famines,</u>\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

        def test_ssa_to_micro_dvd(self):

            converter = TagConverter(Format.SSA, Format.MICRODVD)

            original = '{\\i1}Whenever{\\r} there are famines,\n' \
                       '{\\c&Hffffff&}people will have problems.'
            result   = '{y:i}Whenever there are famines,\n' \
                       '{c:$ffffff}people will have problems.'
            assert converter.convert_tags(original) == result

            original = '{\\i1\\b1\\fs12}Whenever{\\r} there are famines,\n' \
                       'people will have problems.'
            result   = '{y:i}{y:b}{s:12}Whenever there are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

        def test_ssa_to_subrip(self):

            converter = TagConverter(Format.SSA, Format.SUBRIP)

            original = '{\\i1}Whenever{\\r} there are famines,\n' \
                       '{\\c&Hffffff&}people will have problems.'
            result   = '<i>Whenever</i> there are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

            original = '{\\b200}Whenever there{\\b0} are famines,\n' \
                       'people will have problems.'
            result   = '<b>Whenever there</b> are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

        def test_subrip_to_mpl2(self):

            converter = TagConverter(Format.SUBRIP, Format.MPL2)

            original = '<i>Whenever there are famines,</i>\n' \
                       '<i>people will have problems.</i>'
            result   = '/Whenever there are famines,\n' \
                       '/people will have problems.'
            assert converter.convert_tags(original) == result

            original = '<b>Whenever there are famines,</b>\n' \
                       'people will have problems.'
            result   = '\\Whenever there are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

        def test_subrip_to_ssa(self):

            converter = TagConverter(Format.SUBRIP, Format.SSA)

            original = '<i>Whenever there are famines,</i>\n' \
                       '<i>people will have problems.</i>'
            result   = '{\\i1}Whenever there are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

            converter = TagConverter(Format.SUBRIP, Format.ASS)

            original = '<i>Whenever</i> there are famines,\n' \
                       'people will have problems.'
            result   = '{\\i1}Whenever{\\i0} there are famines,\n' \
                       'people will have problems.'
            assert converter.convert_tags(original) == result

    TestTagConverter().run()
