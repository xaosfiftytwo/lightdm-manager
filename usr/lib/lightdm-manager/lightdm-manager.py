#!/usr/bin/env python

try:
    import os
    import sys
    import pygtk
    pygtk.require('2.0')
    import gtk
    import functions
    import string
    import getopt
    import shutil
    from treeview import TreeViewHandler
    from dialogs import MessageDialogSave, QuestionDialog
    from config import Config
    from logger import Logger
except Exception, detail:
    print detail
    sys.exit(1)

menuItems = ['users', 'background']
greeterConf = '/etc/lightdm/lightdm-gtk-greeter.conf'
lightdmConf = '/etc/lightdm/lightdm.conf'
desktopbaseDir = '/usr/share/images/desktop-base'
themeDir = '/usr/share/themes'
themeDirLocal = '~/.local/share/themes'

#class for the main window
class LightDMManager:

    def __init__(self):
        self.scriptDir = os.path.dirname(os.path.realpath(__file__))
        # Load window and widgets
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(self.scriptDir, '../../share/lightdm-manager/lightdm-manager.glade'))
        self.window = self.builder.get_object('ldmWindow')
        self.lblTitle = self.builder.get_object('lblTitle')
        self.lblMenuTitle = self.builder.get_object('lblMenuTitle')
        self.lblMenuSubTitle = self.builder.get_object('lblMenuSubTitle')
        self.lblMenuUsers = self.builder.get_object('lblMenuUsers')
        self.lblMenuBackground = self.builder.get_object('lblMenuBackground')
        self.ebTitle = self.builder.get_object('ebTitle')
        self.ebMenu = self.builder.get_object('ebMenu')
        self.ebMenuUsers = self.builder.get_object('ebMenuUsers')
        self.ebMenuBackground = self.builder.get_object('ebMenuBackground')
        self.swUsers = self.builder.get_object('swUsers')
        self.tvUsers = self.builder.get_object('tvUsers')
        self.btnSave = self.builder.get_object('btnSave')
        self.boxBackground = self.builder.get_object('boxBackground')
        self.fleChooser = self.builder.get_object('fleChooser')
        self.fleChooserTheme = self.builder.get_object('fleChooserTheme')
        self.imgBackground = self.builder.get_object('imgBackground')
        self.statusbar = self.builder.get_object('statusbar')

        # Read from config file
        self.cfg = Config('lightdm-manager.conf')
        self.clrTitleFg = gtk.gdk.Color(self.cfg.getValue('COLORS', 'title_fg'))
        self.clrTitleBg = gtk.gdk.Color(self.cfg.getValue('COLORS', 'title_bg'))
        self.clrMenuSelect = gtk.gdk.Color(self.cfg.getValue('COLORS', 'menu_select'))
        self.clrMenuHover = gtk.gdk.Color(self.cfg.getValue('COLORS', 'menu_hover'))
        self.clrMenuBg = gtk.gdk.Color(self.cfg.getValue('COLORS', 'menu_bg'))

        # Get current background image
        self.cfgGreeter = Config(greeterConf)
        try:
            self.currentbgImg = self.cfgGreeter.getValue('greeter', 'background')
            self.currentTheme = self.cfgGreeter.getValue('greeter', 'theme-name')
        except:
            self.currentbgImg = None
            self.currentTheme = None

        # Get current auto-login user
        self.cfgLightdm = Config(lightdmConf)
        try:
            self.currentAutoUser = self.cfgLightdm.getValue('SeatDefaults', 'autologin-user').strip()
        except:
            self.currentAutoUser = None

        # Get image dimensions
        imgSize = self.imgBackground.get_size_request()
        self.imgBgWidth = imgSize[0]
        self.imgBgHeight = imgSize[1]

        self.newbgImg = self.currentbgImg
        self.newAutoUser = self.currentAutoUser
        self.newTheme = self.currentTheme
        self.selectedMenuItem = None
        self.debug = False
        self.logPath = ''
        self.prevPath = None

        # Add events
        signals = {
            'on_btnSave_clicked': self.saveSettings,
            'on_ebMenuUsers_button_release_event': self.showMenuUsers,
            'on_ebMenuUsers_enter_notify_event': self.changeMenuUsers,
            'on_ebMenuUsers_leave_notify_event': self.cleanMenu,
            'on_ebMenuBackground_button_release_event': self.showMenuBackgroundImg,
            'on_ebMenuBackground_enter_notify_event': self.changeMenuBackgroundImg,
            'on_ebMenuBackground_leave_notify_event': self.cleanMenu,
            'on_fleChooser_file_set': self.chooseFile,
            'on_fleChooserTheme_file_set': self.chooseTheme,
            'on_ldmWindow_destroy': self.destroy
        }
        self.builder.connect_signals(signals)

        self.window.show()

    # ===============================================
    # Menu section functions
    # ===============================================

    def cleanMenu(self, widget, event):
        self.changeMenuBackground(self.selectedMenuItem)

    def changeMenuUsers(self, widget, event):
        self.changeMenuBackground(menuItems[0])

    def changeMenuBackgroundImg(self, widget, event):
        self.changeMenuBackground(menuItems[1])

    def changeMenuBackground(self, menuItem, select=False):
        ebs = []
        ebs.append([menuItems[0], self.ebMenuUsers])
        ebs.append([menuItems[1], self.ebMenuBackground])
        for eb in ebs:
            if eb[0] == menuItem:
                if select:
                    self.selectedMenuItem = menuItem
                    eb[1].modify_bg(gtk.STATE_NORMAL, self.clrMenuSelect)
                else:
                    if eb[0] != self.selectedMenuItem:
                        eb[1].modify_bg(gtk.STATE_NORMAL, self.clrMenuHover)
            else:
                if eb[0] != self.selectedMenuItem or select:
                    eb[1].modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)

    def showMenuUsers(self, widget=None, event=None):
        if self.selectedMenuItem != menuItems[0]:
            self.saveSettings(None, menuItems[1])
            self.changeMenuBackground(menuItems[0], True)
            self.lblMenuTitle.set_text(self.lblMenuUsers.get_text())
            self.lblMenuSubTitle.set_text('Auto-login')
            self.boxBackground.hide()
            self.swUsers.show()

    def showMenuBackgroundImg(self, widget=None, event=None):
        if self.selectedMenuItem != menuItems[1]:
            self.saveSettings(None, menuItems[0])
            self.changeMenuBackground(menuItems[1], True)
            self.lblMenuTitle.set_text(self.lblMenuBackground.get_text())
            self.lblMenuSubTitle.set_text('Theme')
            self.boxBackground.show()
            self.swUsers.hide()

    # ===============================================
    # Functions
    # ===============================================

    def saveSettings(self, widget, menuItem=None):
        if menuItem is None:
            menuItem = self.selectedMenuItem

        if menuItem == menuItems[0]:
            if self.currentAutoUser != self.newAutoUser:
                qd = QuestionDialog('Auto-login user', 'The auto-login user has changed\n\nDo you want to save the new settings?', self.window)
                answer = qd.show()
                if answer:
                    if self.newAutoUser is not None:
                        # Save the auto-login user
                        self.cfgLightdm.setValue('SeatDefaults', 'autologin-user', self.newAutoUser)
                        self.cfgLightdm.setValue('SeatDefaults', 'autologin-user-timeout', '0')
                        self.currentAutoUser = self.newAutoUser
                        MessageDialogSave('Saved', 'Auto-login user saved:\n\n%s' % self.currentAutoUser, gtk.MESSAGE_INFO, self.window).show()
                        self.log.write("New auto-login user: %s" % self.currentAutoUser, 'LightDMManager.saveSettings', 'info')
                    else:
                        self.cfgLightdm.removeOption('SeatDefaults', 'autologin-user')
                        self.cfgLightdm.removeOption('SeatDefaults', 'autologin-user-timeout')
                        self.currentAutoUser = None
                        MessageDialogSave('Saved', 'Auto-login has been disabled.', gtk.MESSAGE_INFO, self.window).show()
                        self.log.write("Auto-login disabled", 'LightDMManager.saveSettings', 'info')
                else:
                    self.fillUsers()

        if menuItem == menuItems[1]:
            bg = False
            theme = False
            if self.currentbgImg != self.newbgImg:
                bg = True
            if self.currentTheme != self.newTheme:
                theme = True

            if bg or theme:
                qd = QuestionDialog('Appearance', 'Appearance settings have changed\n\nDo you want to save these new settings?', self.window)
                answer = qd.show()
                if answer:
                    msg = ''
                    if theme:
                        # Save background
                        self.cfgGreeter.setValue('greeter', 'theme-name', self.newTheme)
                        self.currentTheme = self.newTheme
                        msg = "Theme: %s" % self.currentTheme
                    if bg:
                        if os.path.exists(self.newbgImg):
                            # Save background
                            self.cfgGreeter.setValue('greeter', 'background', self.newbgImg)
                            self.currentbgImg = self.newbgImg
                            if msg != '':
                                msg += '\n'
                            msg += "Background: %s" % self.currentbgImg

                    MessageDialogSave('Saved', 'LightDM appearance saved:\n\n%s' % msg, gtk.MESSAGE_INFO, self.window).show()
                    self.log.write(msg, 'LightDMManager.saveSettings', 'info')
                else:
                    if self.currentTheme is not None:
                        self.fleChooserTheme.set_filename(os.path.join(themeDir, self.currentTheme))
                    self.fleChooserTheme.set_current_folder(themeDir)
                    if os.path.exists(self.currentbgImg):
                        self.imgBackground.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(self.currentbgImg, self.imgBgWidth, self.imgBgHeight))
                        self.fleChooser.set_filename(self.currentbgImg)
                        self.log.write("Current background: %s" % self.currentbgImg, 'LightDMManager.saveSettings', 'info')
                    else:
                        self.imgBackground.set_from_file(os.path.join(self.scriptDir, '../../share/lightdm-manager/empty.png'))
                        self.fleChooser.set_filename('')
                        self.fleChooser.set_current_folder(desktopbaseDir)
                        self.log.write("No background set", 'LightDMManager.saveSettings', 'info')

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
            self.log.write("Auto-login user selected: %s" % user, 'LightDMManager.usersCheckBoxToggled', 'info')
        elif self.prevPath == path and not toggleValue:
            self.newAutoUser = None
            functions.pushMessage(self.statusbar, "")

    def chooseFile(self, widget):
        self.newbgImg = self.fleChooser.get_filename()
        if os.path.exists(self.newbgImg) and self.newbgImg != self.currentbgImg:
            self.imgBackground.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(self.newbgImg, self.imgBgWidth, self.imgBgHeight))
            self.log.write("New background: %s" % self.newbgImg, 'LightDMManager.chooseFile', 'info')

    def chooseTheme(self, widget):
        chosenDir = self.fleChooserTheme.get_filename()
        themeInfo = self.getGtkTheme(chosenDir)
        chosenTheme = themeInfo[1]
        if chosenTheme != '':
            if chosenTheme != self.currentTheme:
                self.newTheme = chosenTheme
                self.log.write("New theme: %s" % self.newTheme, 'LightDMManager.chooseTheme', 'info')
        else:
            MessageDialogSave('No Theme', 'Directory does not contain a valid theme engine:\n\nPlease, choose another theme.', gtk.MESSAGE_WARNING, self.window).show()
            self.log.write("No valid theme: %s" % chosenDir, 'LightDMManager.chooseTheme', 'info')
            self.fleChooserTheme.set_current_folder(self.curThemeDir)

    def getGtkTheme(self, startDir, themeName=None):
        newThemeDir = ''
        newThemeName = ''
        for gtk in functions.locate('gtk-*', startDir, True):
            newThemeDir = ''
            newThemeName = ''

            dirList = gtk.split('/')
            for d in dirList:
                if 'gtk-' in d:
                    break
                newThemeDir += "%s/" % d
                newThemeName = d
            self.log.write('Found themedir: %s and theme name: %s' % (newThemeDir, "%s" % newThemeName), 'LightDMManager.getGtkTheme', 'debug')

            if themeName is None:
                break
            else:
                if newThemeName == themeName:
                    break
        return [newThemeDir, newThemeName]

    def fillUsers(self):
        selUsr = False
        contentList = []
        i = 0
        for usr in self.users:
            if usr[0] == self.currentAutoUser:
                selUsr = True
                self.prevPath = i
            else:
                selUsr = False
            contentList.append([selUsr, usr[0]])
            i += 1

        # Fill treeview with users
        #fillTreeview(contentList, columnTypesList, columnHideList=[-1], setCursor=0, setCursorWeight=400, firstItemIsColName=False, appendToExisting=False, appendToTop=False)
        columnTypesList = ['bool', 'str']
        self.tvHandler.fillTreeview(contentList, columnTypesList)


    # ===============================================
    # Main
    # ===============================================

    def main(self, argv):
        # Handle arguments
        try:
            opts, args = getopt.getopt(argv, 'dl:', ['debug', 'log='])
        except getopt.GetoptError:
            print 'Arguments cannot be parsed: ' + str(argv)
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
        self.log = Logger(self.logPath, 'debug', True, self.statusbar, self.window)
        functions.log = self.log

        # Backup config files because ConfigParser does not preserve commented lines
        if not os.path.exists("%s.org" % greeterConf):
            shutil.copy(greeterConf, "%s.org" % greeterConf)
            self.log.write('%s copied to %s' % (greeterConf, "%s.org" % greeterConf), 'LightDMManager.main', 'debug')
        if not os.path.exists("%s.org" % lightdmConf):
            shutil.copy(lightdmConf, "%s.org" % lightdmConf)
            self.log.write('%s copied to %s' % (lightdmConf, "%s.org" % lightdmConf), 'LightDMManager.main', 'debug')

        # Initiate the treeview handler and connect the custom toggle event with usersCheckBoxToggled
        self.tvHandler = TreeViewHandler(self.log, self.tvUsers)
        self.tvHandler.connect('checkbox-toggled', self.usersCheckBoxToggled)

        # Set background and forground colors
        self.ebTitle.modify_bg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblTitle.modify_fg(gtk.STATE_NORMAL, self.clrTitleFg)
        self.lblMenuTitle.modify_fg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblMenuUsers.modify_fg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblMenuBackground.modify_fg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.ebMenu.modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)
        self.ebMenuUsers.modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)
        self.ebMenuBackground.modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)

        # Change cursor
        self.ebMenuUsers.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND1))
        self.ebMenuBackground.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND1))

        # Get users
        self.users = functions.getUsers()
        self.fillUsers()

        # Set Background File Chooser
        if os.path.exists(self.currentbgImg):
            self.imgBackground.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(self.currentbgImg, self.imgBgWidth, self.imgBgHeight))
            self.fleChooser.set_filename(self.currentbgImg)
        #self.fleChooser.set_default_response(gtk.RESPONSE_OK)
        fleFilter = gtk.FileFilter()
        fleFilter.set_name("Images")
        fleFilter.add_mime_type("image/png")
        fleFilter.add_mime_type("image/jpeg")
        fleFilter.add_mime_type("image/gif")
        fleFilter.add_pattern("*.png")
        fleFilter.add_pattern("*.jpg")
        fleFilter.add_pattern("*.gif")
        self.fleChooser.add_filter(fleFilter)
        self.fleChooser.set_current_folder(desktopbaseDir)

        # Set Theme Chooser
        # TODO: get dir path with correct case
        self.curThemeDir = themeDir
        if self.currentTheme is not None:
            self.log.write('Search %s in %s' % (self.currentTheme, themeDir), 'LightDMManager.main', 'debug')
            themeInfo = self.getGtkTheme(themeDir, self.currentTheme)
            if themeInfo[0] == '':
                self.log.write('Search %s in %s' % (self.currentTheme, themeDirLocal), 'LightDMManager.main', 'debug')
                themeInfo = self.getGtkTheme(themeDirLocal, self.currentTheme)
                if themeInfo[0] != '':
                    self.curThemeDir = themeInfo[0]
            else:
                self.curThemeDir = themeInfo[0]
        self.log.write('Current theme directory: %s' % self.curThemeDir, 'LightDMManager.main', 'debug')
        self.fleChooserTheme.set_current_folder(self.curThemeDir)

        # Show users menu
        self.showMenuUsers()

        self.version = functions.getPackageVersion('lightdm-manager')
        functions.pushMessage(self.statusbar, self.version)

        # Show window and keep it on top of other windows
        #self.window.set_keep_above(True)
        gtk.main()

    def destroy(self, widget, data=None):
        # Close the app
        gtk.main_quit()


if __name__ == '__main__':
    # Flush print when it's called
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # Create an instance of our GTK application
    app = LightDMManager()

    # Very dirty: replace the : back again with -
    # before passing the arguments
    args = sys.argv[1:]
    for i in range(len(args)):
        args[i] = string.replace(args[i], ':', '-')
    app.main(args)
