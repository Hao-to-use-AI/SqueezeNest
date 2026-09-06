# tests/core/test_nfp_cache.py
import pytest
from squeezenest._core.cache import make_cache_key, NFPCache

POLY_A = [(0, 0), (1_000_000, 0), (1_000_000, 1_000_000), (0, 1_000_000)]
POLY_B = [(0, 0), (500_000, 0), (500_000, 500_000), (0, 500_000)]


# Invariant I-06: symmetry
def test_cache_key_symmetry():
    key_ab = make_cache_key(POLY_A, POLY_B, rot_a_mdeg=0, rot_b_mdeg=0, clearance_int=100_000)
    key_ba = make_cache_key(POLY_B, POLY_A, rot_a_mdeg=0, rot_b_mdeg=0, clearance_int=100_000)
    assert key_ab == key_ba


def test_cache_key_differs_on_clearance():
    key_1 = make_cache_key(POLY_A, POLY_B, 0, 0, clearance_int=100_000)
    key_2 = make_cache_key(POLY_A, POLY_B, 0, 0, clearance_int=200_000)
    assert key_1 != key_2


def test_cache_key_differs_on_rotation():
    key_0  = make_cache_key(POLY_A, POLY_B, rot_a_mdeg=0,      rot_b_mdeg=0, clearance_int=100_000)
    key_90 = make_cache_key(POLY_A, POLY_B, rot_a_mdeg=90_000, rot_b_mdeg=0, clearance_int=100_000)
    assert key_0 != key_90


def test_lru_cache_stores_and_retrieves():
    cache = NFPCache(max_size=10)
    key = make_cache_key(POLY_A, POLY_B, 0, 0, 100_000)
    fake_nfp = [(100, 100), (200, 100), (200, 200)]
    cache.put(key, fake_nfp)
    assert cache.get(key) == fake_nfp


def test_lru_cache_evicts_on_overflow():
    cache = NFPCache(max_size=2)
    k1 = make_cache_key(POLY_A, POLY_B, 0,       0, 100_000)
    k2 = make_cache_key(POLY_A, POLY_B, 0,  90_000, 100_000)
    k3 = make_cache_key(POLY_A, POLY_B, 0, 180_000, 100_000)
    cache.put(k1, [(0, 0)])
    cache.put(k2, [(1, 1)])
    cache.put(k3, [(2, 2)])  # k1 should be LRU-evicted
    assert cache.get(k1) is None
    assert cache.get(k3) == [(2, 2)]


def test_lru_cache_miss_returns_none():
    cache = NFPCache(max_size=10)
    key = make_cache_key(POLY_A, POLY_B, 0, 0, 999_999)
    assert cache.get(key) is None
