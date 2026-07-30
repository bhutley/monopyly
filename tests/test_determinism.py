import random
from monopyly import *
from monopyly.game.dice import Dice
from testing_utils import *


class TranscriptLogHandler(object):
    '''
    A log handler which keeps every message it is given, so that two
    games can be compared turn by turn.
    '''

    def __init__(self):
        '''
        The 'constructor'.
        '''
        self.messages = []

    def handle_log_message(self, message, level, indent_level):
        '''
        Stores the message.

        We skip the message reporting how much processing time an AI has
        left, as that is wall-clock and so is never reproducible. Note that
        the AI time budget can therefore still make a game diverge, if an
        AI is close to running out of time...
        '''
        if message.startswith("Processing time remaining"):
            return
        self.messages.append((indent_level, message))


class Buyer(PlayerAIBase):
    '''
    An AI which plays enough of the game to exercise the dice, the cards,
    auctions and house building...
    '''

    def __init__(self, name):
        '''
        The 'constructor'.
        '''
        self._name = name

    def get_name(self):
        '''
        Returns the name of this AI.
        '''
        return self._name

    def landed_on_unowned_property(self, game_state, player, property):
        '''
        Buys anything we can afford.
        '''
        if player.state.cash > property.price:
            return PlayerAIBase.Action.BUY
        return PlayerAIBase.Action.DO_NOT_BUY

    def property_offered_for_auction(self, game_state, player, property):
        '''
        Bids half the face value.
        '''
        return int(property.price / 2)

    def get_out_of_jail(self, game_state, player):
        '''
        Always pays to get out of jail.
        '''
        return PlayerAIBase.Action.BUY_WAY_OUT_OF_JAIL

    def build_houses(self, game_state, player):
        '''
        Builds one house on each property of each complete set we own.

        Note that we walk the board in index order rather than iterating
        player.state.owned_unmortgaged_sets. That collection is a set, so
        iterating it gives a different order each game and the resulting
        build order makes the game diverge...
        '''
        owned_sets = player.state.owned_unmortgaged_sets
        instructions = []
        for square in game_state.board.squares:
            if type(square) is Street and square.property_set in owned_sets:
                instructions.append((square, 1))
        return instructions


def _play_seeded_game(seed):
    '''
    Plays one four-player game driven by the seed passed in and returns
    the transcript of everything logged, along with the game.
    '''
    handler = TranscriptLogHandler()
    Logger.add_handler(handler)
    try:
        game = Game(rng=random.Random(seed))
        for player_number in range(4):
            game.add_player((Buyer("Buyer {0}".format(player_number)), player_number))
        game.play_game()
    finally:
        Logger.remove_handler(handler)

    return handler.messages, game


def test_same_seed_gives_identical_transcript():
    '''
    Tests that two games played with equally-seeded rngs play out exactly
    the same way, message for message.
    '''
    first_transcript, first_game = _play_seeded_game(12345)
    second_transcript, second_game = _play_seeded_game(12345)

    # The games should have gone on for the same length of time...
    assert first_game.number_of_rounds_played == second_game.number_of_rounds_played

    # And every single logged message should match...
    assert len(first_transcript) > 100
    assert first_transcript == second_transcript


def test_different_seeds_give_different_transcripts():
    '''
    Tests that the seed actually does something, ie that we have not
    accidentally made the game deterministic regardless of the seed.
    '''
    first_transcript, _ = _play_seeded_game(12345)
    second_transcript, _ = _play_seeded_game(54321)

    assert first_transcript != second_transcript


def test_dice_are_seeded():
    '''
    Tests that the dice honour the rng passed to them.
    '''
    first_dice = Dice(random.Random(99))
    second_dice = Dice(random.Random(99))

    first_rolls = [first_dice.roll() for _ in range(20)]
    second_rolls = [second_dice.roll() for _ in range(20)]

    assert first_rolls == second_rolls

    # A different seed should give different rolls...
    third_dice = Dice(random.Random(100))
    third_rolls = [third_dice.roll() for _ in range(20)]
    assert first_rolls != third_rolls


def test_cards_are_seeded():
    '''
    Tests that the card decks honour the rng passed to them.
    '''
    first_deck = ChanceDeck(random.Random(7))
    second_deck = ChanceDeck(random.Random(7))

    first_indexes = [first_deck._get_next_index() for _ in range(20)]
    second_indexes = [second_deck._get_next_index() for _ in range(20)]

    assert first_indexes == second_indexes


def test_unseeded_games_are_still_random():
    '''
    Tests that a Game created without an rng still plays differently each
    time, ie that we have not made the default behaviour deterministic.
    '''
    def play_unseeded():
        handler = TranscriptLogHandler()
        Logger.add_handler(handler)
        try:
            game = Game()
            for player_number in range(4):
                game.add_player((Buyer("Buyer {0}".format(player_number)), player_number))
            game.play_game()
        finally:
            Logger.remove_handler(handler)
        return handler.messages

    assert play_unseeded() != play_unseeded()


def test_round_limits_are_configurable():
    '''
    Tests that the round cap and the eminent-domain round can be set when
    the game is constructed. Shorter games are used when training
    reinforcement-learning AIs.
    '''
    game = Game(rng=random.Random(1), maximum_rounds=20, eminent_domain_round=10)
    assert game.maximum_rounds == 20
    assert game.eminent_domain_round == 10

    for player_number in range(4):
        game.add_player((DefaultPlayerAI(), player_number))
    game.play_game()

    # The default AIs never buy anything, so nobody can go bankrupt and
    # the game must stop at the round cap...
    assert game.number_of_rounds_played == 20
