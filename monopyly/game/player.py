from .player_state import PlayerState
from .player_ai_base import PlayerAIBase
from ..squares import Property, Street
from ..utility import Logger
import time


class Player(object):
    '''
    Holds the PlayerState and a player AI (an object
    derived from PlayerAIBase).
    '''

    def __init__(self, ai, player_number, board):
        '''
        The 'constructor'.
        '''
        self.state = PlayerState()
        self.ai = ai
        self.board = board
        self.player_number = player_number

    def owns_properties(self, properties):
        '''
        Returns True if this player owns all the properties passed in,
        False if not (or if any of the squares passed in are no properties).
        '''
        # We check each property...
        for square in properties:
            # We check that the square is a property...
            if not isinstance(square, Property):
                return False

            if square.owner is not self:
                return False

        return True

    @property
    def net_worth(self):
        '''
        Returns the player's net worth, which includes their
        cash, properties and houses.
        '''
        # Net worth includes cash...
        total = self.state.cash

        for property in self.state.properties:
            # We add the mortgage value of properties...
            if not property.is_mortgaged:
                total += property.mortgage_value

            # We add the resale value of houses...
            if type(property) == Street:
                total += int(property.house_price/2 * property.number_of_houses)

        return total

    @property
    def name(self):
        '''
        Returns the player name.

        The name is used in log messages throughout the engine, including
        from places which are not inside call_ai, so we do not let a broken
        get_name() bring the game down...
        '''
        try:
            return self.ai.get_name()
        except Exception:
            return "Player {0} (get_name failed)".format(self.player_number)

    def is_same_player(self, other):
        '''
        Returns true if the other player is the same as this one.

        'other' can be either a Player object or a Player AI object.
        '''
        if other is self:
            return True

        if other is self.ai:
            return True

        return False

    def call_ai(self, function, *args):
        '''
        Calls the function passed in, times it and updates the
        total time used by this player.

        The functions will be the AI methods.

        If the AI raises an exception we catch it and forfeit the decision
        to the default behaviour documented in PlayerAIBase. This keeps one
        broken AI from bringing down a whole game (or a whole tournament).
        The exception is counted against the player, and the Game
        disqualifies players who keep throwing...
        '''
        # We call the function and time how long the AI spends processing it...
        start = time.perf_counter()
        try:
            result = function(*args)
        except Exception as exception:
            result = self._handle_ai_exception(function, exception, *args)
        finally:
            # We update the time the AI has remaining for the current game.
            # We do this even if the AI threw, so that a broken AI is still
            # charged for the time it burned...
            elapsed_seconds = time.perf_counter() - start
            self.state.ai_processing_seconds_remaining -= elapsed_seconds
            self.state.ai_processing_seconds_used += elapsed_seconds

        # And return what the function returned...
        return result

    def _handle_ai_exception(self, function, exception, *args):
        '''
        Called when an AI method has raised an exception.

        We log it, count it against the player, tell the AI about it and
        return the default behaviour for the method so that the game can
        carry on...
        '''
        function_name = getattr(function, "__name__", "(unknown)")
        message = "{0} raised {1} in {2}: {3}".format(
            self.name, type(exception).__name__, function_name, exception)
        Logger.log(message, Logger.WARNING)

        # We count the error against the AI. Game._check_ai_exceptions looks
        # at this and can disqualify the player...
        self.state.ai_exception_count += 1

        # We tell the AI that it misbehaved. A broken AI may well throw
        # again here, so we ignore anything this raises...
        try:
            self.ai.ai_error(message)
        except Exception:
            pass

        return self._default_ai_result(function_name, *args)

    def _default_ai_result(self, function_name, *args):
        '''
        Returns the result of the PlayerAIBase implementation of the method
        named, ie the default behaviour documented for AIs.

        Returns None if PlayerAIBase has no such method, or if the default
        implementation itself raises...
        '''
        default_function = getattr(PlayerAIBase, function_name, None)
        if default_function is None:
            return None

        try:
            return default_function(self.ai, *args)
        except Exception:
            return None


