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

    CREATE TABLE chunks (
        x INTEGER,
        y INTEGER,
        z INTEGER,
        data BLOB,              -- Compressed 1D uint8 array (voxel IDs)
        lightmap BLOB,          -- Compressed 1D uint8 array (light data)
        
        PRIMARY KEY (x, y, z)
    )

**Row Structure:**

- **x, y, z:** Chunk coordinates (e.g., chunk at x=0, y=0, z=0 covers world voxels 0-47 in each axis)
- **data:** Compressed blob of shape (CHUNK_VOL,) = (110592,) uint8 values (voxel IDs)
- **lightmap:** Compressed blob of shape (CHUNK_VOL,) containing packed sunlight+blocklight (4 bits each)

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

    CREATE TABLE player_data (
        id INTEGER PRIMARY KEY,
        data TEXT                -- JSON serialized player state
    )

**Storage Format:**

The `data` column stores a JSON string containing all player information:

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

    CREATE TABLE world_meta (
        id INTEGER PRIMARY KEY,
        world_name TEXT,
        seed INTEGER,
        game_mode INTEGER,
        creation_date TEXT,
        last_played TEXT
    )

**Stored Fields:**

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

    CREATE TABLE dropped_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voxel_id INTEGER,
        px REAL,                        -- Position X
        py REAL,                        -- Position Y
        pz REAL,                        -- Position Z
        vx REAL,                        -- Velocity X
        vy REAL,                        -- Velocity Y
        vz REAL                         -- Velocity Z
    )

**Row Structure:**

- **id:** Unique item identifier
- **voxel_id:** Block/item type ID
- **px, py, pz:** World position of the item
- **vx, vy, vz:** Velocity vector for physics simulation

Serialization and Compression
------------------------------

**Chunk Serialization:**

.. code-block:: python

    import zlib
    import numpy as np
    
    def serialize_chunk(voxel_array, lightmap_array):
        """Convert chunk data to compressed binary"""
        # voxel_array: (110592,) uint8 array
        # lightmap_array: (110592,) uint8 array
        
        # Convert to bytes
        voxel_bytes = voxel_array.tobytes()      # 110592 bytes
        lightmap_bytes = lightmap_array.tobytes()
        
        # Compress with zlib (default level)
        voxel_compressed = zlib.compress(voxel_bytes)
        lightmap_compressed = zlib.compress(lightmap_bytes)
        
        return voxel_compressed, lightmap_compressed
    
    def deserialize_chunk(voxel_compressed, lightmap_compressed):
        """Decompress and convert back to arrays"""
        voxel_bytes = zlib.decompress(voxel_compressed)
        lightmap_bytes = zlib.decompress(lightmap_compressed)
        
        voxel_array = np.frombuffer(voxel_bytes, dtype=np.uint8).copy()
        lightmap_array = np.frombuffer(lightmap_bytes, dtype=np.uint8).copy()
        
        return voxel_array, lightmap_array

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

    import sqlite3
    
    def create_world_database(world_name, seed):
        """Initialize new world database"""
        db_path = f'saves/{world_name}.db'
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        # Enable WAL mode for performance
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')  # Balance safety/speed
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                x INTEGER, y INTEGER, z INTEGER,
                data BLOB, lightmap BLOB,
                PRIMARY KEY (x, y, z)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_data (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS world_meta (
                id INTEGER PRIMARY KEY,
                world_name TEXT,
                seed INTEGER,
                game_mode INTEGER,
                creation_date TEXT,
                last_played TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dropped_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voxel_id INTEGER,
                px REAL, py REAL, pz REAL,
                vx REAL, vy REAL, vz REAL
            )
        ''')
        
        conn.commit()
        return conn

**Save Chunk:**

.. code-block:: python

    def save_chunk_to_db(cursor, conn, x, y, z, voxels, lightmap):
        """Compress and store chunk data"""
        voxel_data = zlib.compress(voxels.tobytes())
        lightmap_data = zlib.compress(lightmap.tobytes()) if lightmap is not None else None
        
        cursor.execute(
            'INSERT OR REPLACE INTO chunks (x, y, z, data, lightmap) VALUES (?, ?, ?, ?, ?)',
            (x, y, z, voxel_data, lightmap_data)
        )
        conn.commit()

**Load Chunk:**

.. code-block:: python

    def load_chunk_from_db(cursor, x, y, z):
        """Retrieve and decompress chunk data"""
        cursor.execute('SELECT data, lightmap FROM chunks WHERE x=? AND y=? AND z=?', (x, y, z))
        row = cursor.fetchone()
        
        if row:
            voxel_data = np.frombuffer(zlib.decompress(row[0]), dtype='uint8').copy()
            lightmap_data = np.frombuffer(zlib.decompress(row[1]), dtype='uint8').copy() if row[1] else None
            return voxel_data, lightmap_data
        
        return None, None

**Save Player Data:**

.. code-block:: python

    def save_player_data(cursor, conn, player_state_dict):
        """Save player state as JSON"""
        json_data = json.dumps(player_state_dict)
        cursor.execute('INSERT OR REPLACE INTO player_data (id, data) VALUES (1, ?)', (json_data,))
        conn.commit()

**Load Player Data:**

.. code-block:: python

    def load_player_data(cursor):
        """Load and deserialize player state"""
        cursor.execute('SELECT data FROM player_data WHERE id=1')
        row = cursor.fetchone()
        
        if row:
            return json.loads(row[0])
        
        return None
            CREATE TABLE player_data (
                id INTEGER PRIMARY KEY,
                x REAL, y REAL, z REAL,
                yaw REAL, pitch REAL,
                health REAL, hunger REAL, oxygen REAL,
                inventory TEXT, inventory_counts TEXT,
                hotbar_index INTEGER, timestamp INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE world_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Store metadata
        cursor.execute("INSERT INTO world_meta VALUES (?, ?)", ("seed", seed))
        cursor.execute("INSERT INTO world_meta VALUES (?, ?)", ("created_time", int(time.time())))
        cursor.execute("INSERT INTO world_meta VALUES (?, ?)", ("game_mode", "SURVIVAL"))
        
        conn.commit()
        conn.close()

**Save Chunk:**

.. code-block:: python

    def save_chunk_to_db(conn, chunk_x, chunk_y, chunk_z, voxels, lightmap):
        """Save chunk to database (insert or update)"""
        cursor = conn.cursor()
        
        voxel_compressed, lightmap_compressed = serialize_chunk(voxels, lightmap)
        timestamp = int(time.time())
        
        # UPSERT pattern (insert or replace)
        cursor.execute('''
            INSERT OR REPLACE INTO chunks 
            (x, y, z, voxel_data, lightmap_data, generated, timestamp)

Asynchronous I/O and Threading
-------------------------------

**Background Save Operations:**

Pyrite uses a ThreadPoolExecutor to handle database saves asynchronously, preventing the main game loop from blocking:

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    class World:
        def __init__(self):
            self.executor = ThreadPoolExecutor(max_workers=max(4, (os.cpu_count() or 5) - 1))
            self.db_lock = threading.Lock()
            self.connection = sqlite3.connect(self.save_path, check_same_thread=False)
        
        def unload_chunk(self, pos):
            """Queue chunk save to background thread"""
            if pos in self.active_chunks:
                chunk = self.active_chunks.pop(pos)
                
                if not chunk.is_empty and chunk.voxels is not None:
                    # Submit save task to thread pool
                    lightmap_copy = chunk.lightmap.copy() if chunk.lightmap else None
                    self.executor.submit(
                        self.save_chunk_to_db,
                        pos[0], pos[1], pos[2],
                        chunk.voxels.copy(),
                        lightmap_copy
                    )
        
        def save_chunk_to_db(self, x, y, z, voxels, lightmap):
            """Thread-safe chunk save"""
            data = zlib.compress(voxels.tobytes())
            l_data = zlib.compress(lightmap.tobytes()) if lightmap is not None else None
            
            with self.db_lock:
                self.cursor.execute(
                    'INSERT OR REPLACE INTO chunks (x, y, z, data, lightmap) VALUES (?, ?, ?, ?, ?)',
                    (x, y, z, data, l_data)
                )
                self.connection.commit()

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

    def list_worlds():
        """Find all saved worlds"""
        worlds = []
        saves_dir = 'saves'
        
        if not os.path.exists(saves_dir):
            return worlds
        
        for world_name in os.listdir(saves_dir):
            world_path = os.path.join(saves_dir, world_name)
            db_file = os.path.join(world_path, f'{world_name}.db')
            
            if os.path.isfile(db_file):
                # Load metadata
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                cursor.execute("SELECT value FROM world_meta WHERE key='created_time'")
                created = cursor.fetchone()[0] if cursor.fetchone() else 0
                
                cursor.execute("SELECT value FROM world_meta WHERE key='game_mode'")
                mode = cursor.fetchone()[0] if cursor.fetchone() else 'SURVIVAL'
                
                conn.close()
                
                worlds.append({
                    'name': world_name,
                    'path': db_file,
                    'created': created,
                    'mode': mode
                })
        
        return worlds

**Delete World:**

.. code-block:: python

    def delete_world(world_name):
        """Delete world and all save files"""
        import shutil
        
        world_path = f'saves/{world_name}'
        if os.path.exists(world_path):
            shutil.rmtree(world_path)

WAL Mode Benefits
-----------------

SQLite's Write-Ahead Logging (WAL) mode provides:

1. **Non-blocking writes:** Readers don't block writers (and vice versa)
2. **Batch commits:** Multiple chunks written in single transaction
3. **Crash recovery:** Partial writes recovered safely
4. **Performance:** 2-10x faster than default journaling

**Enable WAL:**

.. code-block:: python

    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')  # Balance safety (FULL=safer, NORMAL=faster)
    conn.close()

Replication Checklist
---------------------

1. ✓ Create SQLite schema (3 tables)
2. ✓ Implement chunk serialization (numpy → bytes)
3. ✓ Add zlib compression
4. ✓ Implement CRUD operations (save/load)
5. ✓ Set up threading and queues
6. ✓ Enable WAL mode
7. ✓ Handle database cleanup on quit
8. ✓ Implement world listing from filesystem


