# Inline Todo

Total: 31

## Index
- [Urgent](#urgent)
- [By File](#by-file)
- [External Todo](Todo.md)

## Urgent

### 2024-06-04
- `src/xmrsigner/views/tools_views.py:406`
  2024-06-04, rename, because it is missleading, the only thing what will be calculated is the checksum word

### 2024-06-30
- `src/xmrsigner/models/settings.py:25`
  2024-06-30 don't know what will uname return on win32, check

### 2024-07-23
- `src/xmrsigner/views/scan_views.py:224`
  2024-07-23, implement in SeedOptions
- `src/xmrsigner/views/scan_views.py:234`
  2024-07-23, implement in SeedOptions

### 2024-07-27
- `src/xmrsigner/views/monero_views.py:258`
  2024-07-27, decide what to do about
- `src/xmrsigner/views/monero_views.py:288`
  2024-07-27, decide to check or remove
- `src/xmrsigner/views/monero_views.py:413`
  2024-07-27, code missing here!
- `src/xmrsigner/views/seed_views.py:538`
  2024-07-27, thought: ask user if he wants to see the address explorer to tranfer funds to the wallet

### 2024-07-28
- `src/xmrsigner/gui/components.py:600`
  2024-07-28, render only with Monero Logo
- `src/xmrsigner/gui/components.py:677`
  2024-07-28, render only with Monero Logo

### 2024-08-02
- `src/xmrsigner/gui/components.py:590`
  2024-08-02, change to Monero icon

### No time constraint
- `src/test/xmrsigner/helpers/polyseed_mnemonic_generation.py:13`
  not working yet, some issue in polyseed-python
- `src/xmrsigner/gui/constants.py:152`
  don't need BTC, need XMR glyph is still Bitcoin
- `src/xmrsigner/gui/constants.py:153`
  don't need BTC, need XMR glyph is still Bitcoin
- `src/xmrsigner/hardware/buttons.py:148`
  **#SEEDSIGNER** Implement `release_lock` functionality as a global somewhere. Mixes up design
- `src/xmrsigner/helpers/qr.py:62`
  why??? Remove, is there is not a very good reason for it...
- `src/xmrsigner/helpers/qr.py:64`
  WTF, implement in python? Check what was the reason or if i makes any sense.
- `src/xmrsigner/helpers/seedwordindex.py:1`
  remove after migration to OTS
- `src/xmrsigner/helpers/ur2/cbor_lite.py:246`
  Check that this is the right way -- do we need to use struct.unpack()?
- `src/xmrsigner/helpers/ur2/fountain_decoder.py:37`
  Not efficient
- `src/xmrsigner/helpers/ur2/fountain_decoder.py:55`
  Handle None?
- `src/xmrsigner/helpers/ur2/fountain_decoder.py:200`
  Does this need to make a copy of p?
- `src/xmrsigner/helpers/ur2/fountain_encoder.py:35`
  Do something better with this check
- `src/xmrsigner/models/base_decoder.py:29`
  **#SEEDSIGNER** standardize this approach across all decoders (example: SignMessageQrDecoder)
- `src/xmrsigner/models/ur_encoder.py:23`
  why not qr.qrimage instead???
- `src/xmrsigner/views/monero_views.py:167`
  make conditional: only if dire warning is enabled
- `src/xmrsigner/views/screensaver.py:15`
  This early code is now outdated vis-a-vis Screen vs View distinctions
- `src/xmrsigner/views/seed_views.py:240`
  really? Think that is to remove...
- `src/xmrsigner/views/seed_views.py:364`
  Warning screen: "password required!?
- `src/xmrsigner/views/seed_views.py:468`
  check
- `src/xmrsigner/views/tools_views.py:551`
  Refactor to a cleaner `BackStack.get_previous_View_cls()`

## By File

### `src/test/xmrsigner/helpers/polyseed_mnemonic_generation.py`
- Line 13: None 
  not working yet, some issue in polyseed-python

### `src/xmrsigner/gui/components.py`
- Line 590: 2024-08-02 
  2024-08-02, change to Monero icon
- Line 600: 2024-07-28 
  2024-07-28, render only with Monero Logo
- Line 677: 2024-07-28 
  2024-07-28, render only with Monero Logo

### `src/xmrsigner/gui/constants.py`
- Line 152: None 
  don't need BTC, need XMR glyph is still Bitcoin
- Line 153: None 
  don't need BTC, need XMR glyph is still Bitcoin

### `src/xmrsigner/hardware/buttons.py`
- Line 148: None **#SEEDSIGNER** 
  Implement `release_lock` functionality as a global somewhere. Mixes up design

### `src/xmrsigner/helpers/qr.py`
- Line 62: None 
  why??? Remove, is there is not a very good reason for it...
- Line 64: None 
  WTF, implement in python? Check what was the reason or if i makes any sense.

### `src/xmrsigner/helpers/seedwordindex.py`
- Line 1: None 
  remove after migration to OTS

### `src/xmrsigner/helpers/ur2/cbor_lite.py`
- Line 246: None 
  Check that this is the right way -- do we need to use struct.unpack()?

### `src/xmrsigner/helpers/ur2/fountain_decoder.py`
- Line 37: None 
  Not efficient
- Line 55: None 
  Handle None?
- Line 200: None 
  Does this need to make a copy of p?

### `src/xmrsigner/helpers/ur2/fountain_encoder.py`
- Line 35: None 
  Do something better with this check

### `src/xmrsigner/models/base_decoder.py`
- Line 29: None **#SEEDSIGNER** 
  standardize this approach across all decoders (example: SignMessageQrDecoder)

### `src/xmrsigner/models/settings.py`
- Line 25: 2024-06-30 
  2024-06-30 don't know what will uname return on win32, check

### `src/xmrsigner/models/ur_encoder.py`
- Line 23: None 
  why not qr.qrimage instead???

### `src/xmrsigner/views/monero_views.py`
- Line 167: None 
  make conditional: only if dire warning is enabled
- Line 258: 2024-07-27 
  2024-07-27, decide what to do about
- Line 288: 2024-07-27 
  2024-07-27, decide to check or remove
- Line 413: 2024-07-27 
  2024-07-27, code missing here!

### `src/xmrsigner/views/scan_views.py`
- Line 224: 2024-07-23 
  2024-07-23, implement in SeedOptions
- Line 234: 2024-07-23 
  2024-07-23, implement in SeedOptions

### `src/xmrsigner/views/screensaver.py`
- Line 15: None 
  This early code is now outdated vis-a-vis Screen vs View distinctions

### `src/xmrsigner/views/seed_views.py`
- Line 240: None 
  really? Think that is to remove...
- Line 364: None 
  Warning screen: "password required!?
- Line 468: None 
  check
- Line 538: 2024-07-27 
  2024-07-27, thought: ask user if he wants to see the address explorer to tranfer funds to the wallet

### `src/xmrsigner/views/tools_views.py`
- Line 406: 2024-06-04 
  2024-06-04, rename, because it is missleading, the only thing what will be calculated is the checksum word
- Line 551: None 
  Refactor to a cleaner `BackStack.get_previous_View_cls()`
