import numpy as np
import numpy.typing as npt

from ppm_parameters import M


def find_pulses_within_symbol_frame(
    i: int,
    symbol_length: float,
    bin_times: npt.NDArray[np.float_],
    start_time: float
) -> tuple[npt.NDArray[np.float_], float, float]:
    """Find all time events (pulses) within the given symbol frame, defined by i and the symbol length.

    Returns a list of time events within the frame, as well as the symbol start and end time.
    """
    symbol_start: float = start_time + i * symbol_length
    symbol_end: float = start_time + (i + 1) * symbol_length

    symbol_frame_pulses: npt.NDArray[np.float_] = bin_times[np.logical_and(
        bin_times >= symbol_start, bin_times <= symbol_end)]

    return symbol_frame_pulses, symbol_start, symbol_end


def check_timing_requirement(pulse: float, symbol_start: float, bin_length: float) -> bool:
    timing_requirement: bool = True

    A: int = int((pulse - symbol_start) / bin_length)
    slot_start: float = A * bin_length
    slot_end: float = (A + 1) * bin_length
    center: float = slot_start + (slot_end - slot_start) / 2
    sigma: float = 0.1 * bin_length

    # Pulse time does not comply with the timing requirement
    if abs(center - (pulse - symbol_start)) > 3 * sigma:
        timing_requirement = False

    return timing_requirement


def parse_ppm_symbols(
        pulse_times: npt.NDArray[np.float_],
        codeword_start_time: float,
        stop_time: float,
        slot_length: float,
        symbol_length: float,
        num_darkcounts: int = 0,
        **kwargs) -> tuple[list[float], int]:

    symbols: list[float] = []
    num_symbol_frames = int(round((stop_time - codeword_start_time) / symbol_length))

    for i in range(num_symbol_frames):
        symbol_frame_pulses, symbol_start, _ = find_pulses_within_symbol_frame(
            i, symbol_length, pulse_times, codeword_start_time)

        # No symbol detected in this symbol frame
        if symbol_frame_pulses.size == 0:
            symbols.append(0)
            continue

        j = 0
        if len(symbol_frame_pulses) > 1:
            num_darkcounts += 1

        for pulse in symbol_frame_pulses:
            symbol = (pulse - symbol_start - 0.5 * slot_length) / slot_length

            # Symbols cannot be in guard slots
            if round(symbol) > M:
                continue

            # If the symbol is too far off the bin center, it is most likely a darkcount
            # timing_requirement = check_timing_requirement(pulse, symbol_start, slot_length)
            # if not timing_requirement:
            #     continue

            symbols.append(symbol)
            j += 1
            break

        # If there were pulses detected in the symbol frame, but none of them were valid symbols, use a 0 instead.
        # This makes sure that there will always be a symbol in each symbol frame.
        if j == 0:
            symbols.append(0)

    return symbols, num_darkcounts


def rolling_window(a, size):
    shape = a.shape[:-1] + (a.shape[-1] - size + 1, size)
    strides = a.strides + (a. strides[-1],)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)
