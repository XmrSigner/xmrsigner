from ots.enums import SeedType
from ots.seed_language import SeedLanguage

from .wordlist import Wordlist
from .monero.monero import MoneroWordlist
from .polyseed.polyseed import PolyseedWordlist

def monero_en() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.en import MoneroEnglishWordlist
    return MoneroEnglishWordlist

def monero_zh_hans() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.zh_hans import MoneroChineseSimplifiedWordlist
    return MoneroChineseSimplifiedWordlist

def monero_nl() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.nl import MoneroDutchWordlist
    return MoneroDutchWordlist

def monero_eo() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.eo import MoneroEsperantoWordlist
    return MoneroEsperantoWordlist

def monero_fr() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.fr import MoneroFrenchWordlist
    return MoneroFrenchWordlist

def monero_de() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.de import MoneroGermanWordlist
    return MoneroGermanWordlist

def monero_it() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.it import MoneroItalianWordlist
    return MoneroItalianWordlist

def monero_jp() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.jp import MoneroJapaneseWordlist
    return MoneroJapaneseWordlist

def monero_lojban() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.lojban import MoneroLojbanWordlist
    return MoneroLojbanWordlist

def monero_pt() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.pt import MoneroPortugueseWordlist
    return MoneroPortugueseWordlist

def monero_ru() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.ru import MoneroRussianWordlist
    return MoneroRussianWordlist

def monero_es() -> MoneroWordlist:
    from xmrsigner.models.wordlists.monero.es import MoneroSpanishWordlist
    return MoneroSpanishWordlist

def polyseed_en() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.en import PolyseedEnglishWordlist
    return PolyseedEnglishWordlist

def polyseed_jp() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.jp import PolyseedJapaneseWordlist
    return PolyseedJapaneseWordlist

def polyseed_ko() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.ko import PolyseedKoreanWordlist
    return PolyseedKoreanWordlist

def polyseed_es() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.es import PolyseedSpanishWordlist
    return PolyseedSpanishWordlist

def polyseed_zh_hans() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.zh_hans import PolyseedChineseSimplifiedWordlist
    return PolyseedChineseSimplifiedWordlist

def polyseed_zh_hant() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.zh_hant import PolyseedChineseTraditionalWordlist
    return PolyseedChineseTraditionalWordlist

def polyseed_fr() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.fr import PolyseedFrenchWordlist
    return PolyseedFrenchWordlist

def polyseed_it() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.it import PolyseedItalianWordlist
    return PolyseedItalianWordlist

def polyseed_cs() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.cs import PolyseedCzechWordlist
    return PolyseedCzechWordlist

def polyseed_pt() -> PolyseedWordlist:
    from xmrsigner.models.wordlists.polyseed.pt import PolyseedPortugueseWordlist
    return PolyseedPortugueseWordlist

def monero(code: str) -> MoneroWordlist:
    if code == 'ru':
        return monero_ru()
    if code == 'fr':
        return monero_fr()
    if code == 'en':
        return monero_en()
    if code == 'pt':
        return monero_pt()
    if code == 'eo':
        return monero_eo()
    if code == 'it':
        return monero_it()
    if code == 'jp':
        return monero_jp()
    if code == 'es':
        return monero_es()
    if code == 'lojban':
        return monero_lojban()
    if code == 'nl':
        return monero_nl()
    if code == 'zh-Hans':
        return monero_zh_hans()
    if code == 'de':
        return monero_de()
    raise Exception(f'Monero has no wordlist for language code {code}!')

def polyseed(code: str) -> PolyseedWordlist:
    if code == 'fr':
        return polyseed_fr()
    if code == 'en':
        return polyseed_en()
    if code == 'pt':
        return polyseed_pt()
    if code == 'ko':
        return polyseed_ko()
    if code == 'it':
        return polyseed_it()
    if code == 'jp':
        return polyseed_jp()
    if code == 'es':
        return polyseed_es()
    if code == 'cs':
        return polyseed_cs()
    if code == 'zh-Hant':
        return polyseed_zh_hant()
    if code == 'zh-Hans':
        return polyseed_zh_hans()
    raise Exception(f'Polyseed has no wordlist for language code {code}!')

def wordlist(seed_type: SeedType, code: str) -> Wordlist:
    if seed_type == SeedType.MONERO:
        return monero(code)
    if seed_type == SeedType.POLYSEED:
        return polyseed(code)
    raise Exception(f'Undefined SeedType: {seed_type}!')

def words(seed_type: SeedType, language: SeedLanguage|str) -> list[str]:
    return wordlist(seed_type, language.code if isinstance(language, SeedLanguage) else language).words
