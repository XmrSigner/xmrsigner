# TODO: remove after migration to OTS


class ShortSeed:

    def __init__(self, wordlist: list[str], letters: int = 4):
        self.wordlist: list[str] = wordlist
        self.letters: int = letters
        self.shortlist: list[str] = [word[:self.letters] for word in self.wordlist]

    def expand(self, shortlist: list[str]) -> list[str]:
        return [self.wordlist[self.shortlist.index(word[:self.letters])] for word in shortlist]

    def reduce(self, completelist: list[str]) -> list[str]:
        return [word[:self.letters] for word in completelist]

    def test(self, completelist: list[str]) -> bool:
        return self.expand(self.reduce(completelist)) == completelist
