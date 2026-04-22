from math import ceil


class CompactSeed:

    def __init__(self, wordlist: list[str]):
        self.wordlist: list[str] = wordlist

    def bytes(self, words: list[str]) -> bytes:
        return self.idx2bytes([self.wordlist.index(word) for word in words])

    def words(self, cs: bytes) -> list[str]:
        return [self.wordlist[idx] for idx in self.bytes2idx(cs)]

    @staticmethod
    def length(cs: bytes) -> int:
        return ceil((len(cs) * 8) / 11)

    @staticmethod
    def idx2bytes(idx_list: list[int]) -> bytes:
        idxbin = ''.join([f'{idx:>011b}' for idx in idx_list])
        if len(idxbin) % 8 != 0:
            idxbin += '0' * (8 - len(idxbin) % 8)
        idxbytes = b''
        for i in range(0, len(idxbin), 8):
            idxbytes  += int(idxbin[i:i+8], 2).to_bytes(1, byteorder='big')
        return idxbytes

    @staticmethod
    def bytes2idx(data: bytes) -> list[int]:
        idxbin = ''.join(format(byte, '08b') for byte in data)
        idxbin = idxbin[:(len(idxbin) // 11) * 11]  # Remove excess bits
        idx_list = []
        for i in range(0, len(idxbin), 11):
            idx_list.append(int(idxbin[i:i+11], 2))
        return idx_list

    def test_length(self, words: list[str]) -> bool:
        return self.length(self.bytes(words)) == len(words)

    def test_bytes(self, words: list[str]) -> bool:
        return self.words(self.bytes(words)) == words

    def test(self, words: list[str]) -> bool:
        return self.test_length(words) and self.test_bytes(words)
