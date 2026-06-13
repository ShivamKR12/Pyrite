.. _persistence:

World Persistence and Data Storage
===================================

This document details Pyrite's SQLite-based world persistence system, including database schema, chunk serialization, compression, async I/O, and world metadata management.

Overview
--------

Pyrite persists world data using SQLite with Write-Ahead Logging (WAL) mode for high-performance, asynchronous writes. This allows the game loop to remain responsive while data is written in background threads.

**Key Components:**

1. **Database File:** ``saves/<world_name>/<world_name>.db`` (SQLite database)
2. **Tables:** ``chunks``, ``player_data``, ``world_meta``
3. **Compression:** zlib (1:5 ratio typical for voxel data)
4. **Threading:** Background threads handle I/O; main thread reads/writes safely via locks

Database Schema
---------------

**1. Chunks Table**

Stores terrain voxel data and lightmaps for each chunk.

.. code-block:: sql

    CREATE TABLE chunks (x INTEGER, y INTEGER, z INTEGER, data BLOB, lightmap BLOB, PRIMARY KEY (x, y, z))

* **Chunks Table:** Stores the `x`, `y`, `z` coordinates and the heavily compressed NumPy `BLOB` objects representing physical block IDs and BFS volumetric light.

* **Indexing Integrity:** Local indices within a 48x48 chunk are natively resolved strictly to their flat integer via `local_index = (x % 48) + (z % 48) * 48 + (y % 48) * 48²`.

**Note:** The `lightmap` column was added via schema migration (`ALTER TABLE chunks ADD COLUMN lightmap BLOB`) to support lightmap caching in existing worlds.

**Chunk Coordinate Mapping:**

.. code-block:: text

    World voxel (x, y, z) → Chunk coordinate
    chunk_x = floor(x / CHUNK_SIZE)     # CHUNK_SIZE = 48
    chunk_y = floor(y / CHUNK_SIZE)
    chunk_z = floor(z / CHUNK_SIZE)

    Local voxel index within chunk:
    local_index = (x % 48) + (z % 48) * 48 + (y % 48) * 48² = flat_index

**2. Player Data Table**

Stores player position, inventory, and survival stats as serialized JSON.

.. code-block:: sql

    CREATE TABLE player_data (id INTEGER PRIMARY KEY, data TEXT)

* **Player Serialization:** Binds dynamic dictionaries containing position vectors and arrays directly to simple string payloads.

.. code-block:: json

    {
        "x": 128.5,
        "y": 64.0,
        "z": 256.75,
        "yaw": 1.57,
        "pitch": 0.0,
        "health": 20,
        "hunger": 15,
        "oxygen": 20,
        "inventory": [1, 5, 0, 0, 2, 0, 0, 0, 0, 0],
        "inventory_counts": [64, 32, 0, 0, 1, 0, 0, 0, 0, 0],
        "hotbar_index": 0
    }

**3. World Meta Table**

Stores world-level metadata (seed, game mode, creation date).

.. code-block:: sql

    CREATE TABLE world_meta (id INTEGER PRIMARY KEY, world_name TEXT, seed INTEGER, game_mode INTEGER, creation_date TEXT, last_played TEXT)

* **Engine Meta:** Boot params explicitly flag creative toggles and generation integers mapped by `id`.

.. code-block:: text

    id:                 Primary key (typically 1 for single world)
    world_name:         Name of the world/save
    seed:               Integer seed used for procedural generation
    game_mode:          0=CREATIVE, 1=SURVIVAL
    creation_date:      ISO format timestamp of world creation
    last_played:        ISO format timestamp of last play session

**4. Dropped Items Table**

Stores data for items dropped in the world.

.. code-block:: sql

    CREATE TABLE dropped_items (id INTEGER PRIMARY KEY AUTOINCREMENT, voxel_id INTEGER, px REAL, py REAL, pz REAL, vx REAL, vy REAL, vz REAL)

* **Entities Record:** Caches unbound ground collision vectors mapped exclusively per-game instance.

Serialization and Compression
------------------------------

**Chunk Serialization:**

.. code-block:: python

    voxel_bytes = voxel_array.tobytes()
    voxel_compressed = zlib.compress(voxel_bytes)

* **ZLib Compression:** Transforms 110592-index flat buffers straight into highly condensed bytes safely.

.. code-block:: python

    voxel_array = np.frombuffer(zlib.decompress(voxel_compressed), dtype=np.uint8).copy()

* **Restoration Phase:** Explodes byte BLOBs cleanly back to NumPy instances using explicit types.

**Compression Ratios:**

.. code-block:: text

    Terrain Type        Compressed Size    Ratio
    Dense terrain       ~25 KB             1:4.4 (stone/dirt/grass)
    Cave systems        ~15 KB             1:7.4 (many air gaps)
    Mixed biomes        ~35 KB             1:3.2 (varied blocks)

    Typical world with 1,440 chunks (30x5x30):
    Uncompressed: 1,440 * 110,592 * 2 bytes ≈ 318 MB
    Compressed:   1,440 * 25 KB average ≈ 36 MB

Database Operations
-------------------

**Initialize Database (at world creation):**

.. code-block:: python

    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor.execute('PRAGMA journal_mode=WAL')

* **Initialization:** Skips standard lock bindings allowing non-blocking I/O operations dynamically per-session file.

**Save Chunk:**

.. code-block:: python

    cursor.execute('INSERT OR REPLACE INTO chunks (x, y, z, data, lightmap) VALUES (?, ?, ?, ?, ?)', (x, y, z, voxel_data, lightmap_data))

* **Upsert Commit:** Overwrites previously saved geographical records immediately or pushes fresh memory blobs explicitly.

**Load Chunk:**

.. code-block:: python

    cursor.execute('SELECT data, lightmap FROM chunks WHERE x=? AND y=? AND z=?', (x, y, z))

* **Location Seeking:** Finds specifically tied tuples per execution.

**Save Player Data:**

.. code-block:: python

    json_data = json.dumps(player_state_dict)
    cursor.execute('INSERT OR REPLACE INTO player_data (id, data) VALUES (1, ?)', (json_data,))

* **Status Upsert:** Single explicit dicts dumped over primary static rows seamlessly.

**Load Player Data:**

.. code-block:: python

    row = cursor.fetchone()
    return json.loads(row[0]) if row else None

* **Status Recovery:** Unpacks string objects immediately back to Python memory instances.

Asynchronous I/O and Threading
-------------------------------

**Background Save Operations:**

Pyrite uses a ThreadPoolExecutor to handle database saves asynchronously, preventing the main game loop from blocking:

.. code-block:: python

    self.executor = ThreadPoolExecutor(max_workers=max(4, (os.cpu_count() or 5) - 1))
    self.db_lock = threading.Lock()

* **ThreadPool Isolation:** Threading queues independently submit disk write commands avoiding full render stalling during chunk teardowns.

.. code-block:: python

    self.executor.submit(self.save_chunk_to_db, x, y, z, voxels.copy(), lightmap.copy())

* **Non-Blocking Eviction:** Pushing memory to concurrent futures allows main Pygame flow continuation smoothly.

**Main Thread Integration:**

.. code-block:: python

    # On world init
    world = World(app, save_name, seed)

    # On chunk unload (main thread queues, background thread handles)
    world.unload_chunk(chunk_position)

    # On application quit
    world.save()  # Block until all chunks flushed

World Management (File System)
------------------------------

**Directory Structure:**

.. code-block:: text

    saves/
        MyWorld/
            MyWorld.db          # SQLite database
            MyWorld.db-shm      # Shared memory (WAL)
            MyWorld.db-wal      # Write-ahead log
        AnotherWorld/
            AnotherWorld.db
            ...

**List Worlds:**

.. code-block:: python

    for world_name in os.listdir('saves'):
        pass

* **Menu Indexing:** OS module recursively finds instances to build display parameters effortlessly.

**Delete World:**

.. code-block:: python

    if os.path.exists(world_path):
        shutil.rmtree(world_path)

* **Deep Cleaning:** Removes associated filesystem paths fully off drives.

WAL Mode Benefits
-----------------

SQLite's Write-Ahead Logging (WAL) mode provides:

1. **Non-blocking writes:** Readers don't block writers (and vice versa)
2. **Batch commits:** Multiple chunks written in single transaction
3. **Crash recovery:** Partial writes recovered safely
4. **Performance:** 2-10x faster than default journaling

**Enable WAL:**

.. code-block:: python

    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')  # Balance safety (FULL=safer, NORMAL=faster)

* **I/O Balance:** Activates specialized SQLite caching behaviors maximizing engine speeds directly without hard freezing read capabilities on chunk boundaries.

Next Steps
----------

Now that you know how chunks are saved and loaded from SQLite, explore the :doc:`terrain` system to learn how these chunks are procedurally generated from scratch using noise.
