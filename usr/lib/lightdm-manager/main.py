#!/usr/bin/env python

# Elevate permissions
import os
import functions
import getopt
import sys
import string
import gtk
import gettext
from logger import Logger
from dialogs import MessageDialogSave

# i18n
gettext.install("lightdm-manager", "/usr/share/locale")


# Help
def usage():
    # Show usage
    hlp = """Usage: spm [options]

Options:
  -d (--debug): print debug information to log file in user directory
  -f (--force): force start in a live environment
  -h (--help): show this help"""
    print hlp


# Handle arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hdf', ['help', 'debug', 'force'])
except getopt.GetoptError:
    usage()
    sys.exit(2)

debug = False
force = False
for opt, arg in opts:
    if opt in ('-d', '--debug'):
        debug = True
    if opt in ('-f', '--force'):
        force = True
    elif opt in ('-h', '--help'):
        usage()
        sys.exit()

# Initialize logging
logFile = ''
if debug:
    logFile = 'lightdm-manager.log'
log = Logger(logFile)
functions.log = log
if debug:
    if os.path.isfile(log.logPath):
        open(log.logPath, 'w').close()
    log.write(_("Write debug information to file: %(path)s") % { "path": log.logPath }, 'main', 'info')

# Log some basic environmental information
machineInfo = functions.getSystemVersionInfo()
log.write(_("Machine info: %(info)s") % { "info": machineInfo }, 'main', 'info')
version = functions.getPackageVersion('lightdm-manager')
log.write(_("lightdm-manager version: %(version)s") % { "version": version }, 'main', 'info')

if functions.isPackageInstalled('lightdm'):
    # Set variables
    scriptDir = os.path.dirname(os.path.realpath(__file__))

    # Pass arguments to lightdm-manager.py: replace - with : -> because kdesudo assumes these options are meant for him...
    # TODO: Isn't there another way?
    args = ' '.join(sys.argv[1:])
    if len(args) > 0:
        args = ' ' + string.replace(args, '-', ':')
        # Pass the log path to lightdm-manager.py
        if debug:
            args += ' :l ' + log.logPath

    dist = functions.getDistribution()
    if dist == 'debian' or dist == 'arm':
        # Do not run in live environment
        if not functions.isRunningLive() or force:
            dpmPath = os.path.join(scriptDir, 'lightdm-manager.py' + args)

            # Add launcher string, only when not root
            launcher = ''
            if os.geteuid() > 0:
                launcher = "gksu --message \"<b>%s</b>\"" % _("Please enter your password")
                if os.path.exists('/usr/bin/kdesudo'):
                    launcher = "kdesudo -i /usr/share/lightdm-manager/logo.png -d --comment \"<b>%s</b>\"" % _("Please enter your password")

            cmd = '%s python %s' % (launcher, dpmPath)
            log.write(_("Startup command: %(cmd)s") % { "cmd": cmd }, 'main', 'debug')
            os.system(cmd)
        else:
            title = _("LightDM Manager - Live environment")
            msg = _("LightDM Manager cannot run in a live environment\n\nTo force start, use the --force argument")
            MessageDialogSave(title, msg, gtk.MESSAGE_INFO).show()
            log.write(msg, 'main', 'warning')
    else:
        title = _("LightDM Manager - Debian based")
        msg = _("LightDM Manager can only run on Debian based distributions")
        MessageDialogSave(title, msg, gtk.MESSAGE_WARNING).show()
        log.write(msg, 'main', 'warning')
else:
    title = _("LightDM Manager")
    msg = _("LightDM not installed - quitting.")
    MessageDialogSave(title, msg, gtk.MESSAGE_WARNING).show()
    log.write(msg, 'main', 'warning')
