if __name__ == "__main__":
    import qrcode
    import sys
    from ots.seed import (
        Seed,
        MoneroSeed,
        Polyseed,
        LegacySeed
    )
    from ots.enums import SeedType
    from ots.seed_language import SeedLanguage
    from embit import bip39

    print(sys.argv)
    en: SeedLanguage = SeedLanguage.fromCode('en')
    word_count: int = len(sys.argv[1:])
    phrase: str = ' '.join(sys.argv[1:])
    if word_count not in (12, 13, 16, 24, 25):
        print('Not a valid seed!')
        sys.exit(-1)
    seed: Seed|None = None
    if word_count in (24, 25):
        seed = MoneroSeed.decode(phrase)
    if word_count == 16:
        seed = Polyseed.decode(phrase)
    if word_count in (12, 13):
        seed = LegacySeed.decode(phrase)
    print(seed.phrase(en).insecure())
    data = ''.join([
        str("%04d" % i)
        for i in seed.indices().values
    ])
    print(data)
    qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=3)
    qr.add_data(data)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").resize((240,240)).convert('RGB').show()
