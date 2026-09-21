import pytest
from pathlib import Path
from squeezenest._core.cache import SQLiteNFPCache, TieredNFPCache
import time

def test_sqlite_cache_lru(tmp_path: Path):
    db_path = tmp_path / "test.db"
    # Limit max size to 3 for easy testing
    cache = SQLiteNFPCache(db_path, max_size=3)
    
    # Put 3 items
    cache.put("key1", [[1, 2], [3, 4]])
    time.sleep(0.01) # ensure different timestamps
    cache.put("key2", [[5, 6]])
    time.sleep(0.01)
    cache.put("key3", [[7, 8]])
    
    assert len(cache) == 3
    
    # Read key1 so it becomes most recently used
    assert cache.get("key1") == [[1, 2], [3, 4]]
    time.sleep(0.01)
    
    # Put 4th item, should evict key2 (oldest)
    cache.put("key4", [[9, 10]])
    
    assert len(cache) == 3
    assert cache.get("key2") is None # Evicted
    assert cache.get("key1") is not None
    assert cache.get("key3") is not None
    assert cache.get("key4") is not None

def test_tiered_cache(tmp_path: Path):
    db_path = tmp_path / "tiered.db"
    cache = TieredNFPCache(mem_size=2, db_path=db_path, db_size=5)
    
    cache.put("k1", [[1,1]])
    
    # Should be in both
    assert cache.t1.get("k1") == [[1,1]]
    assert cache.t2.get("k1") == [[1,1]]
    
    # If we clear memory, it should restore from sqlite
    cache.t1._store.clear()
    assert cache.t1.get("k1") is None
    
    assert cache.get("k1") == [[1,1]] # This will fetch from t2 and put in t1
    assert cache.t1.get("k1") == [[1,1]]
