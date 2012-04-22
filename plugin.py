import sys
import random
import pprint 

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

    _vkb = []
    _banNick = False
    def vkb(self, irc, msg, args, nicks):
        """nick

        Allowed voiced users to vote to kick other users"""
        
        channel = msg.args[0]
        nick = nicks[0]
        pprint.pprint(msg.nick)
        if msg.nick in irc.state.channels[channel].ops or msg.nick in irc.state.channels[channel].halfops:
            irc.reply("You, sir, are a lazy op. But that's ok.")
            for nick in nicks:
	            self._kban(irc, msg, args, nick, msg.nick + " says to kban you.")
            return
        if not msg.nick in irc.state.channels[channel].voices:
            irc.reply("Sorry, you've got to be voiced before I'd consider trusting your judgement.")
            return
        if nick in irc.state.channels[channel].ops or nick in irc.state.channels[channel].halfops \
        or nick in irc.state.channels[channel].voices:
            irc.reply("AHHAHA. You want to vote to kick a trusted person? Good joke, good joke...")
            return
        if self._banNick and self._banNick == nick:
            self.log.info("Kickbanning %s after 2 votes", nick)
            self._kban(irc, msg, args, nick, "Apparently, you're being bad enough that people want to get rid of you.")
        else:
        	irc.reply("No existing vote to kick...")

    vkb = wrap(vkb, ['public', any('nickInChannel')] )

# copied from channel plugin
    def _kban(self, irc, msg, args, bannedNick, reason):
    # Check that they're not trying to make us kickban ourself.
        channel = msg.args[0]
        if not irc.isNick(bannedNick[0]):
            self.log.warning('%q tried to kban a non nick: %q',
                             msg.prefix, bannedNick)
            raise callbacks.ArgumentError
        elif bannedNick == irc.nick:
            self.log.warning('%q tried to make me kban myself.', msg.prefix)
            irc.error('I cowardly refuse to kickban myself.')
            return
        if not reason:
            reason = msg.nick
        try:
            bannedHostmask = irc.state.nickToHostmask(bannedNick)
        except KeyError:
            irc.error(format('I haven\'t seen %s.', bannedNick), Raise=True)
        capability = ircdb.makeChannelCapability(channel, 'op')
        banmaskstyle = conf.supybot.protocols.irc.banmask
        banmask = banmaskstyle.makeBanmask(bannedHostmask, ["host", "user"])
        # Check (again) that they're not trying to make us kickban ourself.
        if ircutils.hostmaskPatternEqual(banmask, irc.prefix):
            if ircutils.hostmaskPatternEqual(bannedHostmask, irc.prefix):
                self.log.warning('%q tried to make me kban myself.',msg.prefix)
                irc.error('I cowardly refuse to ban myself.')
                return
            else:
                self.log.warning('Using exact hostmask since banmask would '
                                 'ban myself.')
                banmask = bannedHostmask
        # Now, let's actually get to it.  Check to make sure they have
        # #channel,op and the bannee doesn't have #channel,op; or that the
        # bannee and the banner are both the same person.
        def doBan():
            if irc.state.channels[channel].isOp(bannedNick):
                irc.queueMsg(ircmsgs.deop(channel, bannedNick))
            irc.queueMsg(ircmsgs.ban(channel, banmask))
            irc.queueMsg(ircmsgs.kick(channel, bannedNick, reason))
            def f():
                if channel in irc.state.channels and \
                   banmask in irc.state.channels[channel].bans:
                    irc.queueMsg(ircmsgs.unban(channel, banmask))
            schedule.addEvent(f, 3600)
        if bannedNick == msg.nick:
            doBan()
        elif ircdb.checkCapability(msg.prefix, capability):
            if ircdb.checkCapability(bannedHostmask, capability):
                self.log.warning('%s tried to ban %q, but both have %s',
                                 msg.prefix, bannedHostmask, capability)
                irc.error(format('%s has %s too, you can\'t ban him/her/it.',
                                 bannedNick, capability))
            else:
                doBan()
        else:
            self.log.warning('%q attempted kban without %s',
                             msg.prefix, capability)
            irc.errorNoCapability(capability)
            exact,nick,user,host


Class = Aurora