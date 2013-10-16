#! /usr/bin/env python3
#-*- coding: utf-8 -*-

# from gi.repository import Gtk, GdkPixbuf, GObject, Pango, Gdk
from gi.repository import Gtk, Gdk, GdkPixbuf
# abspath, dirname, join, expanduser, exists, basename
from os.path import join, exists
import os
import sys
import functions
import getopt
from shutil import copy
import gettext
from treeview import TreeViewHandler
from dialogs import MessageDialogSave, QuestionDialog, SelectImageDialog
from config import Config
from logger import Logger
from user import User
from image import ImageHandler
from combobox import ComboBoxHandler

menuItems = ['users', 'appearance']

# i18n
gettext.install("lightdm-manager", "/usr/share/locale")


#class for the main window
class LightDMManager:

    def __init__(self):
        self.scriptDir = os.path.dirname(os.path.realpath(__file__))

        # Load window and widgets
        self.builder = Gtk.Builder()
        self.builder.add_from_file(join(self.scriptDir, '../../share/lightdm-manager/lightdm-manager.glade'))
        # Main window objects
        go = self.builder.get_object
        self.window = go('ldmWindow')
        self.ebTitle = go('ebTitle')
        self.ebMenu = go('ebMenu')
        self.ebMenuUsers = go('ebMenuUsers')
        self.ebMenuAppearance = go('ebMenuAppearance')
        self.swUsers = go('swUsers')
        self.tvUsers = go('tvUsers')
        self.btnSave = go('btnSave')
        self.imgBackground = go('imgBackground')
        self.lblMenuUsers = go('lblMenuUsers')
        self.lblMenuAppearance = go('lblMenuAppearance')
        self.chkHideUsers = go('chkHideUsers')
        self.ebFace = go('ebFace')
        self.imgFace = go('imgFace')
        self.nbLightDM = go('nbLightDM')
        self.cmbThemes = go('cmbThemes')

        # Read from config file
        self.cfg = Config('lightdm-manager.conf')
        self.clrTitleFg = Gdk.Color.parse(self.cfg.getValue('COLORS', 'title_fg'))[1]
        self.clrTitleBg = Gdk.Color.parse(self.cfg.getValue('COLORS', 'title_bg'))[1]
        self.clrMenuSelect = Gdk.Color.parse(self.cfg.getValue('COLORS', 'menu_select'))[1]
        self.clrMenuHover = Gdk.Color.parse(self.cfg.getValue('COLORS', 'menu_hover'))[1]
        self.clrMenuBg = Gdk.Color.parse(self.cfg.getValue('COLORS', 'menu_bg'))[1]
        self.greeterConf = self.cfg.getValue('CONFIG', 'greeterConf')
        self.lightdmConf = self.cfg.getValue('CONFIG', 'lightdmConf')
        self.desktopbaseDir = self.cfg.getValue('CONFIG', 'desktopbaseDir')

        # Set background and forground colors
        self.ebTitle.modify_bg(Gtk.StateType.NORMAL, self.clrTitleBg)
        go('lblTitle').modify_fg(Gtk.StateType.NORMAL, self.clrTitleFg)
        self.lblMenuUsers.modify_fg(Gtk.StateType.NORMAL, self.clrTitleBg)
        self.lblMenuAppearance.modify_fg(Gtk.StateType.NORMAL, self.clrTitleBg)
        self.ebMenu.modify_bg(Gtk.StateType.NORMAL, self.clrMenuBg)
        self.ebMenuUsers.modify_bg(Gtk.StateType.NORMAL, self.clrMenuBg)
        self.ebMenuAppearance.modify_bg(Gtk.StateType.NORMAL, self.clrMenuBg)

        # Translations
        self.lblMenuUsers.set_text(_("Users"))
        self.lblMenuAppearance.set_text(_("Appearance"))
        go('lblBackground').set_text(_("Background"))
        go('lblTheme').set_text(_("Theme"))
        go('lblLightDmMenu').set_text(_("Menu"))
        self.chkHideUsers.set_label(_("Hide users"))
        go('lblUsersFace').set_text(_("User icon"))
        go('lblUsersAutologin').set_text(_("Auto-login"))

        # Get current background image
        self.cfgGreeter = Config(self.greeterConf)
        try:
            self.curBgPath = self.cfgGreeter.getValue('greeter', 'background')
            self.curTheme = self.cfgGreeter.getValue('greeter', 'theme-name')
        except:
            self.curBgPath = None
            self.curTheme = None

        # Get current auto-login user
        self.cfgLightdm = Config(self.lightdmConf)
        try:
            self.curAutoUser = self.cfgLightdm.getValue('SeatDefaults', 'autologin-user').strip()
            self.curHideUsers = False
            ghu = self.cfgLightdm.getValue('SeatDefaults', 'greeter-hide-users').strip()
            if ghu == 'true':
                self.curHideUsers = True
        except:
            self.curAutoUser = None
            self.curHideUsers = False

        # Init
        (width, height) = self.imgBackground.get_size_request()
        self.imgBgWidth = width
        self.imgBgHeight = height
        self.usr = User()
        self.newbgImg = self.curBgPath
        self.newAutoUser = self.curAutoUser
        self.newTheme = self.curTheme
        self.themes = []
        self.selectedMenuItem = None
        self.debug = False
        self.logPath = ''
        self.prevPath = None
        self.tempFace = "/tmp/face"
        self.tempUser = "/tmp/user"
        self.newFaces = []
        self.loggedUser = functions.getFileContents(self.tempUser)
        self.curUser = self.loggedUser

        # Handle arguments
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'dl:', ['debug', 'log='])
        except getopt.GetoptError:
            print(("Arguments cannot be parsed: %s" % str(sys.argv[1:])))
            sys.exit(1)

        for opt, arg in opts:
            if opt in ('-d', '--debug'):
                self.debug = True
            elif opt in ('-l', '--log'):
                self.logPath = arg

        # Initialize logging
        if self.debug:
            if not self.logPath:
                self.logPath = 'lightdm-manager.log'
        self.log = Logger(self.logPath, 'debug', True, None, self.window)

        # Backup config files because ConfigParser does not preserve commented lines
        if not exists("%s.org" % self.greeterConf):
            copy(self.greeterConf, "%s.org" % self.greeterConf)
            self.log.write("%(conf1)s copied to %(conf2)s.org" % { "conf1": self.greeterConf, "conf2": self.greeterConf }, 'LightDMManager.main', 'debug')
        if not exists("%s.org" % self.lightdmConf):
            copy(self.lightdmConf, "%s.org" % self.lightdmConf)
            self.log.write("%(conf1)s copied to %(conf2)s.org" % { "conf1": self.lightdmConf, "conf2": self.lightdmConf }, 'LightDMManager.main', 'debug')

        # Initiate the treeview handler and connect the custom toggle event with usersCheckBoxToggled
        self.tvHandler = TreeViewHandler(self.tvUsers, self.log)
        self.tvHandler.connect('checkbox-toggled', self.usersCheckBoxToggled)

        # Get users
        self.users = self.usr.getUsers()
        self.fillUsers()
        self.tvHandler.selectValue(self.curUser, 1)
        self.setBackground(self.curBgPath)
        self.cmbHandlerThemes = ComboBoxHandler(self.cmbThemes)
        self.listThemes()
        self.chkHideUsers.set_active(self.curHideUsers)

        # Show users menu
        self.on_ebMenuUsers_button_release_event(None)
        self.on_tvUsers_cursor_changed(None)

        self.version = functions.getPackageVersion('lightdm-manager')

        # Connect the signals and show the window
        self.builder.connect_signals(self)
        self.window.show()

    # ===============================================
    # Menu section functions
    # ===============================================

    def on_ebMenuUsers_enter_notify_event(self, widget, event):
        self.window.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        self.changeMenuBackground(menuItems[0])

    def on_ebMenuUsers_leave_notify_event(self, widget, event):
        self.window.get_window().set_cursor(None)
        self.changeMenuBackground(self.selectedMenuItem)

    def on_ebMenuAppearance_enter_notify_event(self, widget, event):
        self.window.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        self.changeMenuBackground(menuItems[1])

    def on_ebMenuAppearance_leave_notify_event(self, widget, event):
        self.window.get_window().set_cursor(None)
        self.changeMenuBackground(self.selectedMenuItem)

    def on_ebMenuUsers_button_release_event(self, widget, event=None):
        if self.selectedMenuItem != menuItems[0]:
            self.changeMenuBackground(menuItems[0], True)
            self.nbLightDM.set_current_page(0)

    def on_ebMenuAppearance_button_release_event(self, widget, event=None):
        if self.selectedMenuItem != menuItems[1]:
            self.changeMenuBackground(menuItems[1], True)
            self.nbLightDM.set_current_page(1)

    def changeMenuBackground(self, menuItem, select=False):
        ebs = []
        ebs.append([menuItems[0], self.ebMenuUsers])
        ebs.append([menuItems[1], self.ebMenuAppearance])
        for eb in ebs:
            if eb[0] == menuItem:
                if select:
                    self.selectedMenuItem = menuItem
                    eb[1].modify_bg(Gtk.StateType.NORMAL, self.clrMenuSelect)
                else:
                    if eb[0] != self.selectedMenuItem:
                        eb[1].modify_bg(Gtk.StateType.NORMAL, self.clrMenuHover)
            else:
                if eb[0] != self.selectedMenuItem or select:
                    eb[1].modify_bg(Gtk.StateType.NORMAL, self.clrMenuBg)

    # ===============================================
    # Functions
    # ===============================================

    def on_ebFace_enter_notify_event(self, widget, event):
        self.window.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_ebFace_leave_notify_event(self, widget, event):
        self.window.get_window().set_cursor(None)

    def on_ebFace_button_release_event(self, widget, event):
        home = self.usr.getUserHomeDir(self.curUser)
        primaryGroup = self.usr.getUserPrimaryGroupName(self.curUser)
        imagePath = SelectImageDialog(_('Select user image'), home, self.window).show()
        if imagePath is not None:
            tempUserImg = "%(tempFace)s.%(curUser)s" % {"tempFace": self.tempFace, "curUser": self.curUser}
            self.newFaces.append([tempUserImg, join(home, ".face"), self.curUser, primaryGroup])
            print((">>> self.newFaces = %s" % self.newFaces))
            ih = ImageHandler(imagePath)
            ih.makeFaceImage(tempUserImg)
            if exists(tempUserImg):
                self.imgFace.set_from_pixbuf(ih.pixbuf)

    def on_tvUsers_cursor_changed(self, widget):
        self.curUser = self.tvHandler.getSelectedValue(1)
        showFace = None
        if self.newFaces:
            for face in self.newFaces:
                if face[2] == self.curUser and exists(face[0]):
                    showFace = GdkPixbuf.Pixbuf.new_from_file(face[0])
        if showFace is None:
            showFace = self.usr.getUserFacePixbuf(self.curUser)
        self.imgFace.set_from_pixbuf(showFace)

    def on_btnSave_clicked(self, widget):
        saved = False
        saveHideUsers = False
        saveAutoUser = False
        saveFaces = False
        saveBackground = False
        saveTheme = False
        if self.chkHideUsers.get_active() != self.curHideUsers:
            saveHideUsers = True
        if self.curAutoUser != self.newAutoUser:
            saveAutoUser = True
        if self.newFaces:
            saveFaces = True
        if self.curBgPath != self.newbgImg:
            saveBackground = True
        self.newTheme = self.cmbHandlerThemes.getValue()
        if self.curTheme != self.newTheme:
            saveTheme = True

        if saveHideUsers or saveAutoUser or saveFaces or saveBackground or saveTheme:
            qd = QuestionDialog(_("LightDM settings"), _("Settings have changed\n\nDo you want to save the new settings?"), self.window)
            answer = qd.show()
            if answer:
                if saveAutoUser:
                    if self.newAutoUser is not None:
                        # Save the auto-login user
                        self.cfgLightdm.setValue('SeatDefaults', 'autologin-user', self.newAutoUser)
                        self.cfgLightdm.setValue('SeatDefaults', 'autologin-user-timeout', '0')
                        self.curAutoUser = self.newAutoUser
                        self.log.write("New auto-login user: %(usr)s" % { "usr": self.curAutoUser }, 'LightDMManager.saveSettings', 'debug')
                    else:
                        self.cfgLightdm.removeOption('SeatDefaults', 'autologin-user')
                        self.cfgLightdm.removeOption('SeatDefaults', 'autologin-user-timeout')
                        self.curAutoUser = None
                        self.log.write("Auto-login disabled", 'LightDMManager.saveSettings', 'debug')
                if saveHideUsers:
                    hideUsers = str(self.chkHideUsers.get_active()).lower()
                    self.cfgLightdm.setValue('SeatDefaults', 'greeter-hide-users', hideUsers)
                    self.log.write("Hide users saved: %(users)s" % {"users": hideUsers}, 'LightDMManager.saveSettings', 'debug')
                if saveFaces:
                    for face in self.newFaces:
                        if exists(face[0]):
                            copy(face[0], face[1])
                            if exists(face[1]):
                                os.system("chown %(owner)s:%(group)s %(path)s" % {"owner": face[2], "group": face[3], "path": face[1]})
                    self.log.write("User icons saved", 'LightDMManager.saveSettings', 'debug')
                if saveTheme:
                    self.cfgGreeter.setValue('greeter', 'theme-name', self.newTheme)
                    self.curTheme = self.newTheme
                    self.log.write("Theme saved: %(theme)s" % { "theme": self.curTheme }, 'LightDMManager.saveSettings', 'debug')
                if saveBackground:
                    if os.path.exists(self.newbgImg):
                        self.cfgGreeter.setValue('greeter', 'background', self.newbgImg)
                        self.curBgPath = self.newbgImg
                        self.log.write("Background saved: %(background)s" % { "background": self.curBgPath }, 'LightDMManager.saveSettings', 'debug')
                saved = True
            else:
                if os.path.exists(self.curBgPath):
                    self.setBackground(self.curBgPath)
                    self.log.write("Current background: %(background)s" % { "background": self.curBgPath }, 'LightDMManager.saveSettings', 'debug')
                else:
                    self.imgBackground.set_from_file(join(self.scriptDir, '../../share/lightdm-manager/select.png'))
                    self.log.write("No background set", 'LightDMManager.saveSettings', 'debug')
                self.fillUsers()

        if saved:
            self.curHideUsers = self.chkHideUsers.get_active()
            self.curAutoUser = self.newAutoUser
            self.newFaces = []
            self.curBgPath = self.newbgImg
            self.curTheme = self.newTheme
            MessageDialogSave(_("Saved"), _("LightDM settings saved successfully."), Gtk.MessageType.INFO, self.window).show()


    def on_ebBackground_button_release_event(self, widget, event):
        self.newbgImg = SelectImageDialog(_("Choose background image"), self.desktopbaseDir, self.window).show()
        if exists(self.newbgImg) and self.newbgImg != self.curBgPath:
            self.setBackground(self.newbgImg)
            self.log.write(_("New background: %(bg)s") % { "bg": self.newbgImg }, 'LightDMManager.chooseFile', 'info')

    def on_ebBackground_enter_notify_event(self, widget, event):
        self.window.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_ebBackground_leave_notify_event(self, widget, event):
        self.window.get_window().set_cursor(None)

    # This method is fired by the TreeView.checkbox-toggled event
    def usersCheckBoxToggled(self, obj, path, colNr, toggleValue):
        path = int(path)
        model = self.tvUsers.get_model()
        itr = model.get_iter(path)
        user = model[itr][1]

        if self.prevPath != path or toggleValue:
            # Only one toggle box can be selected (or none)
            self.tvHandler.treeviewToggleAll([0], False, 1, user)
            # Save current path
            self.prevPath = path
            # Save selected user
            self.newAutoUser = user
            self.log.write(_("Auto-login user selected: %(usr)s") % { "usr": user }, 'LightDMManager.usersCheckBoxToggled', 'info')
        elif self.prevPath == path and not toggleValue:
            self.newAutoUser = None

    def listThemes(self):
        themeDir = '/usr/share/themes'
        themeDirLocal = '~/.local/share/themes'
        dirs = functions.locate('gtk-*', themeDir, True) + functions.locate('gtk-*', themeDirLocal, True)
        for path in dirs:
            dirList = path.split('/')
            for d in dirList:
                if 'gtk-' in d:
                    break
                themeName = d
            if themeName not in self.themes:
                self.themes.append(themeName)
        if self.themes:
            self.cmbHandlerThemes.fillComboBox(self.themes)
            if self.curTheme in self.themes:
                self.cmbHandlerThemes.selectValue(self.curTheme)

    def fillUsers(self):
        selUsr = False
        contentList = []
        i = 0
        for usr in self.users:
            if usr == self.curAutoUser:
                selUsr = True
                self.prevPath = i
            else:
                selUsr = False
            contentList.append([selUsr, usr])
            i += 1

        # Fill treeview with users
        #fillTreeview(contentList, columnTypesList, columnHideList=[-1], setCursor=0, setCursorWeight=400, firstItemIsColName=False, appendToExisting=False, appendToTop=False)
        columnTypesList = ['bool', 'str']
        self.tvHandler.fillTreeview(contentList, columnTypesList)

    def setBackground(self, path):
        # Set Background
        if exists(path):
            ih = ImageHandler(path)
            ih.resizeImage(height=200)
            self.imgBackground.set_from_pixbuf(ih.pixbuf)


    # ===============================================
    # General functions
    # ===============================================

    def on_ldmWindow_destroy(self, widget, data=None):
        # Close the app
        self.on_btnSave_clicked(None)
        os.remove(self.tempUser)
        for tmp in self.newFaces:
            os.remove(tmp[0])
        Gtk.main_quit()


if __name__ == '__main__':
    # Create an instance of our GTK application
    try:
        gui = LightDMManager()
        Gtk.main()
    except KeyboardInterrupt:
        pass
