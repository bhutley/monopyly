from monopyly import *
from testing_utils import *


class ThrowingAI(PlayerAIBase):
    '''
    An AI which throws from the methods named when it is constructed.

    Used to check that the engine survives broken AIs...
    '''

    def __init__(self, throw_from=(), name="Thrower"):
        '''
        The 'constructor'.

        throw_from is a collection of the names of the methods which
        should raise...
        '''
        self._throw_from = set(throw_from)
        self._name = name
        self.errors_reported = []

    def get_name(self):
        '''
        Returns the name of this AI.
        '''
        self._maybe_throw("get_name")
        return self._name

    def ai_error(self, message):
        '''
        Records the errors the engine tells us about.
        '''
        self.errors_reported.append(message)

    def landed_on_unowned_property(self, game_state, player, property):
        '''
        Buys the property, unless we are told to throw.
        '''
        self._maybe_throw("landed_on_unowned_property")
        return PlayerAIBase.Action.BUY

    def property_offered_for_auction(self, game_state, player, property):
        '''
        Does not bid, unless we are told to throw. We keep the base class
        behaviour here so that a forfeited buy decision does not turn into
        a purchase at auction instead...
        '''
        self._maybe_throw("property_offered_for_auction")
        return 0

    def build_houses(self, game_state, player):
        '''
        Builds nothing, unless we are told to throw.
        '''
        self._maybe_throw("build_houses")
        return []

    def start_of_turn(self, game_state, player):
        '''
        Does nothing, unless we are told to throw.
        '''
        self._maybe_throw("start_of_turn")

    def game_over(self, winner, maximum_rounds_played):
        '''
        Does nothing, unless we are told to throw.
        '''
        self._maybe_throw("game_over")

    def _maybe_throw(self, function_name):
        '''
        Raises if we were told to throw from the function named.
        '''
        if function_name in self._throw_from:
            raise ValueError("deliberate failure in {0}".format(function_name))


class DisqualificationWatcher(PlayerAIBase):
    '''
    An AI which records the players it is told were disqualified.
    '''

    def __init__(self):
        '''
        The 'constructor'.
        '''
        self.disqualified_players = []

    def get_name(self):
        '''
        Returns the name of this AI.
        '''
        return "Watcher"

    def player_was_disqualified(self, player):
        '''
        Records the disqualified player.
        '''
        self.disqualified_players.append(player)


def test_exception_forfeits_the_decision_to_the_default():
    '''
    Tests that an AI which throws from landed_on_unowned_property does not
    buy the property, ie that the decision falls back to the documented
    default of DO_NOT_BUY.
    '''
    game = Game()
    ai = ThrowingAI(throw_from=["landed_on_unowned_property"])
    player = game.add_player(ai)
    game.dice = MockDice([(1, 2)])

    # The player would buy The Angel Islington if it were not throwing...
    game.play_one_turn(player)

    # The default is DO_NOT_BUY, so the player should still have all
    # their money and no properties...
    assert player.state.cash == 1500
    assert len(player.state.properties) == 0

    # The exception should have been counted and reported to the AI...
    assert player.state.ai_exception_count == 1
    assert len(ai.errors_reported) == 1
    assert "landed_on_unowned_property" in ai.errors_reported[0]
    assert "ValueError" in ai.errors_reported[0]


def test_exception_does_not_stop_the_game():
    '''
    Tests that a game plays to completion even when one AI throws from
    every method it can.
    '''
    thrower = ThrowingAI(
        throw_from=[
            "get_name",
            "start_of_turn",
            "landed_on_unowned_property",
            "property_offered_for_auction",
            "build_houses",
            "game_over"],
        name="Broken")

    game = Game(maximum_rounds=30)
    game.add_player((thrower, 0))
    game.add_player((DefaultPlayerAI(), 1))

    # This must not raise...
    game.play_game()

    assert game.number_of_rounds_played > 0


def test_throwing_get_name_does_not_stop_the_game():
    '''
    Tests that the engine copes with an AI whose get_name throws, as the
    name is used in log messages from all over the engine.
    '''
    ai = ThrowingAI(throw_from=["get_name"])
    game = Game(maximum_rounds=5)
    player = game.add_player((ai, 0))
    game.add_player((DefaultPlayerAI(), 1))

    # Asking for the name must not raise...
    assert "get_name failed" in player.name

    game.play_game()
    assert game.number_of_rounds_played == 5


def test_time_is_charged_even_when_the_ai_throws():
    '''
    Tests that an AI which throws is still charged the processing time it
    used, so that a broken AI cannot get free CPU.
    '''
    game = Game()
    ai = ThrowingAI(throw_from=["build_houses"])
    player = game.add_player(ai)

    seconds_before = player.state.ai_processing_seconds_remaining
    player.call_ai(ai.build_houses, game.state, player)

    assert player.state.ai_processing_seconds_remaining < seconds_before
    assert player.state.ai_processing_seconds_used > 0.0


def test_repeated_exceptions_disqualify_the_player():
    '''
    Tests that an AI which keeps throwing is removed from the game, and
    that the other players are told about it.
    '''
    thrower = ThrowingAI(throw_from=["start_of_turn"], name="Broken")
    watcher = DisqualificationWatcher()

    game = Game(maximum_rounds=100)
    game.maximum_ai_exceptions = 3
    throwing_player = game.add_player((thrower, 0))
    game.add_player((watcher, 1))

    game.play_game()

    # The thrower should have been disqualified and moved to the
    # bankrupt list...
    assert throwing_player not in game.state.players
    assert throwing_player in game.state.bankrupt_players

    # The other player should have been notified once...
    assert watcher.disqualified_players == [throwing_player]

    # And should have won by default...
    assert game.winner is not None
    assert game.winner.name == "Watcher"


def test_well_behaved_ai_is_never_disqualified():
    '''
    Tests that the disqualification machinery does not fire for an AI
    which behaves itself.
    '''
    game = Game(maximum_rounds=20)
    game.maximum_ai_exceptions = 0
    first_player = game.add_player((DefaultPlayerAI(), 0))
    second_player = game.add_player((DefaultPlayerAI(), 1))

    game.play_game()

    assert first_player.state.ai_exception_count == 0
    assert second_player.state.ai_exception_count == 0
    assert first_player in game.state.players
    assert second_player in game.state.players
