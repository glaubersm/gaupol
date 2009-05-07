# Copyright (C) 2007-2008 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Gaupol is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Gaupol. If not, see <http://www.gnu.org/licenses/>.

"""Manager of regular expression substitutions for subtitle texts."""

import gaupol
import os
import re
import xml.etree.ElementTree as ET

__all__ = ("PatternManager",)


class PatternManager(object):

    """Manager of regular expression substitutions for subtitle texts.

    Instance variables:
     * pattern_type: String to indentify what the pattern matches
     * _patterns: Dictionary mapping codes to pattern lists

    pattern_type should be a string with value 'line-break', 'common-error',
    'capitalization' or 'hearing-impaired'. Codes are of form
    Script[-language-[COUNTRY]] using the corresponding ISO codes.
    """

    __metaclass__ = gaupol.Contractual
    _re_comment = re.compile(r"^\s*#.*$")

    def __init___require(self, pattern_type):
        types = ("line-break", "common-error",
            "capitalization", "hearing-impaired")
        assert pattern_type in types

    def __init__(self, pattern_type):
        """Initialize a PatternManager object."""

        self.pattern_type = pattern_type
        self._patterns = {}
        self._read_patterns()

    def _assert_indentifiers(self, script, language, country):
        """Assert that codes are valid and parents are defined."""

        if script is not None:
            assert gaupol.scripts.is_valid(script)
        if language is not None:
            assert script is not None
            assert gaupol.languages.is_valid(language)
        if country is not None:
            assert language is not None
            assert gaupol.countries.is_valid(country)

    def _filter_patterns(self, patterns):
        """Return patterns with name-clashes resolved.

        Patterns with a more specific code replace those with a less specific
        code if they have the same name and the more specific pattern's policy
        is explicitly set to 'Replace' (instead of the implicit 'Append').
        """
        filtered_patterns = []
        for i, pattern in enumerate(patterns):
            replacement_found = False
            name = pattern.get_name(False)
            for j in range(i + 1, len(patterns)):
                j_name = patterns[j].get_name(False)
                j_policy = patterns[j].get_field("Policy")
                if (j_name == name) and (j_policy == "Replace"):
                    replacement_found = True
            if not replacement_found:
                filtered_patterns.append(pattern)
        return filtered_patterns

    def _get_codes_require(self, script=None, language=None, country=None):
        self._assert_indentifiers(script, language, country)

    def _get_codes(self, script=None, language=None, country=None):
        """Return a sequence of all codes to be used by arguments.

        Zyyy is the first code and the most specific one last.
        """
        codes = ["Zyyy"]
        if script is not None:
            codes.append(script)
        if language is not None:
            code = "%s-%s" % (script, language)
            codes.append(code)
        if country is not None:
            code = "%s-%s" % (code, country)
            codes.append(code)
        return tuple(codes)

    def _read_config_from_directory_require(self, directory, encoding):
        assert gaupol.encodings.is_valid_code(encoding)

    def _read_config_from_directory(self, directory, encoding):
        """Read configurations from files in directory."""

        if not os.path.isdir(directory): return
        extension = ".%s.conf" % self.pattern_type
        files = os.listdir(directory)
        for name in (x for x in files if x.endswith(extension)):
            path = os.path.join(directory, name)
            self._read_config_from_file(path, encoding)

    def _read_config_from_file_require(self, path, encoding):
        assert gaupol.encodings.is_valid_code(encoding)

    def _read_config_from_file(self, path, encoding):
        """Read configurations from file."""

        if not os.path.isfile(path): return
        basename = os.path.basename(path)
        extension = ".%s.conf" % self.pattern_type
        code = basename.replace(extension, "")
        if not code in self._patterns: return
        patterns = self._patterns[code]
        for element in ET.parse(path).findall("pattern"):
            name = unicode(element.get("name"))
            name = name.replace("&quot;", '"')
            name = name.replace("&amp;", "&")
            enabled = (element.get("enabled") == "true")
            for pattern in patterns:
                if pattern.get_name(False) == name:
                    pattern.enabled = enabled

    def _read_patterns(self):
        """Read all patterns of self.pattern_type from files."""

        data_dir = os.path.join(gaupol.DATA_DIR, "patterns")
        data_home_dir = os.path.join(gaupol.DATA_HOME_DIR, "patterns")
        config_home_dir = os.path.join(gaupol.CONFIG_HOME_DIR, "patterns")
        encoding = gaupol.util.get_default_encoding()
        self._read_patterns_from_directory(data_dir, "utf_8")
        self._read_patterns_from_directory(data_home_dir, encoding)
        self._read_config_from_directory(data_dir, "utf_8")
        self._read_config_from_directory(config_home_dir, encoding)

    def _read_patterns_from_directory_require(self, directory, encoding):
        assert gaupol.encodings.is_valid_code(encoding)

    def _read_patterns_from_directory(self, directory, encoding):
        """Read all patterns from files in directory."""

        if not os.path.isdir(directory): return
        extension = ".%s" % self.pattern_type
        extensions = (extension, "%s.in" % extension)
        files = os.listdir(directory)
        for name in (x for x in files if x.endswith(extensions)):
            path = os.path.join(directory, name)
            self._read_patterns_from_file(path, encoding)

    def _read_patterns_from_file_require(self, directory, encoding):
        assert gaupol.encodings.is_valid_code(encoding)

    def _read_patterns_from_file(self, path, encoding):
        """Read all patterns from file."""

        if not os.path.isfile(path): return
        basename = os.path.basename(path)
        extension = ".%s" % self.pattern_type
        if basename.endswith(".in"):
            extension = ".%s.in" % self.pattern_type
        code = basename.replace(extension, "")
        local = path.startswith(gaupol.DATA_HOME_DIR)
        patterns = self._patterns.setdefault(code, [])
        lines = gaupol.util.readlines(path, encoding)
        lines = [self._re_comment.sub("", x) for x in lines]
        lines = [x.strip() for x in lines]
        for line in (x for x in lines if x):
            if line.startswith("["): # [HEADER]
                patterns.append(gaupol.Pattern())
                patterns[-1].local = local
            else: # KEY=VALUE. Discard possible leading underscore.
                name, value = unicode(line).split("=", 1)
                name = (name[1:] if name.startswith("_") else name)
                patterns[-1].set_field(name, value)

    def _write_config_to_file(self, code, encoding):
        """Write configurations of all patterns to file."""

        local_dir = os.path.join(gaupol.CONFIG_HOME_DIR, "patterns")
        if not os.path.isdir(local_dir): return
        basename = "%s.%s.conf" % (code, self.pattern_type)
        path = os.path.join(local_dir, basename)
        text = '<?xml version="1.0" encoding="utf-8"?>'
        text += '%s<patterns>%s' % (os.linesep, os.linesep)
        written_names = set(())
        for pattern in self._patterns[code]:
            name = pattern.get_name(False)
            if name in written_names: continue
            written_names.add(name)
            name = name.replace("&", "&amp;")
            name = name.replace('"', "&quot;")
            enabled = ("false", "true")[pattern.enabled]
            text += '  <pattern name="%s" ' % name
            text += 'enabled="%s"/>' % enabled
            text += os.linesep
        text += "</patterns>%s" % os.linesep
        gaupol.util.write(path, text, encoding)

    def get_countries(self, script, language):
        """Return a sequence of countries for which patterns exist."""

        codes = self._patterns.keys()
        start = "%s-%s-" % (script, language)
        codes = [x for x in codes if x.startswith(start)]
        countries = [x.split("-")[2] for x in codes]
        return tuple(gaupol.util.get_unique(countries))

    def get_languages(self, script):
        """Return a sequence of languages for which patterns exist."""

        codes = self._patterns.keys()
        start = "%s-" % script
        codes = [x for x in codes if x.startswith(start)]
        languages = [x.split("-")[1] for x in codes]
        return tuple(gaupol.util.get_unique(languages))

    def get_patterns_require(self, script=None, language=None, country=None):
        self._assert_indentifiers(script, language, country)

    def get_patterns(self, script=None, language=None, country=None):
        """Return patterns for script, language and country."""

        patterns = []
        for code in self._get_codes(script, language, country):
            for pattern in self._patterns.get(code, []):
                patterns.append(pattern)
        patterns = self._filter_patterns(patterns)
        return patterns

    def get_scripts(self):
        """Return a sequence of scripts for which patterns exist."""

        codes = self._patterns.keys()
        while "Zyyy" in codes:
            codes.remove("Zyyy")
        scripts = [x.split("-")[0] for x in codes]
        return tuple(gaupol.util.get_unique(scripts))

    def save_config_require(self, script=None, language=None, country=None):
        self._assert_indentifiers(script, language, country)

    def save_config(self, script=None, language=None, country=None):
        """Save pattern configurations to files."""

        local_dir = os.path.join(gaupol.CONFIG_HOME_DIR, "patterns")
        gaupol.deco.silent(OSError)(gaupol.util.makedirs)(local_dir)
        encoding = gaupol.util.get_default_encoding()
        codes = self._get_codes(script, language, country)
        for code in (x for x in codes if x in self._patterns):
            self._write_config_to_file(code, "utf_8")
