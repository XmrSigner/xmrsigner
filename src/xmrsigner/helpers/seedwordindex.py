# TODO: remove after migration to OTS

class SeedWordIndex:

    def __init__(self, wordlist: list[str]):
        self.wordlist = wordlist

    def indices(self, words: list[str]) -> list[int]:
        return [self.wordlist.index(word) for word in words]

    def words(self, indices: list[int]) -> list[str]:
        return [self.wordlist[idx] for idx in indices]

    def from_indices_string(self, indices_string: str) -> list[str]:
        return [self.wordlist[int(indices_string[i:i + 4])] for i in range(0, len(indices_string), 4)]

    def to_indices_string(self, words: list[str]) -> str:
        return ''.join([f'{self.wordlist.index(word):04d}' for word in words])

    def test_string(self, words: list[str]) -> bool:
        return self.from_indices_string(self.to_indices_string(words)) == words

    def test_list(self, words: list[str]) -> bool:
        return self.words(self.indices(words)) == words

    def test(self, words: list[str]) -> bool:
        return self.test_string(words) and self.test_list(words)
