# Copyright (C) 2005 Osmo Salomaa
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


"""Editing subtitle data."""


try:
    from psyco.classes import *
except ImportError:
    pass

from gettext import gettext as _
import bisect

from gaupol.base.colcons import *
from gaupol.base.delegates    import Delegate
from gaupol.base.cons         import Action, Document, Framerate, Mode


class EditDelegate(Delegate):

    """Editing subtitle data."""

    def clear_texts(self, rows, document, register=Action.DO):
        """Clear texts."""

        new_texts = [u''] * len(rows)
        self.replace_texts(rows, document, new_texts, register)
        self.set_action_description(register, _('Clearing texts'))

    def copy_texts(self, rows, document):
        """Copy texts to the clipboard."""

        start_row = min(rows)
        end_row   = max(rows)
        texts = (self.main_texts, self.tran_texts)[document]

        data = []
        for row in range(start_row, end_row + 1):
            if row in rows:
                data.append(texts[row])
            else:
                data.append(None)

        self.clipboard.data = data

    def cut_texts(self, rows, document, register=Action.DO):
        """Cut texts to the clipboard."""

        self.copy_texts(rows, document)
        self.clear_texts(rows, document, register)
        self.set_action_description(register, _('Cutting texts'))

    def get_mode(self):
        """
        Get main file's mode.

        If main file does not exist, return time mode. Due to its greater
        accuracy, time mode is the preferred mode for new documents.
        """
        try:
            return self.main_file.mode
        except AttributeError:
            return Mode.TIME

    def get_needs_resort(self, row, show_value):
        """Return True if rows need resorting after changing show value."""

        mode       = self.get_mode()
        positions = self.get_positions()

        # Convert show_value to same type as mode.
        try:
            show_value = int(show_value)
        except ValueError:
            if mode == Mode.FRAME:
                show_value = self.calc.time_to_frame(show_value)
        else:
            if mode == Mode.TIME:
                show_value = self.calc.frame_to_time(show_value)

        # Get new row.
        lst = positions[:row] + positions[row + 1:]
        item = [show_value] + positions[row][1:]
        new_row = bisect.bisect_right(lst, item)
        return bool(new_row != row)

    def get_positions(self):
        """Return either times or frames depending on main file's mode."""

        mode = self.get_mode()
        if mode == Mode.TIME:
            return self.times
        elif mode == Mode.FRAME:
            return self.frames

    def _insert_blank(self, rows):
        """
        Insert blank subtitles.

        rows must be a single range.
        """
        times      = self.times
        frames     = self.frames
        main_texts = self.main_texts
        tran_texts = self.tran_texts
        calc       = self.calc
        mode       = self.get_mode()
        positions = self.get_positions()
        start_row  = min(rows)
        amount     = len(rows)

        # Optimal duration in seconds
        opt_sec = 3

        # Get the first show time or frame.
        if start_row > 0:
            start = positions[start_row - 1][HIDE]
            if mode == Mode.TIME:
                start = calc.time_to_seconds(start)
        else:
            start = 0

        # Get duration.
        if start_row < len(self.times):
            end = positions[start_row][SHOW]
            if mode == Mode.TIME:
                end = calc.time_to_seconds(end)
                duration = float(end - start) / float(amount)
            if mode == Mode.FRAME:
                duration = int((end - start) / amount)
        else:
            if mode == Mode.TIME:
                duration = opt_sec
            if mode == Mode.FRAME:
                fr_value = Framerate.values[self.framerate]
                duration = int(round(fr_value * opt_sec, 0))

        if mode == Mode.TIME:
            for i in range(amount):

                show_time = calc.seconds_to_time(start + ( i      * duration))
                hide_time = calc.seconds_to_time(start + ((i + 1) * duration))
                durn_time = calc.get_time_duration(show_time, hide_time)

                show_frame = calc.time_to_frame(show_time)
                hide_frame = calc.time_to_frame(hide_time)
                durn_frame = calc.get_frame_duration(show_frame, hide_frame)

                row = start_row + i
                times.insert(row, [show_time, hide_time, durn_time])
                frames.insert(row, [show_frame, hide_frame, durn_frame])
                main_texts.insert(row, u'')
                tran_texts.insert(row, u'')

        elif mode == Mode.FRAME:
            for i in range(amount):

                show_frame = start + ( i      * duration)
                hide_frame = start + ((i + 1) * duration)
                durn_frame = calc.get_frame_duration(show_frame, hide_frame)

                show_time = calc.frame_to_time(show_frame)
                hide_time = calc.frame_to_time(hide_frame)
                durn_time = calc.get_time_duration(show_time, hide_time)

                row = start_row + i
                times.insert(row, [show_time, hide_time, durn_time])
                frames.insert(row, [show_frame, hide_frame, durn_frame])
                main_texts.insert(row, u'')
                tran_texts.insert(row, u'')

    def _insert_data(self, rows, times, frames, main_texts, tran_texts):
        """
        Insert subtitles with data.

        rows, times, frames, main_texts and tran_texts must all have the same
        length. subtitles are inserted in ascending order by simply inserting
        elements of data in positions defined by elements of rows. This means
        that the addition of subtitles must be taken into account beforehand in
        the "rows" argument. Data is not resorted, so this method must be
        called with ordered show times.
        """
        for i, row in enumerate(rows):
            self.times.insert(row, times[i])
            self.frames.insert(row, frames[i])
            self.main_texts.insert(row, main_texts[i])
            self.tran_texts.insert(row, tran_texts[i])

    def insert_subtitles(self, rows, times=None, frames=None, main_texts=None,
                         tran_texts=None, register=Action.DO):
        """
        Insert subtitles.

        rows, times, frames, main_texts and tran_texts must all have the same
        length. subtitles are inserted in ascending order by simply inserting
        elements of data in positions defined by elements of rows. This means
        that the addition of subtitles must be taken into account beforehand in
        the "rows" argument.
        """
        rows = sorted(rows)

        if None in (times, frames, main_texts, tran_texts):
            self._insert_blank(rows)
        else:
            args = rows, times, frames, main_texts, tran_texts
            self._insert_data(*args)

        self.register_action(
            register=register,
            docs=[Document.MAIN, Document.TRAN],
            description=_('Inserting subtitles'),
            revert_method=self.remove_subtitles,
            revert_args=[rows],
            inserted_rows=rows,
        )

    def paste_texts(self, start_row, document, register=Action.DO):
        """
        Paste texts from the clipboard.

        Return rows that were pasted into.
        """
        data = self.clipboard.data

        # Add rows if needed.
        current_length = len(self.times)
        amount = len(data) - (current_length - start_row)
        if amount > 0:
            signal = self.get_signal(register)
            self.block(signal)
            rows = range(current_length, current_length + amount)
            self.insert_subtitles(rows, register=register)

        rows = []
        new_texts = []
        for i, value in enumerate(data):
            if value is not None:
                rows.append(start_row + i)
                new_texts.append(value)
        self.replace_texts(rows, document, new_texts, register)

        # Group actions if needed.
        description = _('Pasting texts')
        if amount > 0:
            self.unblock(signal)
            self.group_actions(register, 2, description)
        else:
            self.set_action_description(register, description)

        return rows

    def remove_subtitles(self, rows, register=Action.DO):
        """Remove subtitles."""

        times      = []
        frames     = []
        main_texts = []
        tran_texts = []

        rows = sorted(rows)
        for row in reversed(rows):
            times.insert(0, self.times.pop(row))
            frames.insert(0, self.frames.pop(row))
            main_texts.insert(0, self.main_texts.pop(row))
            tran_texts.insert(0, self.tran_texts.pop(row))

        self.register_action(
            register=register,
            docs=[Document.MAIN, Document.TRAN],
            description=_('Removing subtitles'),
            revert_method=self.insert_subtitles,
            revert_args=[rows, times, frames, main_texts, tran_texts],
            removed_rows=rows,
        )

    def replace_both_texts(self, rows, new_texts, register=Action.DO):
        """
        Replace texts in both documents' in rows with new_texts.

        rows: (main_rows, tran_rows)
        new_texts: (new_main_texts, new_tran_texts)
        """
        # FIX: Check if either is empty (or does it matter?)
        main_texts = self.main_texts
        tran_texts = self.tran_texts
        main_rows = rows[0]
        tran_rows = rows[1]
        orig_main_texts = []
        orig_tran_texts = []
        new_main_texts = new_texts[0]
        new_tran_texts = new_texts[1]

        for i, row in enumerate(main_rows):
            orig_main_texts.append(main_texts[row])
            main_texts[row] = new_main_texts[i]
        for i, row in enumerate(tran_rows):
            orig_tran_texts.append(tran_texts[row])
            tran_texts[row] = new_tran_texts[i]

        orig_texts = (orig_main_texts, orig_tran_texts)

        self.register_action(
            register=register,
            docs=[Document.MAIN, Document.TRAN],
            description=_('Replacing texts'),
            revert_method=self.replace_both_texts,
            revert_args=[rows, orig_texts],
            updated_main_texts=main_rows,
            updated_tran_texts=tran_rows
        )

    def replace_texts(self, rows, document, new_texts, register=Action.DO):
        """Replace texts in document's rows with new_texts."""

        if document == Document.MAIN:
            texts = self.main_texts
            updated_main_texts = rows
            updated_tran_texts = []
        elif document == Document.TRAN:
            texts = self.tran_texts
            updated_main_texts = []
            updated_tran_texts = rows

        orig_texts = []

        for i, row in enumerate(rows):
            orig_texts.append(texts[row])
            texts[row] = new_texts[i]

        self.register_action(
            register=register,
            docs=[document],
            description=_('Replacing texts'),
            revert_method=self.replace_texts,
            revert_args=[rows, document, orig_texts],
            updated_main_texts=updated_main_texts,
            updated_tran_texts=updated_tran_texts
        )

    def set_durations(self, row):
        """Set durations for row based on shows and hides."""

        show = self.times[row][SHOW]
        hide = self.times[row][HIDE]
        self.times[row][DURN] = self.calc.get_time_duration(show, hide)

        show = self.frames[row][SHOW]
        hide = self.frames[row][HIDE]
        self.frames[row][DURN] = self.calc.get_frame_duration(show, hide)

    def set_frame(self, row, col, value, register=Action.DO):
        """
        Set frame.

        Return new index of row.
        """
        orig_value = self.frames[row][col]
        if value == orig_value:
            return row

        # Avoid rounding errors by mode-dependent revert.
        if self.get_mode() == Mode.TIME:
            orig_value = self.times[row][col]
            revert_method = self.set_time
        elif self.get_mode() == Mode.FRAME:
            orig_value = self.frames[row][col]
            revert_method = self.set_frame

        updated_rows = []
        updated_positions = [row]
        revert_row = row

        self.frames[row][col] = value
        self.times[row][col]  = self.calc.frame_to_time(value)

        # Calculate affected data.
        if col in (SHOW, HIDE):
            self.set_durations(row)
        elif col == DURN:
            self.set_hides(row)

        # Resort if show frame changed.
        if col == SHOW:
            new_row = self._sort_data(row)
            if new_row != row:
                first_row = min(row, new_row)
                last_row  = max(row, new_row)
                updated_rows = range(first_row, last_row + 1)
                revert_row = new_row
                updated_positions = []

        self.register_action(
            register=register,
            docs=[Document.MAIN],
            description=_('Editing frame'),
            revert_method=revert_method,
            revert_args=[revert_row, col, orig_value],
            updated_rows=updated_rows,
            updated_positions=updated_positions,
        )

        return revert_row

    def set_hides(self, row):
        """Set hides for row based on shows and durations."""

        show = self.times[row][SHOW]
        durn = self.times[row][DURN]
        self.times[row][HIDE] = self.calc.add_times(show, durn)

        show = self.frames[row][SHOW]
        durn = self.frames[row][DURN]
        self.frames[row][HIDE] = show + durn

    def set_text(self, row, document, value, register=Action.DO):
        """Set text."""

        value = unicode(value)

        if document == Document.MAIN:
            orig_value = self.main_texts[row]
            self.main_texts[row] = value
            updated_main_texts = [row]
            updated_tran_texts = []
        elif document == Document.TRAN:
            orig_value = self.tran_texts[row]
            self.tran_texts[row] = value
            updated_main_texts = []
            updated_tran_texts = [row]

        if value == orig_value:
            return

        self.register_action(
            register=register,
            docs=[document],
            description=_('Editing text'),
            revert_method=self.set_text,
            revert_args=[row, document, orig_value],
            updated_main_texts=updated_main_texts,
            updated_tran_texts=updated_tran_texts
        )

    def set_time(self, row, col, value, register=Action.DO):
        """
        Set time.

        Return new index of row.
        """
        orig_value = self.times[row][col]
        if value == orig_value:
            return row

        # Avoid rounding errors by mode-dependent revert.
        if self.get_mode() == Mode.TIME:
            orig_value = self.times[row][col]
            revert_method = self.set_time
        elif self.get_mode() == Mode.FRAME:
            orig_value = self.frames[row][col]
            revert_method = self.set_frame

        updated_rows = []
        updated_positions = [row]
        revert_row = row

        self.times[row][col]  = value
        self.frames[row][col] = self.calc.time_to_frame(value)

        # Calculate affected data.
        if col in (SHOW, HIDE):
            self.set_durations(row)
        elif col == DURN:
            self.set_hides(row)

        # Resort if show frame changed.
        if col == SHOW:
            new_row = self._sort_data(row)
            if new_row != row:
                first_row = min(row, new_row)
                last_row  = max(row, new_row)
                updated_rows = range(first_row, last_row + 1)
                revert_row = new_row
                updated_positions = []

        self.register_action(
            register=register,
            docs=[Document.MAIN],
            description=_('Editing time'),
            revert_method=revert_method,
            revert_args=[revert_row, col, orig_value],
            updated_rows=updated_rows,
            updated_positions=updated_positions,
        )

        return revert_row

    def _sort_data(self, row):
        """
        Sort data after show value in row has changed.

        Return new index of row.
        """
        positions = self.get_positions()

        # Get new row.
        lst  = positions[:row] + positions[row + 1:]
        item = positions[row]
        new_row = bisect.bisect_right(lst, item)

        # Move data.
        if new_row != row:
            data = [
                self.times,
                self.frames,
                self.main_texts,
                self.tran_texts
            ]
            for entry in data:
                entry.insert(new_row, entry.pop(row))

        return new_row


if __name__ == '__main__':

    import copy
    from gaupol.test import Test

    class TestEditDelegate(Test):

        def __init__(self):

            Test.__init__(self)
            self.project = self.get_project()

        def test_clear_texts(self):

            orig_texts = self.project.main_texts[0:2]
            self.project.clear_texts([0, 1], Document.MAIN)
            assert self.project.main_texts[0] == ''
            assert self.project.main_texts[1] == ''

            self.project.undo()
            assert self.project.main_texts[0:2] == orig_texts

        def test_copy_texts(self):

            orig_0 = self.project.main_texts[0]
            orig_2 = self.project.main_texts[2]
            self.project.copy_texts([0, 2], Document.MAIN)
            assert self.project.clipboard.data == [orig_0, None, orig_2]

        def test_cut_texts(self):

            orig_0 = self.project.main_texts[0]
            orig_2 = self.project.main_texts[2]
            self.project.cut_texts([0, 2], Document.MAIN)
            assert self.project.main_texts[0] == ''
            assert self.project.main_texts[2] == ''
            assert self.project.clipboard.data == [orig_0, None, orig_2]

            self.project.undo()
            assert self.project.main_texts[0] == orig_0
            assert self.project.main_texts[2] == orig_2

        def test_get_mode(self):

            assert self.project.get_mode() in (Mode.TIME, Mode.FRAME)

        def test_get_needs_resort(self):

            assert self.project.get_needs_resort(0, '99:00:00,000') is True
            assert self.project.get_needs_resort(0, '00:00:00,000') is False

        def test_get_positions(self):

            positions = self.project.get_positions()
            assert positions in (self.project.times, self.project.frames)

        def test_insert_subtitles(self):

            orig_1 = self.project.main_texts[1]
            orig_2 = self.project.main_texts[2]
            self.project.insert_subtitles([1, 2])
            assert self.project.main_texts[1] == ''
            assert self.project.main_texts[2] == ''

            self.project.undo()
            assert self.project.main_texts[1] == orig_1
            assert self.project.main_texts[2] == orig_2

            orig_0 = self.project.main_texts[0]
            orig_1 = self.project.main_texts[1]
            self.project.insert_subtitles(
                [0, 1],
                ['00:00:00:001', '00:00:00:002'],
                [0, 1],
                ['1', '2'],
                ['1', '2']

            )
            assert self.project.main_texts[0] == '1'
            assert self.project.main_texts[1] == '2'

            self.project.undo()
            assert self.project.main_texts[0] == orig_0
            assert self.project.main_texts[1] == orig_1

        def test_paste_texts(self):

            self.project.copy_texts([2, 3], Document.TRAN)
            orig_0 = self.project.main_texts[0]
            orig_1 = self.project.main_texts[1]
            self.project.paste_texts(0, Document.MAIN)
            assert self.project.main_texts[0] == self.project.tran_texts[2]
            assert self.project.main_texts[1] == self.project.tran_texts[3]

            self.project.undo()
            assert self.project.main_texts[0] == orig_0
            assert self.project.main_texts[1] == orig_1

            self.project.clipboard.data = ['test'] * 999
            self.project.paste_texts(0, Document.MAIN)
            assert len(self.project.times) == 999
            for i in range(999):
                assert self.project.main_texts[i] == 'test'

            self.project.undo()
            assert self.project.main_texts[0] == orig_0
            assert self.project.main_texts[1] == orig_1

        def test_remove_subtitles(self):

            orig_length = len(self.project.times)
            orig_2 = self.project.main_texts[2]
            orig_3 = self.project.main_texts[3]
            self.project.remove_subtitles([2, 3])
            assert len(self.project.times) == orig_length - 2

            self.project.undo()
            assert len(self.project.times) == orig_length
            assert self.project.main_texts[2] == orig_2
            assert self.project.main_texts[3] == orig_3

        def test_replace_both_texts(self):

            orig_main_1 = self.project.main_texts[1]
            orig_tran_1 = self.project.tran_texts[1]
            self.project.replace_both_texts([[1], [1]], [['test'], ['test']])
            assert self.project.main_texts[1] == 'test'
            assert self.project.tran_texts[1] == 'test'

            self.project.undo()
            assert self.project.main_texts[1] == orig_main_1
            assert self.project.tran_texts[1] == orig_tran_1

        def test_replace_texts(self):

            orig_main_1 = self.project.main_texts[1]
            orig_main_2 = self.project.main_texts[2]
            self.project.replace_texts([1, 2], Document.MAIN, ['1', '2'])
            assert self.project.main_texts[1] == '1'
            assert self.project.main_texts[2] == '2'

            self.project.undo()
            assert self.project.main_texts[1] == orig_main_1
            assert self.project.main_texts[2] == orig_main_2

        def test_set_frame(self):

            orig_hide_frame = self.project.frames[3][HIDE]
            orig_durn_frame = self.project.frames[3][DURN]
            orig_hide_time  = self.project.times[3][HIDE]
            orig_durn_time  = self.project.times[3][DURN]

            self.project.set_frame(3, HIDE, 8888888)
            assert self.project.frames[3][HIDE] == 8888888
            assert self.project.frames[3][DURN] != orig_hide_frame
            assert self.project.times[3][HIDE]  != orig_hide_time
            assert self.project.times[3][DURN]  != orig_durn_time

            self.project.undo()
            assert self.project.frames[3][HIDE] == orig_hide_frame
            assert self.project.frames[3][DURN] == orig_durn_frame
            assert self.project.times[3][HIDE]  == orig_hide_time
            assert self.project.times[3][DURN]  == orig_durn_time

        def test_set_text(self):

            orig_text = self.project.tran_texts[2]
            self.project.set_text(2, Document.TRAN, 'foo')
            assert self.project.tran_texts[2] == 'foo'

            self.project.undo()
            assert self.project.tran_texts[2] == orig_text

        def test_set_time(self):

            orig_hide_time  = self.project.times[3][HIDE]
            orig_durn_time  = self.project.times[3][DURN]
            orig_hide_frame = self.project.frames[3][HIDE]
            orig_durn_frame = self.project.frames[3][DURN]

            self.project.set_time(3, DURN, '33:33:33,333')
            assert self.project.times[3][HIDE]  != orig_hide_time
            assert self.project.times[3][DURN]  == '33:33:33,333'
            assert self.project.frames[3][HIDE] != orig_hide_frame
            assert self.project.frames[3][DURN] != orig_durn_frame

            self.project.undo()
            assert self.project.times[3][HIDE]  == orig_hide_time
            assert self.project.times[3][DURN]  == orig_durn_time
            assert self.project.frames[3][HIDE] == orig_hide_frame
            assert self.project.frames[3][DURN] == orig_durn_frame

        def test_sort_data(self):

            last = len(self.project.times) - 1
            orig_times  = copy.deepcopy(self.project.times)
            orig_text_0 = self.project.main_texts[0]
            self.project.set_frame(0, SHOW, 9999999999)
            assert self.project.times[:last] == orig_times[1:]
            assert self.project.main_texts[last] == orig_text_0

            self.project.undo()
            assert self.project.times[1:] == orig_times[1:]
            assert self.project.main_texts[0] == orig_text_0

    TestEditDelegate().run()
