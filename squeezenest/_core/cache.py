"""squeezenest._core.cache -- NFP (No-Fit Polygon) two-tier cache.

Tier 1: In-process LRU cache (cachetools.LRUCache) for hot NFP lookups.
Tier 2: SQLite on-disk persistence (planned for v0.2; stub here).

Cache Key design (Invariant I-06: symmetry):
    make_cache_key(A, B, rA, rB, d) == make_cache_key(B, A, rB, rA, d)

    The key is a SHA-256 hex digest of a canonical representation obtained by:
      1. Computing a stable fingerprint for each polygon (SHA-256 of its
         canonically-ordered vertex bytes).
      2. Forming a sorted pair of (fingerprint, rotation) tuples so that
         swapping (A, rA) <-> (B, rB) produces the same ordering.
      3. Hashing (sorted_pair, clearance_int) to produce the final key.

All coordinates are int64 scale units (see squeezenest._core.scale).
"""
from __future__ import annotations

import hashlib
import struct
from collections import OrderedDict
from typing import Any

__all__ = ["make_cache_key", "NFPCache"]

# Type aliases
Polygon = list[tuple[int, int]]


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def _poly_fingerprint(poly: Polygon) -> bytes:
    """Stable SHA-256 fingerprint of a polygon's vertex sequence.

    Normalised to the lexicographically-smallest rotation of the vertex list
    so that the same shape in different starting-vertex representations still
    produces the same fingerprint.
    """
    n = len(poly)
    # Canonicalise: choose the rotation that starts at the lexicographically
    # smallest vertex (handles different start-vertex representations).
    min_idx = min(range(n), key=lambda i: poly[i])
    rotated = poly[min_idx:] + poly[:min_idx]
    raw = b"".join(struct.pack("<qq", x, y) for x, y in rotated)
    return hashlib.sha256(raw).digest()


def make_cache_key(
    poly_a: Polygon,
    poly_b: Polygon,
    rot_a_mdeg: int,
    rot_b_mdeg: int,
    clearance_int: int,
) -> str:
    """Generate a symmetric SHA-256 cache key for an NFP entry.

    The key is invariant under swapping (poly_a, rot_a_mdeg) <-> (poly_b, rot_b_mdeg),
    satisfying Invariant I-06.

    Args:
        poly_a:        First polygon (int64 scale units).
        poly_b:        Second polygon (int64 scale units).
        rot_a_mdeg:    Rotation of poly_a in milli-degrees (0 = unrotated).
        rot_b_mdeg:    Rotation of poly_b in milli-degrees.
        clearance_int: Inter-part clearance in int64 scale units.

    Returns:
        Hex-encoded SHA-256 digest string (64 characters).
    """
    fp_a = _poly_fingerprint(poly_a)
    fp_b = _poly_fingerprint(poly_b)

    # Build (fingerprint, rotation) token for each polygon
    token_a = fp_a + struct.pack("<q", rot_a_mdeg)
    token_b = fp_b + struct.pack("<q", rot_b_mdeg)

    # Sort tokens to achieve symmetry invariant I-06
    ordered = sorted([token_a, token_b])

    # Final hash = SHA-256(sorted_token_a || sorted_token_b || clearance)
    h = hashlib.sha256()
    h.update(ordered[0])
    h.update(ordered[1])
    h.update(struct.pack("<q", clearance_int))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# LRU Cache (Tier 1)
# ---------------------------------------------------------------------------

class NFPCache:
    """In-process LRU cache for No-Fit Polygon results.

    Backed by collections.OrderedDict for O(1) get/put/evict.

    Args:
        max_size: Maximum number of NFP entries to hold in memory.
    """

    def __init__(self, max_size: int) -> None:
        if max_size < 1:
            raise ValueError(f"max_size must be >= 1, got {max_size}")
        self._max_size = max_size
        self._store: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        """Retrieve an NFP by key.  Returns None on cache miss.

        Moves the accessed entry to the end (most-recently-used).
        """
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def put(self, key: str, value: Any) -> None:
        """Store an NFP entry. Evicts the least-recently-used entry on overflow."""
        if key in self._store:
            self._store.move_to_end(key)
        else:
            if len(self._store) >= self._max_size:
                self._store.popitem(last=False)  # evict LRU (front)
        self._store[key] = value

    def __len__(self) -> int:
        return len(self._store)
