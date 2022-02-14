from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
from enum import IntEnum
import re
import json
import base64
import json
import logging
import re

from binascii import a2b_base64, b2a_base64
from embit import psbt
from enum import IntEnum
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol

from . import QRType, Seed
from .seed import SeedConstants
from .settings import SettingsConstants

from seedsigner.helpers.ur2.ur_decoder import URDecoder
from seedsigner.helpers.bcur import (cbor_decode, bc32decode)

logger = logging.getLogger(__name__)



from urtypes.crypto import PSBT as UR_PSBT

###
### DecodeQR Class
### Purpose: used to process images or string data from animated qr codes with psbt data to create binary/base64 psbt
###
class DecodeQR:

    def __init__(self, **kwargs):
        self.complete = False
        self.qr_type = None
        self.ur_decoder = URDecoder() # UR2 decoder
        self.specter_qr = SpecterDecodePSBTQR() # Specter Desktop PSBT QR base64 decoder
        self.legacy_ur = LegacyURDecodeQR() # UR Legacy decoder
        self.base64_qr = Base64DecodeQR() # Single Segments Base64
        self.base43_qr = Base43DecodeQR() # Single Segment Base43
        self.address_qr = BitcoinAddressQR() # Single Segment bitcoin address
        self.specter_wallet_qr = SpecterDecodeWalletQR() # Specter Desktop Wallet Export decoder
        self.settings_qr = SettingsQR()             # Settings config in .ini format
        self.wordlist = None

        for key, value in kwargs.items():
            if key == "qr_type":
                self.qr_type = value
            if key == "wordlist":
                self.wordlist = value
                
        if self.wordlist == None:
            raise Exception('Wordlist Required')
            
        self.seedqr = SeedQR(wordlist=self.wordlist)

    def addImage(self, image):
        qr_str = DecodeQR.QR2Str(image)
        if qr_str == None:
            return DecodeQRStatus.FALSE

        return self.addString(qr_str)

    def addString(self, qr_str):
        if qr_str == None:
            return DecodeQRStatus.FALSE

        qr_type = DecodeQR.SegmentType(qr_str, wordlist=self.wordlist)

        if self.qr_type == None:
            self.qr_type = qr_type
        elif self.qr_type != qr_type:
            raise Exception('QR Fragement Unexpected Type Change')

        if self.qr_type == QRType.PSBTUR2:

            self.ur_decoder.receive_part(qr_str)
            if self.ur_decoder.is_complete():
                self.complete = True
                return DecodeQRStatus.COMPLETE
            return DecodeQRStatus.PART_COMPLETE # segment added to ur2 decoder

        elif self.qr_type == QRType.PSBTSPECTER:

            rt = self.specter_qr.add(qr_str)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == QRType.PSBTURLEGACY:

            rt = self.legacy_ur.add(qr_str)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == QRType.PSBTBASE64:

            rt = self.base64_qr.add(qr_str)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt
            
        elif self.qr_type == QRType.PSBTBASE43:
            
            rt = self.base43_qr.add(qr_str)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == QRType.SEEDSSQR:
            rt = self.seedqr.add(qr_str, QRType.SEEDSSQR)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == QRType.SETTINGS:
            rt = self.settings_qr.add(qr_str, self.qr_type)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == QRType.SEEDMNEMONIC:
            rt = self.seedqr.add(qr_str, QRType.SEEDMNEMONIC)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == QRType.SEED4LETTERMNEMONIC:
            rt = self.seedqr.add(qr_str, QRType.SEED4LETTERMNEMONIC)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt
            
        elif self.qr_type == QRType.BITCOINADDRESSQR:
            rt = self.address_qr.add(qr_str, QRType.BITCOINADDRESSQR)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt
            
        elif self.qr_type == QRType.SPECTERWALLETQR:
            rt = self.specter_wallet_qr.add(qr_str)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        else:
            return DecodeQRStatus.INVALID

    def getPSBT(self):
        if self.complete:
            data = self.getDataPSBT()
            if data != None:
                try:
                    return psbt.PSBT.parse(data)
                except:
                    return None
        return None

    def getDataPSBT(self):
        if self.complete:
            if self.qr_type == QRType.PSBTUR2:
                cbor = self.ur_decoder.result_message().cbor
                return UR_PSBT.from_cbor(cbor).data
                # return cbor_decode(cbor)
            elif self.qr_type == QRType.PSBTSPECTER:
                return self.specter_qr.getData()
            elif self.qr_type == QRType.PSBTURLEGACY:
                return self.legacy_ur.getData()
            elif self.qr_type == QRType.PSBTBASE64:
                return self.base64_qr.getData()
            elif self.qr_type == QRType.PSBTBASE43:
                return self.base43_qr.getData()
        return None

    def getBase64PSBT(self):
        if self.complete:
            data = self.getDataPSBT()
            b64_psbt = b2a_base64(data)

            if b64_psbt[-1:] == b"\n":
                b64_psbt = b64_psbt[:-1]

            return b64_psbt.decode("utf-8")
        return None

    def getSeedPhrase(self):
        return self.seedqr.getSeedPhrase()
    
    def get_settings_data(self):
        return self.settings_qr.settings
    
    def get_settings_config_name(self):
        return self.settings_qr.config_name
        
    def getAddress(self):
        return self.address_qr.getAddress()
        
    def getAddressType(self):
        return self.address_qr.getAddressType()
        
    def getWalletDescriptor(self):
        return self.specter_wallet_qr.getWalletDescriptor()

    def getPercentComplete(self) -> int:
        if self.qr_type == QRType.PSBTUR2:
            return int(self.ur_decoder.estimated_percent_complete() * 100)
        elif self.qr_type == QRType.PSBTSPECTER:
            if self.specter_qr.total_segments == None:
                return 0
            return int((self.specter_qr.collected_segments / self.specter_qr.total_segments) * 100)
        elif self.qr_type == QRType.PSBTURLEGACY:
            if self.legacy_ur.total_segments == None:
                return 0
            return int((self.legacy_ur.collected_segments / self.legacy_ur.total_segments) * 100)
        elif self.qr_type == QRType.PSBTBASE64:
            if self.base64_qr.complete:
                return 100
            else:
                return 0
        elif self.qr_type == QRType.PSBTBASE43:
            if self.base43_qr.complete:
                return 100
            else:
                return 0
        else:
            return 0

    # TODO: Convert these to properties, python-ize naming convention
    def isComplete(self) -> bool:
        return self.complete

    def isInvalid(self) -> bool:
        if self.qr_type == QRType.INVALID:
            return True
        return False

    def isPSBT(self) -> bool:
        if self.qr_type in (QRType.PSBTUR2, QRType.PSBTSPECTER, QRType.PSBTURLEGACY, QRType.PSBTBASE64, QRType.PSBTBASE43):
            return True
        return False

    def isSeed(self):
        if self.qr_type in (QRType.SEEDSSQR, QRType.SEEDUR2, QRType.SEEDMNEMONIC, QRType.SEED4LETTERMNEMONIC):
            return True
        return False
    
    @property
    def is_json(self):
        return self.qr_type in [QRType.SETTINGS, QRType.JSON]
        
    def isAddress(self):
        if self.qr_type == QRType.BITCOINADDRESSQR:
            return True
        return False
        
    def isWalletDescriptor(self):
        if self.qr_type in (QRType.SPECTERWALLETQR, QRType.URWALLETQR, QRType.BLUEWALLETQR):
            return True
        return False

    def qrType(self):
        return self.qr_type

    @staticmethod
    def QR2Str(image) -> str:
        if image is None:
            return None

        barcodes = pyzbar.decode(image, symbols=[ZBarSymbol.QRCODE])

        for barcode in barcodes:
            # Only pull and return the first barcode
            return barcode.data.decode("utf-8")

    @staticmethod
    def SegmentType(s, wordlist=None):

        # PSBT
        if re.search("^UR:CRYPTO-PSBT/", s, re.IGNORECASE):
            return QRType.PSBTUR2
        elif re.search(r'^p(\d+)of(\d+) ([A-Za-z0-9+\/=]+$)', s, re.IGNORECASE): #must be base64 characters only in segment
            return QRType.PSBTSPECTER
        elif re.search("^UR:BYTES/", s, re.IGNORECASE):
            return QRType.PSBTURLEGACY
        elif DecodeQR.isBase64PSBT(s):
            return QRType.PSBTBASE64
            
        # Wallet Descriptor
        desc_str = s.replace("\n","").replace(" ","")
        if re.search(r'^p(\d+)of(\d+) ', s, re.IGNORECASE):
            # when not a SPECTER Base64 PSBT from above, assume it's json
            return QRType.SPECTERWALLETQR
        elif re.search(r'^\{\"label\".*\"descriptor\"\:.*', desc_str, re.IGNORECASE):
            # if json starting with label and contains descriptor, assume specter wallet json
            return QRType.SPECTERWALLETQR

        # create 4 letter wordlist only if not PSBT (performance gain)
        try:
            _4LETTER_WORDLIST = [word[:4].strip() for word in wordlist]
        except:
            _4LETTER_WORDLIST = []
        
        # Seed
        if re.search(r'\d{48,96}', s):
            return QRType.SEEDSSQR
            
        # Bitcoin Address
        elif DecodeQR.isBitcoinAddress(s):
            return QRType.BITCOINADDRESSQR
        
        # Seed
        elif all(x in wordlist for x in s.strip().split(" ")):
            # checks if all words in list are in bip39 word list
            return QRType.SEEDMNEMONIC
        elif all(x in _4LETTER_WORDLIST for x in s.strip().split(" ")):
            # checks if all 4 letter words are in list are in 4 letter bip39 word list
            return QRType.SEED4LETTERMNEMONIC
        elif DecodeQR.isBase43PSBT(s):
            return QRType.PSBTBASE43
        
        # config data
        if "type=settings" in s:
            return QRType.SETTINGS

        return QRType.INVALID

    @staticmethod   
    def isBase64(s):
        try:
            return base64.b64encode(base64.b64decode(s)) == s.encode('ascii')
        except Exception:
            return False

    @staticmethod   
    def isBase64PSBT(s):
        try:
            if DecodeQR.isBase64(s):
                psbt.PSBT.parse(a2b_base64(s))
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def isBase43PSBT(s):
        try:
            psbt.PSBT.parse(DecodeQR.base43Decode(s))
            return True
        except Exception:
            return False
        return False
    
    @staticmethod
    def base43Decode(s):
        chars = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$*+-./:' #base43 chars

        if isinstance(s, bytes):
            v = s
        if isinstance(s, str):
            v = s.encode('ascii')
        elif isinstance(s, bytearray):
            v = bytes(s)
            
        long_value = 0
        power_of_base = 1
        for c in v[::-1]:
            digit = chars.find(bytes([c]))
            if digit == -1:
                raise Exception('Forbidden character {} for base {}'.format(c, 43))
            # naive but slow variant:   long_value += digit * (base**i)
            long_value += digit * power_of_base
            power_of_base *= 43
        result = bytearray()
        while long_value >= 256:
            div, mod = divmod(long_value, 256)
            result.append(mod)
            long_value = div
        result.append(long_value)
        nPad = 0
        for c in v:
            if c == chars[0]:
                nPad += 1
            else:
                break
        result.extend(b'\x00' * nPad)
        result.reverse()
        return bytes(result)
        
    @staticmethod
    def isBitcoinAddress(s):
    
        if re.search(r'^bitcoin\:.*', s, re.IGNORECASE):
            return True
        elif re.search(r'^((bc1|tb1|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,62})$', s):
            return True
        else:
            return False

###
### SpecterDecodePSBTQR Class
### Purpose: used in DecodePSBTQR to decode Specter Desktop Animated QR PSBT encoding
###

class SpecterDecodePSBTQR:

    def __init__(self):
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False
        self.segments = []

    def add(self, segment):
        if self.total_segments == None:
            self.total_segments = SpecterDecodePSBTQR.totalSegmentNum(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != SpecterDecodePSBTQR.totalSegmentNum(segment):
            raise Exception('Specter Desktop segment total changed unexpectedly')

        if self.segments[SpecterDecodePSBTQR.currentSegmentNum(segment) - 1] == None:
            self.segments[SpecterDecodePSBTQR.currentSegmentNum(segment) - 1] = SpecterDecodePSBTQR.parseSegment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                self.complete = True
                return DecodeQRStatus.COMPLETE
            return DecodeQRStatus.PART_COMPLETE # new segment added

        return DecodeQRStatus.PART_EXISTING # segment not added because it's already been added

    def getBase64Data(self) -> str:
        base64 = "".join(self.segments)
        if self.complete and DecodeQR.isBase64(base64):
            return base64

        return None

    def getData(self):
        base64 = self.getBase64Data()
        if base64 != None:
            return a2b_base64(base64)

        return None

    def is_complete(self) -> bool:
        return self.complete

    @staticmethod
    def currentSegmentNum(segment) -> int:
        if DecodeQR.SegmentType(segment) == QRType.PSBTSPECTER:
            if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
                return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(1))
        raise Exception('Unable to parse Specter Desktop segment')

    @staticmethod
    def totalSegmentNum(segment) -> int:
        if DecodeQR.SegmentType(segment) == QRType.PSBTSPECTER:
            if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
                return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(2))
        raise Exception('Unable to parse Specter Desktop segment')

    @staticmethod
    def parseSegment(segment) -> str:
        return segment.split(" ")[-1].strip()

###
### LegacyURDecodeQR Class
### Purpose: used in DecodeQR to decode Legacy UR animated qr encoding
###

class LegacyURDecodeQR:

    def __init__(self):
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False
        self.segments = []

    def add(self, segment):
        if self.total_segments == None:
            self.total_segments = LegacyURDecodeQR.totalSegmentNum(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != LegacyURDecodeQR.totalSegmentNum(segment):
            raise Exception('UR Legacy segment total changed unexpectedly')

        if self.segments[LegacyURDecodeQR.currentSegmentNum(segment) - 1] == None:
            self.segments[LegacyURDecodeQR.currentSegmentNum(segment) - 1] = LegacyURDecodeQR.parseSegment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                self.complete = True
                return DecodeQRStatus.COMPLETE
            return DecodeQRStatus.PART_COMPLETE # new segment added

        return DecodeQRStatus.PART_EXISTING # segment not added because it's already been added

    def getBase64Data(self) -> str:
        bc32_cbor = "".join(self.segments)
        raw = cbor_decode(bc32decode(bc32_cbor))
        base64 = b2a_base64(raw)

        if self.complete:
            return base64

        return None

    def getData(self):
        if not self.complete:
            return None

        bc32_cbor = "".join(self.segments)
        raw = cbor_decode(bc32decode(bc32_cbor))
        return raw

    def is_complete(self) -> bool:
        return self.complete

    @staticmethod
    def currentSegmentNum(segment) -> int:
        if DecodeQR.SegmentType(segment) == QRType.PSBTURLEGACY:
            if re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE) != None:
                return int(re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE).group(1))
            else:
                raise Exception('Unexpected Legacy UR Error')
        raise Exception('Unable to parse Legacy UR segment')

    @staticmethod
    def totalSegmentNum(segment) -> int:
        if DecodeQR.SegmentType(segment) == QRType.PSBTURLEGACY:
            if re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE) != None:
                return int(re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE).group(2))
            else:
                return 1
        raise Exception('Unable to parse Legacy UR segment')

    @staticmethod
    def parseSegment(segment) -> str:
        return segment.split("/")[-1].strip()

###
### Base64DecodeQR Class
### Purpose: used in DecodeQR to decode single frame base64 encoded qr image
###          does not support animated qr because no indicator or segments or their order
###

class Base64DecodeQR:

    def __init__(self):
        self.total_segments = 1
        self.collected_segments = 0
        self.complete = False
        self.data = None

    def add(self, segment):
        if DecodeQR.isBase64(segment):
            self.complete = True
            self.data = segment
            self.collected_segments = 1
            return DecodeQRStatus.COMPLETE

        return DecodeQRStatus.INVALID

    def getBase64Data(self) -> str:
        return self.data

    def getData(self):
        base64 = self.getBase64Data()
        if base64 != None:
            return a2b_base64(base64)

        return None


###
### Base43DecodeQR Class
### Purpose: used in DecodeQR to decode single frame base43 encoded qr image
###          does not support animated qr because no indicator or segments or their order
###

class Base43DecodeQR:

    def __init__(self):
        self.total_segments = 1
        self.collected_segments = 0
        self.complete = False
        self.data = None

    def add(self, segment):
        if DecodeQR.isBase43PSBT(segment):
            self.complete = True
            self.data = DecodeQR.base43Decode(segment)
            self.collected_segments = 1
            return DecodeQRStatus.COMPLETE

        return DecodeQRStatus.INVALID

    def getData(self):
        return self.data


###
### SeedQR Class
### Purpose: used in DecodeQR to decode single frame representing a seed
###          SeedSigner numeric representation of a seed as a qr is supported
###          Mnemonic seed phrase representation of a seed as a qr is supported
###          does not support animated qr because no indicator or segments or their order
###

class SeedQR:

    def __init__(self, wordlist=None):
        self.total_segments = 1
        self.collected_segments = 0
        self.complete = False
        self.seed_phrase = []
        self.wordlist = wordlist
        
        if self.wordlist == None:
            raise Exception('Wordlist Required')

    def add(self, segment, qr_type=QRType.SEEDSSQR):
        _4LETTER_WORDLIST = [word[:4].strip() for word in self.wordlist]

        if qr_type == QRType.SEEDSSQR:

            try:
                self.seed_phrase = []

                # Parse 12 or 24-word QR code
                num_words = int(len(segment) / 4)
                for i in range(0, num_words):
                    index = int(segment[i * 4: (i*4) + 4])
                    word = self.wordlist[index]
                    self.seed_phrase.append(word)
                if len(self.seed_phrase) > 0:
                    if self.is1224Phrase() == False:
                        return DecodeQRStatus.INVALID
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
                else:
                    return DecodeQRStatus.INVALID
            except Exception as e:
                return DecodeQRStatus.INVALID

        elif qr_type == QRType.SEEDMNEMONIC:

            try:
                # embit mnemonic code to validate
                seed = Seed(segment, passphrase="", wordlist=self.wordlist)
                if not seed:
                    # seed is not valid, return invalid
                    return DecodeQRStatus.INVALID
                self.seed_phrase = segment.strip().split(" ")
                if self.is1224Phrase() == False:
                        return DecodeQRStatus.INVALID
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                return DecodeQRStatus.INVALID

        elif qr_type == QRType.SEED4LETTERMNEMONIC:

            try:
                sl = segment.strip().split(" ")
                words = []
                for s in sl:
                    words.append(self.wordlist[_4LETTER_WORDLIST.index(s)])

                # embit mnemonic code to validate
                seed = Seed(words, passphrase="", wordlist=self.wordlist)
                if not seed:
                    # seed is not valid, return invalid
                    return DecodeQRStatus.INVALID
                self.seed_phrase = words
                if self.is1224Phrase() == False:
                        return DecodeQRStatus.INVALID
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                return DecodeQRStatus.INVALID

        else:

            return DecodeQRStatus.INVALID

    def getSeedPhrase(self):
        if self.complete:
            return self.seed_phrase[:]
        return []

    def is1224Phrase(self):
        if len(self.seed_phrase) in (12, 24):
            return True
        return False


class SettingsQR:
    def __init__(self, wordlist=None):
        self.total_segments = 1
        self.collected_segments = 0
        self.complete = False
        self.settings = {}
        self.config_name = None

    def add(self, segment, qr_type=QRType.SETTINGS):
        print(f"SettingsQR: {segment}")
        try:
            self.settings = {}

            # QR Settings format is space-separated key/value pairs
            for entry in segment.split(" "):
                key = entry.split("=")[0].strip()
                value = entry.split("=")[1].strip()
                self.settings[key] = value

            # Remove values only needed for import
            self.settings.pop("type", None)
            version = self.settings.pop("version", None)
            if not version or int(version) != 1:
                raise Exception(f"Settings QR version {version} not supported")

            self.config_name = self.settings.pop("name", None)
            if self.config_name:
                self.config_name = self.config_name.replace("_", " ")
            
            # Have to translate the abbreviated settings into the human-readable values
            # used in the normal Settings.
            map_abbreviated_enable = {
                "0": SettingsConstants.OPTION__DISABLED,
                "1": SettingsConstants.OPTION__ENABLED,
                "2": SettingsConstants.OPTION__PROMPT,
            }
            map_abbreviated_sig_types = {
                "s": SeedConstants.SINGLE_SIG,
                "m": SeedConstants.MULTISIG,
            }
            map_abbreviated_scripts = {
                "na": SeedConstants.NATIVE_SEGWIT,
                "ne": SeedConstants.NESTED_SEGWIT,
                "tr": SeedConstants.TAPROOT,
                "cu": SeedConstants.CUSTOM_DERIVATION,
            }
            map_abbreviated_coordinators = {
                "bw": SettingsConstants.COORDINATOR__BLUE_WALLET,
                "sw": SettingsConstants.COORDINATOR__SPARROW,
                "sd": SettingsConstants.COORDINATOR__SPECTER_DESKTOP,
            }

            def convert_abbreviated_value(category, key, abbreviation_map, is_list=False, new_key_name=None):
                try:
                    if key not in self.settings:
                        logger.debug(f"'{key}' not found in settings")
                        return
                    value = self.settings[key]

                    if not is_list:
                        new_value = abbreviation_map.get(value)
                        if not new_value:
                            logger.error(f"No abbreviation map value for \"{value}\" for setting {key}")
                            return
                    else:
                        # `value` is a comma-separated list; yields list of map matches
                        values = value.split(",")
                        new_value = []
                        for v in values:
                            mapped_value = abbreviation_map.get(v)
                            if not mapped_value:
                                logger.error(f"No abbreviation map value for \"{v}\" for setting {key}")
                                return
                            new_value.append(mapped_value)
                    del self.settings[key]
                    if new_key_name:
                        key = new_key_name
                    if category not in self.settings:
                        self.settings[category] = {}
                    self.settings[category][key] = new_value
                except Exception as e:
                    logger.exception(e)
                    return

            convert_abbreviated_value("wallet", "coord", map_abbreviated_coordinators, is_list=True, new_key_name="coordinators")
            convert_abbreviated_value("features", "xpub", map_abbreviated_enable, new_key_name="xpub_export")
            convert_abbreviated_value("features", "sigs", map_abbreviated_sig_types, is_list=True, new_key_name="sig_types")
            convert_abbreviated_value("features", "scripts", map_abbreviated_scripts, is_list=True, new_key_name="script_types")
            convert_abbreviated_value("features", "xp_det", map_abbreviated_enable, new_key_name="show_xpub_details")
            convert_abbreviated_value("features", "passphrase", map_abbreviated_enable)
            convert_abbreviated_value("features", "priv_warn", map_abbreviated_enable, new_key_name="show_privacy_warnings")
            convert_abbreviated_value("features", "dire_warn", map_abbreviated_enable, new_key_name="show_dire_warnings")

            self.complete = True
            self.collected_segments = 1
            return DecodeQRStatus.COMPLETE
        except Exception as e:
            logger.exception(e)
            return DecodeQRStatus.INVALID

###
### BitcoinAddressQR Class
### Purpose: used in DecodeQR to decode single frame representing a bitcoin address
###

class BitcoinAddressQR:

    def __init__(self, wordlist=None):
        self.total_segments = 1
        self.collected_segments = 0
        self.complete = False
        self.address = None
        self.address_type = None

    def add(self, segment, qr_type=QRType.BITCOINADDRESSQR):
        
        r = re.search(r'((bc1|tb1|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,62})', segment)
        if r != None:
            self.address = r.group(1)
        
            if re.search(r'^((bc1|tb1|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,62})$', self.address) != None:
                self.complete = True
                self.collected_segments = 1
                
                # get address type
                r = re.search(r'^((bc1|tb1|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,62})$', self.address)
                if r != None:
                    r = r.group(2)
                
                if r == "1":
                    self.address_type = "P2PKH-main" # Legacy
                elif r == "m" or r == "n":
                    self.address_type = "P2PKH-test" # Legacy
                elif r == "3":
                    self.address_type = "P2SH-main" # Nested Segwit Single Sig (P2WPKH in P2SH) or Multisig (P2WSH in P2SH)
                elif r == "2":
                    self.address_type = "P2SH-test" # Nested Segwit Single Sig (P2WPKH in P2SH) or Multisig (P2WSH in P2SH)
                elif r == "bc1":
                    self.address_type = "Bech32-main" 
                elif r == "tb1":
                    self.address_type = "Bech32-test"
                
                return DecodeQRStatus.COMPLETE

        return DecodeQRStatus.INVALID
        
    def getAddress(self):
        if self.address != None:
            return self.address
        return None
        
    def getAddressType(self):
        if self.address != None:
            if self.address_type != None:
                return self.address_type
            else:
                return "Unknown"
        return None

###
### SpecterDecodeWalletQR Class
### Purpose: used in DecodeQR to decode animated frames to get a wallet descriptor from Specter Desktop
###

class SpecterDecodeWalletQR:
    
    def __init__(self):
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False
        self.segments = []

    def add(self, segment):
        if self.total_segments == None:
            self.total_segments = SpecterDecodeWalletQR.totalSegmentNum(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != SpecterDecodeWalletQR.totalSegmentNum(segment):
            raise Exception('Specter Desktop segment total changed unexpectedly')

        if self.segments[SpecterDecodeWalletQR.currentSegmentNum(segment) - 1] == None:
            self.segments[SpecterDecodeWalletQR.currentSegmentNum(segment) - 1] = SpecterDecodeWalletQR.parseSegment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                if self.validateWalletDescriptor():
                    self.complete = True
                    return DecodeQRStatus.COMPLETE
                else:
                    return DecodeQRStatus.INVALID
            return DecodeQRStatus.PART_COMPLETE # new segment added

        return DecodeQRStatus.PART_EXISTING # segment not added because it's already been added
        
    def validateJson(self) -> str:
        try:
            j = "".join(self.segments)
            json.loads(j)
        except json.decoder.JSONDecodeError:
            return False
        return True
        
    def validateWalletDescriptor(self):
        if self.validateJson():
            j = "".join(self.segments)
            data = json.loads(j)
            if "descriptor" in data:
                return True
            return False
        
    def getWalletDescriptor(self) -> str:
        if self.validateWalletDescriptor():
            j = "".join(self.segments)
            data = json.loads(j)
            return data['descriptor']
        return None

    def is_complete(self) -> bool:
        if self.complete and self.validateWalletDescriptor():
            return True
        return False

    @staticmethod
    def currentSegmentNum(segment) -> int:
        if DecodeQR.SegmentType(segment) == QRType.SPECTERWALLETQR:
            if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
                return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(1))
            else:
                return 1

    @staticmethod
    def totalSegmentNum(segment) -> int:
        if DecodeQR.SegmentType(segment) == QRType.SPECTERWALLETQR:
            if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
                return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(2))
            else:
                return 1

    @staticmethod
    def parseSegment(segment) -> str:
        try:
            return re.search(r'^p(\d+)of(\d+) (.+$)', segment, re.IGNORECASE).group(3)
        except:
            return segment

###
### DecodeQRStatus Class IntEum
### Purpose: used in DecodeQR to communicate status of adding qr frame/segment
###

class DecodeQRStatus(IntEnum):
    PART_COMPLETE = 1
    PART_EXISTING = 2
    COMPLETE = 3
    FALSE = 4
    INVALID = 5