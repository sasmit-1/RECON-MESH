"""
TRIDENT Numba Acceleration Layer (Step 03)
Provides JIT-compiled greedy 1:1 matching over integer paise amounts and Unix timestamps.
Falls back cleanly to vectorized NumPy / pure Python if Numba is unavailable or fails to compile.
"""

import numpy as np
from typing import List, Tuple

# Attempt Numba import — graceful fallback if unavailable or compile-time failure occurs.
try:
    from numba import njit as _numba_njit  # type: ignore

    @_numba_njit(fastmath=True, cache=True)
    def numba_greedy_1to1_match(
        rzp_amounts: np.ndarray,
        rzp_timestamps: np.ndarray,
        bank_amounts: np.ndarray,
        bank_timestamps: np.ndarray,
        max_time_diff_sec: int = 259200,  # 72 hours in seconds
    ) -> np.ndarray:
        """
        JIT-compiled greedy 1:1 match on amounts and timestamps.
        Returns paired index matrix of shape (M, 2) where M is number of matches found.
        Each row is [rzp_index, bank_index].
        """
        n_rzp = len(rzp_amounts)
        n_bank = len(bank_amounts)

        # Pre-allocate maximum possible pairs (upper bound = min(n_rzp, n_bank))
        max_pairs = min(n_rzp, n_bank)
        pairs = np.empty((max_pairs, 2), dtype=np.int64)
        pair_count = 0

        used_bank = np.zeros(n_bank, dtype=np.bool_)

        for i in range(n_rzp):
            for j in range(n_bank):
                if used_bank[j]:
                    continue
                if rzp_amounts[i] == bank_amounts[j]:
                    t_delta = rzp_timestamps[i] - bank_timestamps[j]
                    if t_delta < 0:
                        t_delta = -t_delta
                    if t_delta <= max_time_diff_sec:
                        pairs[pair_count, 0] = i
                        pairs[pair_count, 1] = j
                        pair_count += 1
                        used_bank[j] = True
                        break

        return pairs[:pair_count]

    _NUMBA_AVAILABLE = True

except Exception:
    # Numba not installed or failed to import — will use pure-Python fallback
    _NUMBA_AVAILABLE = False

    def numba_greedy_1to1_match(  # type: ignore
        rzp_amounts: np.ndarray,
        rzp_timestamps: np.ndarray,
        bank_amounts: np.ndarray,
        bank_timestamps: np.ndarray,
        max_time_diff_sec: int = 259200,
    ) -> np.ndarray:
        """
        Pure NumPy fallback for greedy 1:1 matching.
        Identical semantics to the Numba JIT version.
        """
        n_rzp = len(rzp_amounts)
        n_bank = len(bank_amounts)

        pairs: List[Tuple[int, int]] = []
        used_bank = np.zeros(n_bank, dtype=bool)

        for i in range(n_rzp):
            for j in range(n_bank):
                if used_bank[j]:
                    continue
                if rzp_amounts[i] == bank_amounts[j]:
                    t_delta = abs(int(rzp_timestamps[i]) - int(bank_timestamps[j]))
                    if t_delta <= max_time_diff_sec:
                        pairs.append((i, j))
                        used_bank[j] = True
                        break

        if not pairs:
            return np.empty((0, 2), dtype=np.int64)
        return np.array(pairs, dtype=np.int64)


def build_amount_timestamp_arrays(
    transactions: list,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Converts a list of CanonicalTransaction objects into parallel
    int64 NumPy arrays for amount_net_paise and Unix timestamp (seconds).
    """
    amounts = np.array([t.amount_net_paise for t in transactions], dtype=np.int64)
    timestamps = np.array(
        [int(t.timestamp_utc.timestamp()) for t in transactions], dtype=np.int64
    )
    return amounts, timestamps


def is_numba_available() -> bool:
    """Returns whether Numba JIT acceleration is active."""
    return _NUMBA_AVAILABLE
