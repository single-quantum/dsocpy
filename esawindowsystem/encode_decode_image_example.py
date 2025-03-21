from fractions import Fraction
import pathlib

import matplotlib.pyplot as plt
from PIL import Image

from esawindowsystem.core.data_converter import payload_to_bit_sequence
from esawindowsystem.core.encoder_functions import map_PPM_symbols, get_asm_bit_arr
from esawindowsystem.core.scppm_decoder import decode
from esawindowsystem.core.scppm_encoder import encoder

# Definitions:
# - M: PPM order, should be increment of 2**m with m in [2, 3, 4, ...]
# - CODE_RATE: code rate of the encoder, should be one of [1/3, 2/3, 1/2]
# - B_interleaver: base length of the shift register of the channel interleaver
# - N_interleaver: number of parallel shift registers in the channel interleaver
#   Note: the product B*N should be a multiple of 15120/m with m np.log2(M)
# - reference_file_path: file path to the pickle file of the encoded bit sequence.
#   This file is used to determine the bit error ratio (BER) before decoding.

M: int = 8
code_rate: Fraction = Fraction(2, 3)
payload_type = 'image'

parent_dir = pathlib.Path(__file__).parent.resolve()
payload_file_path = pathlib.Path(parent_dir) / 'sample_payloads/JWST_Jupiter_tiny.png'

IMG_SIZE: tuple[int, ...] = tuple((0, 0))

if payload_type == 'image':
    img = Image.open(payload_file_path)
    IMG_SIZE = img.size

# Additional settings that are not strictly necessary.
# If B and N are not provided, N is assumed to be 2
user_settings = {
    'B_interleaver': 2520,
    'N_interleaver': 2,
    'reference_file_path': parent_dir / 'tmp' / 'pillars_greyscale_16_samples_per_slot_8-PPM_interleaved_sent_bit_sequence'
}

# 1. Convert payload to bit sequence
# 2. Encode
# 3. Decode

# Convert payload (in this case an image) to bit array
sent_bits = payload_to_bit_sequence(payload_type, filepath=payload_file_path)

# Put the payload through the encoder
# Some extra settings can be passed through the encoder and decoder, like the length of the channel interleaver
# or whether or not to save the encoded bit sequence to a file for reference.
slot_mapped_sequence, _, _ = encoder(
    sent_bits,
    M,
    code_rate,
    **{
        'user_settings': user_settings,
        'save_encoded_sequence_to_file': True,
        'reference_file_prefix': 'pillars_greyscale',
        'num_samples_per_slot': 16,
        'use_inner_encoder': True,
        'use_randomizer': True
    })

decoded_message, _, where_asms = decode(
    slot_mapped_sequence,
    M,
    code_rate,
    **{
        'user_settings': user_settings,
        'use_inner_encoder': True,
        'use_randomizer': True
    }
)

information_block_sizes = {
    Fraction(1, 3): 5040,
    Fraction(1, 2): 7560,
    Fraction(2, 3): 10080
}

num_bits = information_block_sizes[code_rate]
ASM_arr = get_asm_bit_arr()
decoded_message = decoded_message[where_asms[0] +
                                  ASM_arr.shape[0]:(where_asms[0] + ASM_arr.shape[0] + num_bits * 8)]

if payload_type == 'image':
    # Although `map_PPM_symbols` was meant to map bits to PPM symbols, it can conveniently also be used
    # to map bit values to 1-byte greyscale values.

    pixel_values = map_PPM_symbols(decoded_message, 8)
    img_arr = pixel_values[:IMG_SIZE[0] * IMG_SIZE[1]].reshape((IMG_SIZE[1], IMG_SIZE[0]))

    plt.figure()
    plt.imshow(img_arr)
    plt.show()

else:
    print('Decoded message', decoded_message)
