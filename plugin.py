import sys
import random
from pprint import pprint

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.schedule as schedule
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Aurora(callbacks.Plugin):
	_rouletteChamber = random.randrange(0, 6)
	_rouletteBullet = random.randrange(0, 6)
	def rroulette(self, irc, msg, args, spin):
		"""[spin]

		Fires the revolver.  If the bullet was in the chamber, you're dead.
		Tell me to spin the chambers and I will.
		"""
		pprint(irc)
		pprint(msg)
		pprint(args)
		pprint(spin)
		if spin:
			self._rouletteBullet = random.randrange(0, 6)
			irc.reply('*SPIN* Are you feeling lucky?', prefixNick=False)
			return
		channel = msg.args[0]
		if self._rouletteChamber == self._rouletteBullet:
			self._rouletteBullet = random.randrange(0, 6)
			self._rouletteChamber = random.randrange(0, 6)
			if irc.nick in irc.state.channels[channel].ops or irc.nick in irc.state.channels[channel].halfops:
				try:
					bannedHostmask = irc.state.nickToHostmask(msg.nick)
				except KeyError:
					irc.error(format('I haven\'t seen %s.', msg.nick), Raise=True)
				banmaskstyle = conf.supybot.protocols.irc.banmask
				banmask = banmaskstyle.makeBanmask(bannedHostmask, ["nick", "host"])
				if ircutils.hostmaskPatternEqual(banmask, irc.prefix):
					if ircutils.hostmaskPatternEqual(bannedHostmask, irc.prefix):
						self.log.warning('%q played rroulette, but he\'s got the same hostmask as me, strangely enough.',msg.prefix)
						irc.error('I\'m not playing this game.')
						return
					else:
						self.log.warning('Using exact hostmask since banmask would '
						'ban myself.')
						banmask = bannedHostmask
						def f():
							if channel in irc.state.channels and banmask in irc.state.channels[channel].bans:
								irc.queueMsg(ircmsgs.unban(channel, banmask))
						schedule.addEvent(f, 60)
				irc.queueMsg(ircmsgs.ban(channel, banmask))
				irc.queueMsg(ircmsgs.kick(channel, msg.nick, 'BANG!'))
			else:
				irc.reply('*BANG* Hey, who put a blank in here?!',
				prefixNick=False)
				irc.reply('reloads and spins the chambers.', action=True)
		else:
			irc.reply('*click*')
			self._rouletteChamber += 1
			self._rouletteChamber %= 6
	rroulette = wrap(rroulette, ['public', additional(('literal', 'spin'))])

Class = Aurora