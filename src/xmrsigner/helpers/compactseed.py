from math import ceil


from ots.seed import SeedIndices


class CompactSeed:

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

    @classmethod
    def seedIndices2bytes(cls, seedIndices: SeedIndices) -> bytes:
        return cls.idx2bytes(seedIndices.values)

    @classmethod
    def bytes2seedIndices(cls, data: bytes) -> SeedIndices:
        return SeedIndices.fromValues(cls.bytes2idx(data))
