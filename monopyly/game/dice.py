import random


class Dice(object):
    '''
    Generates random numbers by rolling two 'dice'.

    The reason for this class existing is so that it can be
    mocked and replaced with a deterministic version for
    testing.
    '''

    def __init__(self, rng=None):
        '''
        The 'constructor'.

        You can pass a random.Random to make the rolls reproducible. If you
        do not, we create our own, so the rolls are unpredictable...
        '''
        self._rng = rng if rng is not None else random.Random()

    def roll(self):
        '''
        Returns two value: the rolls of the two dice.
        '''
        roll1 = self._rng.randint(1, 6)
        roll2 = self._rng.randint(1, 6)
        return roll1, roll2
