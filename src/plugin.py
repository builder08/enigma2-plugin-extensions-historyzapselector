# Coded by vlamo /Dimitrij

from . import _
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Screens.ChannelSelection import ChannelSelection
from Screens.InfoBarGenerics import InfoBarChannelSelection
from enigma import eServiceCenter, eActionMap
from HistoryZap import HistoryZapSelector
from Components.Pixmap import Pixmap, MultiPixmap
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, getConfigListEntry,ConfigYesNo, NoSave
from Screens.MessageBox import MessageBox
from keyids import KEYIDS
from Components.Button import Button
from Tools.BoundFunction import boundFunction
import Components.ParentalControl
from time import localtime, time
try:
	from Plugins.SystemPlugins.AutoCamSetup.autocam import hew_setHistoryPath
	UseAutoCamSetup = True
except:
	UseAutoCamSetup = False

PLUGIN_VERSION = _(" ver. ") + "2.4"

HistoryZapSelectorKeys = [
	["none",_("standard <  >"),["KEY_RESERVED","KEY_RESERVED"]],
	["LeftRight",_("only LEFT/RIGHT"),["KEY_LEFT","KEY_RIGHT"]],
	["TextHelp",_("only TEXT/HELP"),["KEY_TEXT","KEY_HELP"]],
	["Bouquet",_("only CH+/-,B+/-,P+/-"),["KEY_CHANNELUP","KEY_CHANNELDOWN"]],
]

config.plugins.SetupZapSelector = ConfigSubsection()
config.plugins.SetupZapSelector.start = ConfigYesNo(default = True)
config.plugins.SetupZapSelector.history = ConfigInteger(20, limits = (1,60))
config.plugins.SetupZapSelector.event = ConfigSelection(choices = {"0": _("default (only service name)"), "1": _("event name"), "2": _("event name and description")}, default="0")
config.plugins.SetupZapSelector.duration = ConfigYesNo(default = False)
config.plugins.SetupZapSelector.duration_type = ConfigSelection(choices = {"0": _("remaining minutes"), "1": _("progress bar")}, default="0")
config.plugins.SetupZapSelector.picon = ConfigYesNo(default = False)
config.plugins.SetupZapSelector.preview = NoSave(ConfigYesNo(default = False))
config.plugins.SetupZapSelector.number_zap = ConfigYesNo(default = False)
config.plugins.SetupZapSelector.replace_keys = ConfigSelection([(x[0],x[1]) for x in HistoryZapSelectorKeys], "none")
config.plugins.SetupZapSelector.show_button = ConfigYesNo(default = False)
config.plugins.SetupZapSelector.warning_message = ConfigYesNo(default = True)
config.plugins.SetupZapSelector.pip_zap = ConfigSelection(choices = {"0": _("disabled"), "1": _("show options list"), "2": _("only Pipzap"), "3": _("only standard PiP"), "4": _("enabled")}, default="0")

HISTORYSIZE = config.plugins.SetupZapSelector.history.value

class HistoryZapInfoBar:
	def __init__(self, session, infobar):
		self.session = session
		self.infobar = infobar
		self.lastKey = None
		self.hotkeys = { }
		for x in HistoryZapSelectorKeys:
			self.hotkeys[x[0]] = [KEYIDS[key] for key in x[2]]
		eActionMap.getInstance().bindAction('', -10, self.keyPressed)

	def keyPressed(self, key, flag):
		if not config.plugins.SetupZapSelector.start.value:
			return 0
		if config.plugins.SetupZapSelector.replace_keys.value == "none":
			return 0
		for k in self.hotkeys[config.plugins.SetupZapSelector.replace_keys.value]:
			if key == k and self.session.current_dialog == self.infobar:
				if flag == 0:
					self.lastKey = key
				elif self.lastKey != key or flag == 4:
					self.lastKey = None
					continue
				elif flag == 3:
					self.lastKey = None
					continue
				elif flag == 1:
					self.lastKey = None
					if InfoBarChannelSelection_instance is not None:
						historyZap(InfoBarChannelSelection_instance, key == self.hotkeys[config.plugins.SetupZapSelector.replace_keys.value][0] and -1 or +1)
				return 1
		return 0

class SetupZapSelectorScreen(Screen, ConfigListScreen):
	global PLUGIN_VERSION
	skin = """
		<screen position="center,center" size="510,340" >
		<widget name="config" position="5,5" size="500,290" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="180,300" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="5,300" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="360,300" zPosition="0" size="140,40" alphatest="on" />
		<widget name="clear" position="360,300" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="blue" />
		<widget name="ok" position="180,300" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="5,300" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session, args=None):
		self.skin = SetupZapSelectorScreen.skin
		self.setup_title = _("Setup Zap History:") + PLUGIN_VERSION
		Screen.__init__(self, session)

		self["ok"] = Button(_("Save"))
		self["cancel"] = Button(_("Cancel"))
		self["clear"] = Button(_("Clear History"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions"], 
		{
			"ok": self.keyOk,
			"save": self.keyGreen,
			"cancel": self.keyRed,
			"blue": self.keyBlue,
		}, -2)
		ConfigListScreen.__init__(self, [])
		self.initConfig()
		self.createSetup()
		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __closed(self):
		pass

	def __layoutFinished(self):
		self.setTitle(self.setup_title)

	def initConfig(self):
		def getPrevValues(section):
			res = { }
			for (key,val) in section.content.items.items():
				if isinstance(val, ConfigSubsection):
					res[key] = getPrevValues(val)
				else:
					res[key] = val.value
			return res

		self.ZAP = config.plugins.SetupZapSelector
		self.prev_values = getPrevValues(self.ZAP)
		self.cfg_start = getConfigListEntry(_("Enable Zap History"), self.ZAP.start)
		self.cfg_history = getConfigListEntry(_("Maximum zap history entries"), self.ZAP.history)
		self.cfg_event  = getConfigListEntry(_("Style services list"), self.ZAP.event)
		self.cfg_duration = getConfigListEntry(_("Show duration events"), self.ZAP.duration)
		self.cfg_duration_type = getConfigListEntry(_("Duration type"), self.ZAP.duration_type)
		self.cfg_picon = getConfigListEntry(_("Use picons"), self.ZAP.picon)
		self.cfg_number_zap = getConfigListEntry(_("Use number zap"), self.ZAP.number_zap)
		self.cfg_pip_zap = getConfigListEntry(_("Zap focus PiP (if only enabled)"), self.ZAP.pip_zap)
		self.cfg_warning_message = getConfigListEntry(_("Show warning message before action"), self.ZAP.warning_message)
		self.cfg_show_button = getConfigListEntry(_("Show panel buttons on display"), self.ZAP.show_button)
		self.cfg_replace_keys = getConfigListEntry(_("Behavior of keys for use"), self.ZAP.replace_keys)

	def createSetup(self):
		list = [ self.cfg_start ]
		if self.ZAP.start.value:
			list.append(self.cfg_history)
			list.append(self.cfg_event)
			if self.ZAP.event.value != "0":
				list.append(self.cfg_duration)
				if self.ZAP.duration.value:
					list.append(self.cfg_duration_type)
				list.append(self.cfg_picon)
			list.append(self.cfg_number_zap)
			list.append(self.cfg_show_button)
			list.append(self.cfg_pip_zap)
			list.append(self.cfg_warning_message)
			#list.append(self.cfg_replace_keys)
		self["config"].list = list
		self["config"].l.setList(list)

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur in (self.cfg_start, self.cfg_history, self.cfg_event, self.cfg_duration):
			self.createSetup()

	def keyOk(self):
		pass

	def keyRed(self):
		def setPrevValues(section, values):
			for (key,val) in section.content.items.items():
				value = values.get(key, None)
				if value is not None:
					if isinstance(val, ConfigSubsection):
						setPrevValues(val, value)
					else:
						val.value = value
		setPrevValues(self.ZAP, self.prev_values)
		self.keyGreen()

	def keyGreen(self):
		global HISTORYSIZE
		if not self.ZAP.start.value:
			self.ZAP.event.value = "0"
		if self.ZAP.event.value == "0":
			self.ZAP.duration.value = False
			self.ZAP.picon.value = False
		if not self.ZAP.duration.value:
			self.ZAP.duration_type.value = "0" 
		if self.ZAP.replace_keys.value != "none":
			self.ZAP.replace_keys.value = "none"
		self.ZAP.save()
		HISTORYSIZE = self.ZAP.history.value
		self.close()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keyBlue(self):
		if InfoBarChannelSelection_instance and historyClear(InfoBarChannelSelection_instance):
			txt = _("History list clean is successed!")
		else:
			txt = _("History list clean is failed!")
		self.session.open(MessageBox, txt, MessageBox.TYPE_INFO, timeout = 3)
		self.close()

baseInfoBarChannelSelection__init__ = None
InfoBarChannelSelection_instance = None
oldInfoBar__init__ = None
PrevHistoryBack = None
PrevhistoryNext = None

def newInfoBarChannelSelection__init__(self):
	baseInfoBarChannelSelection__init__(self)
	global InfoBarChannelSelection_instance
	InfoBarChannelSelection_instance = self

def historyBack(self):
	if not config.plugins.SetupZapSelector.start.value:
		if PrevHistoryBack is not None:
			PrevHistoryBack(self)
	elif config.plugins.SetupZapSelector.replace_keys.value != "none":
		if PrevHistoryBack is not None:
			PrevHistoryBack(self)
	else:
		self.historyZap(-1)

def historyNext(self):
	if not config.plugins.SetupZapSelector.start.value:
		if PrevhistoryNext is not None:
			PrevhistoryNext(self)
	elif config.plugins.SetupZapSelector.replace_keys.value != "none":
		if PrevhistoryNext is not None:
			PrevhistoryNext(self)
	else:
		self.historyZap(+1)

def historyClear(self):
	if self and self.servicelist:
		for i in range(0, len(self.servicelist.history)-1):
			del self.servicelist.history[0]
		self.servicelist.history_pos = len(self.servicelist.history)-1
		return True
	return False

def historyDeleteCurrentEntry(self, ref):
	if ref:
		if self and self.servicelist:
			hlen = len(self.servicelist.history)
			x = 0
			while x < hlen-1:
				if self.servicelist.history[x][-1] == ref:
					try:
						del self.servicelist.history[x]
						hlen -= 1
						self.servicelist.history_pos = hlen-1
						return True
					except:
						pass
				else:
					x += 1
	return False

def historyZap(self, direction):
	hlen = len(self.servicelist.history)
	if hlen < 1: return
	mark = self.servicelist.history_pos
	selpos = self.servicelist.history_pos + direction
	if selpos < 0: selpos = 0
	if selpos > hlen-1: selpos = hlen-1
	serviceHandler = eServiceCenter.getInstance()
	historylist = [ ]
	for x in self.servicelist.history:
		info = serviceHandler.info(x[-1])
		if info:
			serviceName = info.getName(x[-1])
			if serviceName is None:
				serviceName = ""
			eventName = ""
			if config.plugins.SetupZapSelector.duration_type.value == "1":
				durationTime = -1
			else:
				durationTime = ""
			descriptionName = ""
			if config.plugins.SetupZapSelector.event.value != "0":
				event = info.getEvent(x[-1])
				if event:
					eventName = event.getEventName()
					if eventName is None:
						eventName = ""
					else:
						eventName = eventName.replace('|', '').replace('(18+)', '').replace('18+', '').replace('(16+)', '').replace('16+', '').replace('(12+)', '').replace('12+', '').replace('(7+)', '').replace('7+', '').replace('(6+)', '').replace('6+', '').replace('(0+)', '').replace('0+', '')	
					if config.plugins.SetupZapSelector.event.value == "2":
						descriptionName = event.getShortDescription()
						if descriptionName is None or descriptionName == "":
							descriptionName = event.getExtendedDescription()
							if descriptionName is None:
								descriptionName = ""
					if config.plugins.SetupZapSelector.duration.value:
						try:
							begin = event.getBeginTime()
							if begin is not None:
								end = begin + event.getDuration()
								if config.plugins.SetupZapSelector.duration_type.value == "1":
									i = (int(time()) - begin) * 100 / event.getDuration()
									if i < 101:
										durationTime = i
								else:
									remaining = (end - int(time())) / 60
									prefix = ""
									if remaining > 0:
										prefix = "+"
									local_begin = localtime(begin)
									local_end = localtime(end)
									durationTime = _('%02d.%02d - %02d.%02d (%s%d min)') % (local_begin[3],local_begin[4],local_end[3],local_end[4],prefix,remaining)
						except:
							pass
			historylist.append((serviceName, x[-1], eventName, descriptionName, durationTime))
	self.session.openWithCallback(self.historyMenuClosed, HistoryZapSelector, historylist, selpos, mark, invert_items=True, redirect_buttons=True, wrap_around=True)

def historyMenuClosed(self, retval, checkTimeshift=True, checkParentalControl=True, ref=None):
	if not retval: return
	hlen = len(self.servicelist.history)
	pos = 0
	for x in self.servicelist.history:
		if x[-1] == retval: break
		pos += 1
	force_zap = config.plugins.SetupZapSelector.preview.value and pos == self.servicelist.history_pos
	if pos < hlen and (pos != self.servicelist.history_pos or force_zap):
		if checkTimeshift:
			try:
				self.checkTimeshiftRunning(boundFunction(self.historyCheckTimeshiftCallback, retval))
			except:
				checkTimeshift = False
		if not checkTimeshift:
			if not checkParentalControl or Components.ParentalControl.parentalControl.isServicePlayable(retval, boundFunction(self.historyMenuClosed, retval, checkTimeshift=False, checkParentalControl=False)):
				if force_zap:
					self.session.nav.playService(retval, checkParentalControl=False, adjust=False)
					return
				tmp = self.servicelist.history[pos]
				self.servicelist.history.append(tmp)
				del self.servicelist.history[pos]
				self.servicelist.history_pos = hlen-1
				oldref = self.session.nav.getCurrentlyPlayingServiceReference()
				self.session.nav.playService(retval, checkParentalControl=False, adjust=False)
				if UseAutoCamSetup:
					try:
						if config.plugins.autoCamSetup.autocam.enabled.value and config.plugins.autoCamSetup.autocam.history_zap.value:
							self.servicelist.setHistoryPath(ref=oldref)
						else:
							self.servicelist.setHistoryPath()
					except:
						self.servicelist.setHistoryPath()
				else:
					self.servicelist.setHistoryPath()

def historyCheckTimeshiftCallback(self, retval, answer):
	if answer:
		self.historyMenuClosed(retval, checkTimeshift=False)

def addToHistory(self, ref):
	if self.servicePath is not None:
		tmp=self.servicePath[:]
		tmp.append(ref)
		self.history.append(tmp)
		hlen = len(self.history)
		x = 0
		while x < hlen-1:
			if self.history[x][-1] == ref:
				del self.history[x]
				hlen -= 1
			else:
				x += 1
		if hlen > HISTORYSIZE:
			del self.history[0]
			hlen -= 1
		self.history_pos = hlen-1

def main(session, **kwargs):
	session.open(SetupZapSelectorScreen)

def zapInfoBar__init__(self, session):
	oldInfoBar__init__(self, session)
	self.zapinfobar = HistoryZapInfoBar(session, self)

def StartMainSession(reason, **kwargs):
	global baseInfoBarChannelSelection__init__, PrevHistoryBack, PrevhistoryNext, oldInfoBar__init__
	if reason == 0:
		#from Screens.InfoBar import InfoBar
		#if oldInfoBar__init__ is None:
		#	oldInfoBar__init__ = InfoBar.__init__
		#InfoBar.__init__ = zapInfoBar__init__
		if baseInfoBarChannelSelection__init__ is None:
			baseInfoBarChannelSelection__init__ = InfoBarChannelSelection.__init__
			InfoBarChannelSelection.__init__ = newInfoBarChannelSelection__init__
			PrevHistoryBack = InfoBarChannelSelection.historyBack
			PrevhistoryNext = InfoBarChannelSelection.historyNext
			InfoBarChannelSelection.historyBack = historyBack
			InfoBarChannelSelection.historyNext = historyNext
			InfoBarChannelSelection.historyZap = historyZap
			InfoBarChannelSelection.historyMenuClosed = historyMenuClosed
			InfoBarChannelSelection.historyCheckTimeshiftCallback = historyCheckTimeshiftCallback
			ChannelSelection.addToHistory = addToHistory

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("HistoryZapSelector"), description=_("History Zap Selector"), where = [PluginDescriptor.WHERE_SESSIONSTART,PluginDescriptor.WHERE_AUTOSTART], fnc = StartMainSession),
		PluginDescriptor(name=_("HistoryZapSelector"), description=_("Settings zap history") + PLUGIN_VERSION, where = PluginDescriptor.WHERE_PLUGINMENU, icon = "zap.png", fnc = main)]
