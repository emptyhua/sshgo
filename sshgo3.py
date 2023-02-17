#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os,sys,re
import curses
import locale
import math
import traceback
from optparse import OptionParser

locale.setlocale(locale.LC_ALL, 'en_US')

def _assert(exp, err):
    if not exp:
        print(err, file=sys.stderr)
        sys.exit(1)


class SSHGO:

    UP = -1
    DOWN = 1

    KEY_O = 79
    KEY_R = 82
    KEY_G = 71
    KEY_o = 111
    KEY_r = 114
    KEY_g = 103
    KEY_c = 99
    KEY_C = 67
    KEY_m = 109
    KEY_M = 77
    KEY_d = 0x64
    KEY_u = 0x75
    KEY_SPACE = 32
    KEY_ENTER = 10
    KEY_q = 113
    KEY_ESC = 27

    KEY_j = 106
    KEY_k = 107

    KEY_SPLASH = 47

    screen = None

    def _parse_tree_from_config_file(self, config_file):
        tree = {'line_number':None,'expanded':True,'line':None,'sub_lines':[]}

        def find_parent_line(new_node):
            line_number = new_node['line_number']
            level = new_node['level']

            if level == 0:
                return tree

            stack = tree['sub_lines'] + []
            parent = None
            while len(stack):
                node = stack.pop()
                if node['line_number'] < line_number and node['level'] == level - 1:
                    if parent is None:
                        parent = node
                    elif node['line_number'] > parent['line_number']:
                        parent = node
                if len(node['sub_lines']) and node['level'] < level:
                    stack = stack + node['sub_lines']
                    continue

            return parent

        tree_level = None
        nodes_pool = []
        line_number = 0;


        for line in open(config_file, 'r'):
            line_number += 1
            line_con = line.strip()
            if line_con == '' or line_con[0] == '#':
                continue
            expand = True
            if line_con[:2] == '- ':
                line_con = line_con[2:]
                expand = False
            indent = re.findall(r'^[\t ]*(?=[^\t ])', line)[0]
            line_level = indent.count('    ') + indent.count('\t')
            if tree_level == None:
                _assert(line_level == 0, 'invalid indent,line:' + str(line_number))
            else:
                _assert(line_level <= tree_level
                        or line_level == tree_level + 1, 'invalid indent,line:' + str(line_number))
            tree_level = line_level

            new_node = {'level':tree_level,'expanded':expand,'line_number':line_number,'line':line_con,'sub_lines':[]}
            nodes_pool.append(new_node)
            parent = find_parent_line(new_node)
            parent['sub_lines'].append(new_node)

        return tree, nodes_pool


    def __init__(self, config_file):

        self.hosts_tree, self.hosts_pool = self._parse_tree_from_config_file(config_file)

        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.screen.keypad(1)
        self.screen.border(0)

        self.top_line_number = 0
        self.highlight_line_number = 0
        self.search_keyword = None

        curses.start_color()
        curses.use_default_colors()

        #highlight
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
        self.COLOR_HIGHLIGHT = 2
        #red
        curses.init_pair(3, curses.COLOR_RED, -1)
        self.COLOR_RED = 3

        #red highlight
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLUE)
        self.COLOR_RED_HIGH = 4

        #white bg
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.COLOR_WBG = 5

        #black bg
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_BLACK)
        self.COLOR_BBG = 6

        try:
            self.run()
        except SystemExit:
            self.restore_screen()
            pass
        except:
            self.restore_screen()
            traceback.print_exc()


    def run(self):
        while True:
            self.render_screen()
            c = self.screen.getch()
            if c == curses.KEY_UP or c == self.KEY_k:
                self.updown(-1)
            elif c == curses.KEY_DOWN or c == self.KEY_j:
                self.updown(1)
            elif c == self.KEY_u:
                for i in range(0, curses.tigetnum('lines')):
                    self.updown(-1)
            elif c == self.KEY_d:
                for i in range(0, curses.tigetnum('lines')):
                    self.updown(1)
            elif c == self.KEY_ENTER or c == self.KEY_SPACE:
                self.toggle_node()
            elif c == self.KEY_ESC or c == self.KEY_q:
                self.exit()
            elif c == self.KEY_O or c == self.KEY_M:
                self.open_all()
            elif c == self.KEY_o or c == self.KEY_m:
                self.open_node()
            elif c == self.KEY_C or c == self.KEY_R:
                self.close_all()
            elif c == self.KEY_c or c == self.KEY_r:
                self.close_node()
            elif c == self.KEY_g:
                self.page_top()
            elif c == self.KEY_G:
                self.page_bottom()
            elif c == self.KEY_SPLASH:
                self.enter_search_mode()

    def exit(self):
        if self.search_keyword is not None:
            self.search_keyword = None
        else:
            sys.exit(0)

    def enter_search_mode(self):
        screen_cols = curses.tigetnum('cols')
        self.screen.addstr(0, 0, '/' + ' ' * screen_cols)
        curses.echo()
        curses.curs_set(1)
        self.search_keyword = self.screen.getstr(0, 1).decode('utf-8')
        curses.noecho()
        curses.curs_set(0)

    def _get_visible_lines_for_render(self):
        lines = []
        stack = self.hosts_tree['sub_lines'] + []
        while len(stack):
            node = stack.pop()
            lines.append(node)
            if node['expanded'] and len(node['sub_lines']):
                stack = stack + node['sub_lines']

        lines.sort(key=lambda n:n['line_number'], reverse=False)
        return lines

    def _search_node(self):
        rt = []
        keyword = self.search_keyword.lower()
        for node in self.hosts_pool:
            if len(node['sub_lines']) == 0 and keyword in node['line'].lower():
                rt.append(node)
        return rt

    def get_lines(self):
        if self.search_keyword is not None:
            return self._search_node()
        else:
            return self._get_visible_lines_for_render()

    def page_top(self):
        self.top_line_number = 0
        self.highlight_line_number = 0

    def page_bottom(self):
        screen_lines = curses.tigetnum('lines')
        visible_hosts = self.get_lines()
        self.top_line_number = max(len(visible_hosts) - screen_lines, 0)
        self.highlight_line_number = min(screen_lines, len(visible_hosts)) - 1

    def open_node(self):
        visible_hosts = self.get_lines()
        linenum = self.top_line_number + self.highlight_line_number
        node = visible_hosts[linenum]
        if not len(node['sub_lines']):
            return
        stack = [node]
        while len(stack):
            node = stack.pop()
            node['expanded'] = True
            if len(node['sub_lines']):
                stack = stack + node['sub_lines']

    def close_node(self):
        visible_hosts = self.get_lines()
        linenum = self.top_line_number + self.highlight_line_number
        node = visible_hosts[linenum]
        if not len(node['sub_lines']):
            return
        stack = [node]
        while len(stack):
            node = stack.pop()
            node['expanded'] = False
            if len(node['sub_lines']):
                stack = stack + node['sub_lines']


    def open_all(self):
        for node in self.hosts_pool:
            if len(node['sub_lines']):
                node['expanded'] = True

    def close_all(self):
        for node in self.hosts_pool:
            if len(node['sub_lines']):
                node['expanded'] = False

    def toggle_node(self):
        visible_hosts = self.get_lines()
        linenum = self.top_line_number + self.highlight_line_number
        node = visible_hosts[linenum]
        if len(node['sub_lines']):
            node['expanded'] = not node['expanded']
        else:
            self.restore_screen()
            ssh = 'ssh'
            if os.popen('which zssh 2> /dev/null').read().strip() != '':
                ssh = 'zssh'
            cmd = node['line'].split('#')[0]
            os.execvp(ssh, [ssh] + re.split(r'[ ]+', cmd))

    def render_screen(self):
        # clear screen
        self.screen.clear()

        # now paint the rows
        screen_lines = curses.tigetnum('lines')
        screen_cols = curses.tigetnum('cols')

        if self.highlight_line_number >= screen_lines:
            self.highlight_line_number = screen_lines - 1

        all_nodes = self.get_lines()
        if self.top_line_number >= len(all_nodes):
            self.top_line_number = 0

        top = self.top_line_number
        bottom = self.top_line_number + screen_lines
        nodes = all_nodes[top:bottom]

        if not len(nodes):
            self.screen.refresh()
            return

        if self.highlight_line_number >= len(nodes):
            self.highlight_line_number = len(nodes) - 1

        if self.top_line_number >= len(all_nodes):
            self.top_line_number = 0

        for (index,node,) in enumerate(nodes):
            #linenum = self.top_line_number + index

            line = node['line']
            if len(node['sub_lines']):
                line += '(%d)' % len(node['sub_lines'])

            prefix = ''
            if self.search_keyword is None:
                prefix += '  ' * node['level']
            if len(node['sub_lines']):
                if node['expanded']:
                    prefix += '-'
                else:
                    prefix += '+'
            else:
                prefix += 'o'
            prefix += ' '

            # highlight current line
            if index != self.highlight_line_number:
                self.screen.addstr(index, 0, prefix, curses.color_pair(self.COLOR_RED))
                self.screen.addstr(index, len(prefix), line)
            else:
                self.screen.addstr(index, 0, prefix, curses.color_pair(self.COLOR_RED_HIGH))
                self.screen.addstr(index, len(prefix), line, curses.color_pair(self.COLOR_HIGHLIGHT))
        #render scroll bar
        for i in range(screen_lines):
            self.screen.addstr(i, screen_cols - 2, '|', curses.color_pair(self.COLOR_WBG))

        scroll_top = int(math.ceil((self.top_line_number + 1.0) / max(len(all_nodes), screen_lines) * screen_lines - 1))
        scroll_height = int(math.ceil((len(nodes) + 0.0) / len(all_nodes) * screen_lines))
        highlight_pos = int(math.ceil(scroll_height * ((self.highlight_line_number + 1.0)/min(screen_lines, len(nodes)))))

        self.screen.addstr(scroll_top, screen_cols - 2, '^', curses.color_pair(self.COLOR_WBG))
        self.screen.addstr(min(screen_lines, scroll_top + scroll_height) - 1, screen_cols - 2, 'v', curses.color_pair(self.COLOR_WBG))
        self.screen.addstr(min(screen_lines, scroll_top + highlight_pos) - 1, screen_cols - 2, '+', curses.color_pair(self.COLOR_WBG))


        self.screen.refresh()

    # move highlight up/down one line
    def updown(self, increment):
        visible_hosts = self.get_lines()
        visible_lines_count = len(visible_hosts)
        next_line_number = self.highlight_line_number + increment

        # paging
        if increment < 0 and self.highlight_line_number == 0 and self.top_line_number != 0:
            self.top_line_number += self.UP
            return
        elif increment > 0 and next_line_number == curses.tigetnum('lines') and (self.top_line_number+curses.tigetnum('lines')) != visible_lines_count:
            self.top_line_number += self.DOWN
            return

        # scroll highlight line
        if increment < 0 and (self.top_line_number != 0 or self.highlight_line_number != 0):
            self.highlight_line_number = next_line_number
        elif increment > 0 and (self.top_line_number+self.highlight_line_number+1) != visible_lines_count and self.highlight_line_number != curses.tigetnum('lines'):
            self.highlight_line_number = next_line_number

    def restore_screen(self):
        curses.initscr()
        curses.nocbreak()
        curses.echo()
        curses.endwin()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-c', '--config', help='use specified config file instead of ~/.ssh_hosts')
    options, args = parser.parse_args(sys.argv)
    host_file = os.path.expanduser('~/.ssh_hosts')

    if options.config is not None:
        host_file = options.config

    if not os.path.exists(host_file):
        print("%s is not found" % host_file, file=sys.stderr)
        sys.exit(1)

    sshgo = SSHGO(host_file)
