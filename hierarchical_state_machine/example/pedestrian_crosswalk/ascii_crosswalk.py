"""
Copyright (c) 2023 by Crystal Clear Design

This intellectual property is shared to the public domain under the MIT License.
Crystal Clear Design offers no warranty and accepts no liability.
The only requirement for use is that this copyright notice remains intact.

This file is an example to help illustrate the use of the state_machine.py
library module. It simulates the common crosswalk signaling system used to
help pedestrians cross a busy street by stopping the vehicle traffic.

DISCLAIMER: This example must not be used for an actual, safety-critical
implementation of a crosswalk! It was selected for its familiarity to anyone
learning about the library, and is only to be used for demonstrating the various
features of the state_machine library module, and its use. This example does not
meet necessary safety requirements such as handling power outages, burned out
lights, emergency vehicle approaches, nor other possible events and usages.
"""

import copy
try:
    import curses
except:
    print("This test script requires the 'curses' module. Before trying again, run: pip install windows-curses")
    exit(1)


trf_lt_strs = [
    " .-. "
  , "|   |"
  , " '-' "
]

trf_sig_strs = [
    " _.---._ "
  , "|  .-.  |"
  , "| |   | |"
  , "|  '-'  |"
  , "|_.---._|"
  , "|  .-.  |"
  , "| |   | |"
  , "|  '-'  |"
  , " \_____/"
]

hand_strs = [
    "   _.-._"
  , " _| | | |"
  , "| | | | |"
  , "| | | | | ,-,"
  , "| i ` i |/ /"
  , "|     ,-' /"
  , "|    ;    |"
  , "|        /"
  , " \______/"
]

walk_strs = [
    "     / \\"
  , "  _..\ /"
  , " /     \\"
  , " | |   | `--"
  , "   /  /"
  , "  / ^ \\"
  , " |     \\"
  , "/       |"
]

digit_0_strs = [
    " -----"
  , "|     |"
  , "|     |"
  , ""
  , "|     |"
  , "|     |"
  , " -----"
]

digit_1_strs = [
    ""
  , "      |"
  , "      |"
  , ""
  , "      |"
  , "      |"
  , ""
]

digit_2_strs = [
    " -----"
  , "      |"
  , "      |"
  , " -----"
  , "|"
  , "|"
  , " -----"
]

digit_3_strs = [
    " -----"
  , "      |"
  , "      |"
  , " -----"
  , "      |"
  , "      |"
  , " -----"
]

digit_4_strs = [
    ""
  , "|     |"
  , "|     |"
  , " -----"
  , "      |"
  , "      |"
  , ""
]

digit_5_strs = [
    " -----"
  , "|"
  , "|"
  , " -----"
  , "      |"
  , "      |"
  , " -----"
]

digit_6_strs = [
    " -----"
  , "|"
  , "|"
  , " -----"
  , "|     |"
  , "|     |"
  , " -----"
]

digit_7_strs = [
    " -----"
  , "      |"
  , "      |"
  , "       "
  , "      |"
  , "      |"
  , ""
]

digit_8_strs = [
    " -----"
  , "|     |"
  , "|     |"
  , " -----"
  , "|     |"
  , "|     |"
  , " -----"
]

digit_9_strs = [
    " -----"
  , "|     |"
  , "|     |"
  , " -----"
  , "      |"
  , "      |"
  , ""
]

digits = [
    digit_0_strs
  , digit_1_strs
  , digit_2_strs
  , digit_3_strs
  , digit_4_strs
  , digit_5_strs
  , digit_6_strs
  , digit_7_strs
  , digit_8_strs
  , digit_9_strs
]

class ascii_crosswalk:
    def __init__(self, stdscr) -> None:
        # Using -1 as a flag to not show the count.
        self.ped_count_down_s = -1
        self.traf_light_color = "red"
        self.ped_light_color = "red"

        # Set up curses windows.
        self.stdscr = stdscr
        self.stdscr.clear()
        curses.start_color()
        self.colors = {}
        self.colors["wht"] = curses.color_pair(0)
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        self.colors["cya"] = curses.color_pair(1)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        self.colors["red"] = curses.color_pair(2)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        self.colors["yel"] = curses.color_pair(3)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
        self.colors["grn"] = curses.color_pair(4)
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_RED)
        self.colors["red_red"] = curses.color_pair(5)
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_YELLOW)
        self.colors["yel_yel"] = curses.color_pair(6)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_BLACK)
        self.colors["blk"] = curses.color_pair(7)
        curses.curs_set(False)
        curses.cbreak()
        curses.raw()
        curses.noecho()
        self.stdscr.nodelay(True)

        if curses.COLS < 64 or curses.LINES < 32:
            curses.resize_term(32, 64)
        self.stdscr.refresh()

        # Set up "display" and "status" window areas.
        self.scrn_wid = curses.COLS
        self.scrn_hgt = curses.LINES
        
        # 19 rows / lines required (+2 for borders) to fit the signal drawings.
        display_win_hgt = 22
        self.display_win_hgt = display_win_hgt
        status_win_hgt = self.scrn_hgt - display_win_hgt
        self.status_win_hgt = status_win_hgt

        self.display_win_bord = curses.newwin(display_win_hgt, self.scrn_wid, 0, 0)
        self.display_win_bord.border()
        self.display_win_bord.refresh()
        self.display_win = curses.newwin(display_win_hgt - 2, self.scrn_wid - 2, 1, 1)

        self.status_win_bord = curses.newwin(status_win_hgt, self.scrn_wid, self.scrn_hgt - status_win_hgt, 0)
        self.status_win_bord.border()
        self.status_win_bord.refresh()
        self.status_pad = curses.newpad(status_win_hgt - 2, self.scrn_wid - 2)
        self.status_pad.scrollok(1)
        self.status_pad_row = 0
        self.status_pad_ul_y = self.scrn_hgt - status_win_hgt + 1
        self.status_pad_ul_x = 1
        self.status_pad_lr_y = self.scrn_hgt - 1
        self.status_pad_lr_x = self.scrn_wid - 1
        #print(f"self.scrn_hgt={self.scrn_hgt}")

        title_x = self.scrn_wid - 33 - 2
        self.display_win.addstr(0, title_x, "-------------------------------", self.colors["cya"])
        self.display_win.addstr(1, title_x, "|  Crosswalk Light Simulator  |", self.colors["cya"])
        self.display_win.addstr(2, title_x, "-------------------------------", self.colors["cya"])
        self.display_win.addstr(4, title_x, "Press 'b' to request a crossing", self.colors["cya"])
        self.display_win.addstr(5, title_x, "Press 'esc' to exit simulation",  self.colors["cya"])
        
        #self.stdscr.getkey()
        #self.stdscr.nodelay(True)
        return

    def print_display(self) -> None:
        self.draw_traf_sig()
        self.draw_ped_sig()
        self.display_win.refresh()
        return

    def print_status(self, status: str) -> None:
        self.status_pad.addstr(str(status) + '\n', self.colors["cya"])
        # Note: With these settings, once it fills the window, it starts to auto-scroll!
        # No need to manually try to track the first visible row as was done here...
        #if self.status_pad_row < self.status_pad_len - self.status_pad_hgt:
        #    self.status_pad_row += 1

        # The arguments are pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol; the p arguments
        # refer to the upper left corner of the pad region to be displayed and the s arguments
        # define a clipping box on the screen within which the pad region is to be displayed.
        self.status_pad.refresh(self.status_pad_row, 0, self.status_pad_ul_y, self.status_pad_ul_x, self.status_pad_lr_y, self.status_pad_lr_x)

        return

    def set_traf_light(self, color: str) -> None:
        assert color == "blk" or color == "red" or color == "yel"
        self.traf_light_color = color
        return

    def set_ped_light(self, color: str) -> None:
        assert color == "blk" or color == "red" or color == "yel" or color == "grn"
        self.ped_light_color = color
        return

    def set_ped_time(self, time_s: int) -> None:
        assert time_s >= -1 and time_s < 100
        self.ped_count_down_s = time_s
        return

    def draw_traf_sig(self) -> None:
        y = 0
        for line in trf_sig_strs:
            x = 1
            self.display_win.addstr(y, x, line, self.colors["wht"])
            y += 1

        if self.traf_light_color == "red":
            y = 1
            for line in trf_lt_strs:
                x = 3
                self.display_win.addstr(y, x, line, self.colors["red"])
                y += 1
            self.display_win.addstr(2, 5, " ", self.colors["red_red"])

        if self.traf_light_color == "yel":
            y = 5
            for line in trf_lt_strs:
                x = 3
                self.display_win.addstr(y, x, line, self.colors["yel"])
                y += 1
            self.display_win.addstr(6, 5, " ", self.colors["yel_yel"])

        #self.display_win.refresh()
        return

    def draw_hand(self, color) -> None:
        posn_y = 10
        posn_x = 20
        y = posn_y
        for line in hand_strs:
            self.display_win.addstr(y, posn_x, line, color)
            y += 1

        return
    
    def draw_walk(self, color) -> None:
        posn_y = 10
        posn_x = 20
        y = posn_y
        for line in walk_strs:
            self.display_win.addstr(y, posn_x, line, color)
            y += 1

        return

    def draw_count(self, posn_y: int, posn_x: int, digit_idx: int, color) -> None:
        assert posn_y >= 0 and posn_y < self.display_win_hgt - 2
        assert posn_x >= 0 and posn_x < self.scrn_wid - 2
        assert digit_idx >= 0 and digit_idx <= 9

        y = posn_y
        digit_strs = digits[digit_idx]
        for line in digit_strs:
            self.display_win.addstr(y, posn_x, line, color)
            y += 1

        return

    def draw_ped_sig(self) -> None:
        hand_posn_y = 11
        hand_posn_x = 17
        count_posn_10s_y = hand_posn_y
        count_posn_10s_x = hand_posn_x + 20
        count_posn_1s_y = hand_posn_y
        count_posn_1s_x = count_posn_10s_x + 10

        self.draw_walk(self.colors["blk"])
        self.draw_hand(self.colors["blk"])
        if self.ped_light_color == "red":
            self.draw_hand(self.colors["red"])
        elif self.ped_light_color == "yel":
            self.draw_hand(self.colors["yel"])
        elif self.ped_light_color == "grn":
            self.draw_walk(self.colors["grn"])

        # Blank any currently drawn digits.
        self.draw_count(count_posn_10s_y, count_posn_10s_x, 8, self.colors["blk"])
        self.draw_count(count_posn_1s_y,  count_posn_1s_x,  8, self.colors["blk"])
        if self.ped_count_down_s > -1:
            tens_digit = int(self.ped_count_down_s / 10)
            ones_digit = int(self.ped_count_down_s - (tens_digit * 10))
            self.draw_count(count_posn_10s_y, count_posn_10s_x, tens_digit, self.colors["yel"])
            self.draw_count(count_posn_1s_y,  count_posn_1s_x,  ones_digit, self.colors["yel"])
        
        #self.display_win.refresh()
        return

