#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import sys
import subprocess
import gettext

# i18n: http://docs.python.org/2/library/gettext.html
#t = gettext.translation("solydxk-conky", "/usr/share/locale")
#_ = t.lgettext


# Class to execute a command and return the output in an array
class ExecCmd(object):

    def __init__(self, loggerObject=None):
        self.log = loggerObject

    def run(self, cmd, realTime=True, returnAsList=True):
        if self.log:
            self.log.write(_("Command to execute: %(cmd)s") % { "cmd": cmd }, 'execcmd.run', 'debug')

        p = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lstOut = []
        while True:
            line = p.stdout.readline()
            if not line:
                break
            # Strip the line, also from null spaces (strip() only strips white spaces)
            line = line.decode('utf-8').strip().strip("\0")
            lstOut.append(line)
            if realTime:
                sys.stdout.flush()
                if self.log:
                    self.log.write(line, 'execcmd.run', 'info')

        ret = lstOut
        if not returnAsList:
            ret = "\n".join(lstOut)
        return ret
