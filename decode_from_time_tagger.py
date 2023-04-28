import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import TimeTagger

from PIL import Image

from demodulation_functions import demodulate
from encoder_functions import map_PPM_symbols
from ppm_parameters import (BIT_INTERLEAVE, CHANNEL_INTERLEAVE, CODE_RATE,
                            GREYSCALE, IMG_SHAPE, B_interleaver, N_interleaver,
                            m, num_slots_per_symbol, slot_length, symbol_length)

from BCJR_decoder_functions import ppm_symbols_to_bit_array
from scppm_decoder import DecoderError, decode
from utils import flatten

"""Read time tagger files from the Swabian Time Tagger Ultra. Required software for the time tagger can be found here:
https://www.swabianinstruments.com/time-tagger/downloads/ . """


def get_time_events_from_tt_file(time_events_filename: str, **kwargs):
    """Open the `time_events_filename` with the TimeTagger.FileReader class and retrieve events. 

    Can either read out the entire buffer or read out a given number of events. """
    fr = TimeTagger.FileReader(time_events_filename)

    if num_events := kwargs.get('num_events'):
        data = fr.getData(num_events)
        time_stamps = data.getTimestamps()
        time_events = time_stamps * 1E-12

        return time_events

    buffer_empty: bool = False

    # It is a bit awkward to work with a list here, then flatten it and
    # recast it to a numpy array, but it is much faster than working with np.hstack / np.append
    time_stamps = []

    while not buffer_empty:
        data = fr.getData(1000)
        events = data.getTimestamps()
        if events.size == 0:
            buffer_empty = True
        else:
            time_stamps.append(events)

    time_stamps = flatten(time_stamps)
    time_stamps = np.array(time_stamps)

    time_events = time_stamps * 1E-12

    return time_events


M = 8
use_latest_tt_file: bool = False
time_tagger_files_dir: str = 'time tagger files/'
reference_file_path = 'jupiter_greyscale_8_samples_per_slot_8-PPM_interleaved_sent_bit_sequence'

if use_latest_tt_file:
    time_tagger_files_path: Path = Path(__file__).parent.absolute() / time_tagger_files_dir
    tt_files = time_tagger_files_path.rglob('*.ttbin')
    files: list[Path] = [x for x in tt_files if x.is_file()]
    files = sorted(files, key=lambda x: x.lstat().st_mtime)
    time_tagger_filename = time_tagger_files_dir + re.split(r'\.\d{1}', files[-1].stem)[0] + '.ttbin'
else:
    time_tagger_filename = time_tagger_files_dir + 'jupiter_tiny_greyscale_64_samples_per_slot_CSM_0_interleaved_16-29-15.ttbin'


time_events = get_time_events_from_tt_file(time_tagger_filename)

print(f'Number of events: {len(time_events)}')

slot_mapped_message = demodulate(time_events[800000:1200000], M, slot_length, symbol_length, num_slots_per_symbol)

information_blocks, BER_before_decoding = decode(
    slot_mapped_message, M, CODE_RATE,
    **{'use_cached_trellis': False, })


if GREYSCALE:
    pixel_values = map_PPM_symbols(information_blocks, 8)
    img_arr = pixel_values[:IMG_SHAPE[0] * IMG_SHAPE[1]].reshape(IMG_SHAPE)
    CMAP = 'Greys'
    MODE = "L"
    IMG_MODE = 'L'
else:
    img_arr = information_blocks.flatten()[:IMG_SHAPE[0] * IMG_SHAPE[1]].reshape(IMG_SHAPE)
    CMAP = 'binary'
    MODE = "1"
    IMG_MODE = '1'


# compare to original image
file = "sample_payloads/JWST_2022-07-27_Jupiter_tiny.png"
img = Image.open(file)
img = img.convert(IMG_MODE)
sent_img_array = np.asarray(img).astype(int)

img_shape = sent_img_array.shape
# In the case of greyscale, each pixel has a value from 0 to 255.
# This would be the same as saying that each pixel is a symbol, which should be mapped to an 8 bit sequence.
if GREYSCALE:
    sent_message = ppm_symbols_to_bit_array(sent_img_array.flatten(), 8)
else:
    sent_message = sent_img_array.flatten()

if len(information_blocks) < len(sent_message):
    BER_after_decoding = np.sum(np.abs(information_blocks -
                                sent_message[:len(information_blocks)])) / len(information_blocks)
else:
    BER_after_decoding = np.sum(
        np.abs(information_blocks[:len(sent_message)] - sent_message)) / len(sent_message)

print(f'BER after decoding: {BER_after_decoding }. ')

plt.figure()
plt.imshow(img_arr, cmap=CMAP)
plt.title('Decoded image of Jupiter')
plt.xlabel('Pixel number (x)')
plt.ylabel('Pixel number (y)')
plt.show()

print('Done')
