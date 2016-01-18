#! /usr/bin/env python3

# Make sure the right Gtk version is loaded
import gi
gi.require_version('Gtk', '3.0')

import os
import pwd
import spwd
import grp
import operator
import crypt
from shutil import copy
from datetime import datetime, timedelta
from gi.repository import GdkPixbuf, Gtk
from os.path import join, exists

#pwd
#Index	Attribute	Meaning
#0	pw_name	Login name
#1	pw_passwd	Optional encrypted password
#2	pw_uid	Numerical user ID
#3	pw_gid	Numerical group ID
#4	pw_gecos	User name or comment field
#5	pw_dir	User home directory
#6	pw_shell	User command interpreter

#pwd.getpwuid(uid)
#Return the password database entry for the given numeric user ID.

#pwd.getpwnam(name)
#Return the password database entry for the given user name.

#pwd.getpwall()
#Return a list of all available password database entries, in arbitrary order.

#==============================================================================

#spwd
#Index	Attribute	Meaning
#0	sp_nam	Login name
#1	sp_pwd	Encrypted password
#2	sp_lstchg	Date of last change
#3	sp_min	Minimal number of days between changes
#4	sp_max	Maximum number of days between changes
#5	sp_warn	Number of days before password expires to warn user about it
#6	sp_inact	Number of days after password expires until account is blocked
#7	sp_expire	Number of days since 1970-01-01 until account is disabled
#8	sp_flag	Reserved

#spwd.getspnam(name)
#Return the shadow password database entry for the given user name.

#spwd.getspall()
#Return a list of all available shadow password database entries, in arbitrary order.

#==============================================================================

#grp
#Index	Attribute	Meaning
#0	gr_name	the name of the group
#1	gr_passwd	the (encrypted) group password; often empty
#2	gr_gid	the numerical group ID
#3	gr_mem	all the group member’s user names

#grp.getgrgid(gid)
#Return the group database entry for the given numeric group ID. KeyError is raised if the entry asked for cannot be found.

#grp.getgrnam(name)
#Return the group database entry for the given group name. KeyError is raised if the entry asked for cannot be found.

#grp.getgrall()
#Return a list of all available group entries, in arbitrary order.

class User(object):

    def __init__(self, loggerObject=None):
        self.log = loggerObject

    def getAllUsersInfoDict(self, homeUsers=True):
        users = []
        pwds = self.sortListOnColumn(pwd.getpwall(), [0])
        for p in pwds:
            # Check UID range when returning non-system users only
            addUser = True
            if homeUsers:
                if p.pw_uid < 1000 or p.pw_uid > 1500:
                    addUser = False
            if addUser:
                users.append({ 'user': p, 'groups': self.getUserGroups(p.pw_name), 'prgrp': self.getUserPrimaryGroupName(p.pw_name), 'pwd': self.getUserPasswordInfoDict(p.pw_name), 'face': self.getUserFacePath(p.pw_name) })
        return users

    def getUserGroups(self, name):
        userGroups = []
        for g in grp.getgrall():
            for u in g.gr_mem:
                if u == name:
                    userGroups.append(g.gr_name)
        userGroups.sort()
        return userGroups

    def getGroupAccounts(self, group):
        groupAccounts = []
        try:
            g = grp.getgrnam(group)
            gid = g.gr_gid
            pwds = pwd.getpwall()
            for p in pwds:
                if p.pw_gid == gid:
                    groupAccounts.append(p.pw_name)
            for u in g.gr_mem:
                groupAccounts.append(u)
        except:
            # Best effort
            pass
        return groupAccounts

    def getGroups(self):
        groups = []
        groupsDict = grp.getgrall()
        for group in groupsDict:
            groups.append(group.gr_name)
        groups.sort()
        return groups

    def doesGroupExist(self, group):
        return group in self.getGroups()

    def getUsers(self, homeUsers=True):
        users = []
        pwds = pwd.getpwall()
        for p in pwds:
            addUser = True
            if homeUsers:
                if p.pw_uid < 1000 or p.pw_uid > 1500:
                    addUser = False
            if addUser:
                users.append(p.pw_name)
        users.sort()
        return users

    def getLoggedinUser(self):
        p = os.popen('logname', 'r')
        userName = p.readline().strip()
        p.close()
        if userName is "":
            userName = pwd.getpwuid(os.getuid()).pw_name
        return userName

    def doesUserExist(self, user):
        return user in self.getUsers(False)

    def getUserPrimaryGroupName(self, name):
        p = pwd.getpwnam(name)
        return grp.getgrgid(p.pw_gid).gr_name

    def getUserHomeDir(self, name=None):
        if name is None:
            name = pwd.getpwuid(os.getuid()).pw_name
        return pwd.getpwnam(name).pw_dir

    def getUserFacePath(self, name=None):
        face = None
        homeDir = self.getUserHomeDir(name)
        if exists(homeDir):
            # Check for face icon
            if exists(join(homeDir, ".face")):
                face = join(homeDir, ".face")
            elif exists(join(homeDir, ".face.icon")):
                face = join(homeDir, ".face.icon")

            if face is None:
                genericFace = '/usr/share/pixmaps/faces/user-generic.png'
                kdeFace = '/usr/share/kde4/apps/kdm/faces/.default.face.icon'
                if exists(genericFace):
                    face = genericFace
                elif exists(kdeFace):
                    face = kdeFace
                else:
                    defaultTheme = Gtk.IconTheme.get_default()
                    iconInfo = Gtk.IconTheme.lookup_icon(defaultTheme, "user-identity", 64, Gtk.IconLookupFlags.NO_SVG)
                    if iconInfo is not None:
                        face = iconInfo.get_filename()
                if face is not None:
                    copy(face, join(homeDir, ".face"))
        return face

    def getUserFacePixbuf(self, name=None, width=None, height=None):
        pb = None
        facePath = self.getUserFacePath(name)
        if facePath is None:
            defaultTheme = Gtk.IconTheme.get_default()
            iconInfo = Gtk.IconTheme.lookup_icon(defaultTheme, "user-identity", 64, Gtk.IconLookupFlags.NO_SVG)
            if iconInfo is not None:
                facePath = iconInfo.get_filename()
        if facePath is not None:
            pb = GdkPixbuf.Pixbuf.new_from_file(facePath)
            if width is not None and height is not None:
                pb.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
            elif width is not None:
                height = pb.get_height() * (width / pb.get_width())
                pb.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
            elif height is not None:
                width = pb.get_width() * (height / pb.get_height())
                pb.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
        return pb

    def getUserPasswordInfoDict(self, name):
        return spwd.getspnam(name)

    def getUserID(self, name):
        return pwd.getpwdwnam(name).pw_uid

    def getNewUserID(self):
        newID = 0
        pwds = pwd.getpwall()
        for p in pwds:
            if (p.pw_uid >= 500 and p.pw_uid <= 1500) and p.pw_uid > newID:
                newID = p.pw_uid
        return newID + 1

    def getGroupID(self, group):
        return grp.getgrnam(group).gr_gid

    def getNewGroupID(self):
        newID = 0
        grps = grp.getgrall()
        for g in grps:
            if (g.gr_gid >= 1000 and g.gr_gid <= 1500) and g.gr_gid > newID:
                newID = g.gr_gid
        return newID + 1

    def getShells(self):
        shells = []
        availableShells = ['/bin/bash', '/bin/sh', '/bin/ksh', '/bin/dash', '/bin/rbash', '/bin/ksh93', '/usr/bin/ksh']
        for shell in availableShells:
            if exists(shell):
                shells.append(shell)
        return shells

    def createGroup(self, group):
        cmd = "addgroup %s" % group
        print((">>> createGroup = %s" % cmd))
        return os.system(cmd)

    def deleteGroup(self, group):
        retMsg = ""
        cmd = "delgroup %s" % group
        print((">>> delgroup = %s" % cmd))
        ret = os.system(cmd)
        if ret > 0:
            if ret == 1280 or ret == 1792:
                retMsg = _("Cannot remove group '%(group)s': not empty." % {"group": group})
            else:
                retMsg = _("The command '%(cmd)s' returned error code: %(ret)d." % {"cmd": cmd, "ret": ret})
        return retMsg

    def removeGroupFromAccount(self, user, group):
        newGroups = []
        userGroups = self.getUserGroups(user)
        for ug in userGroups:
            if ug != group:
                newGroups.append(ug)
        if newGroups:
            self.manageUser(user, "", newGroups)

    def addGroupToAccount(self, user, group):
        cmd = "usermod -aG %(group)s %(user)s" % {"group": group, "user": user}
        print((">>> addGroupToAccount = %s" % cmd))
        return os.system(cmd)

    def manageUser(self, user, primary_group="", group_list=[], shell="", home_dir="", full_name="", password="", expire_date="", inactive_days=""):
        groups = ""

        user_cmd = "useradd"
        if self.doesUserExist(user):
            user_cmd = "usermod"

        if primary_group != "":
            if not self.doesGroupExist(primary_group):
                self.createGroup(primary_group)
            primary_group = "-g %(primary_group)s" % {"primary_group": primary_group}

        if group_list:
            for grp in group_list:
                if not self.doesGroupExist(grp):
                    self.createGroup(grp)
            groups = "-G %s" % ",".join(group_list)

        if shell != "":
            shell = "-s %(shell)s" % {"shell": shell}

        enc_password = ""
        if password != "":
            enc_password = self.encryptPassword(password)
            enc_password = "-p %(enc_password)s" % {"enc_password": enc_password}

        if home_dir != "":
            home_dir = "-d %(home_dir)s" % {"home_dir": home_dir}
            user = "-m %(user)s" % {"user": user}

        if full_name != "":
            full_name = "-c %(full_name)s" % {"full_name": full_name}

        if expire_date != "":
            expire_date = "-e %(expire_date)s" % {"expire_date": expire_date}

        if inactive_days != "":
            inactive_days = "-f %(inactive_days)s" % {"inactive_days": inactive_days}

        cmd = "%(user_cmd)s %(primary_group)s %(groups)s %(shell)s %(enc_password)s %(home_dir)s \
        %(full_name)s %(expire_date)s %(inactive_days)s %(user)s" % \
        {"user_cmd": user_cmd, "primary_group": primary_group, "groups": groups, "shell": shell, "enc_password": enc_password, \
        "home_dir": home_dir, "full_name": full_name, "expire_date": expire_date, "inactive_days": inactive_days, "user": user}
        print((">>> manageUser = %s" % cmd))
        return os.system(cmd)

    def deleteUser(self, user):
        retMsg = ""
        cmd = "deluser --remove-home %s" % user
        print((">>> deleteUser = %s" % cmd))
        ret = os.system(cmd)
        if ret > 0:
            if ret == 256:
                retMsg = _("Cannot remove user '%(user)s': processes started by user are still running." % {"user": user})
            else:
                retMsg = _("The command '%(cmd)s' returned error code: %(ret)d." % {"cmd": cmd, "ret": ret})
        return retMsg

    # Convert integer to (formatted) date
    def intToDate(self, nr_days, format_string=None, start_date=None):
        if start_date is None:
            start_date = datetime.now()
        dt = start_date + timedelta(days=nr_days)
        if format_string is None:
            return dt
        else:
            return dt.strftime(format_string)

    def disableUserAccount(self, user):
        cmd = "usermod -L -e 1970-01-01 %s" % user
        print((">>> disableUserAccount = %s" % cmd))
        return os.system(cmd)

    def enableUserAccount(self, user):
        cmd = "usermod -U -e 1970-01-01 %s" % user
        print((">>> enableUserAccount = %s" % cmd))
        return os.system(cmd)

    def encryptPassword(self, password):
        return crypt.crypt(password, "22")

    # Sort list on given column
    def sortListOnColumn(self, lst, columsList):
        for col in reversed(columsList):
            lst = sorted(lst, key=operator.itemgetter(col))
        return lst
