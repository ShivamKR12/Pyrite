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
        voxel_data BLOB,        -- Compressed 1D uint8 array
        lightmap_data BLOB,     -- Compressed 1D uint8 array
        generated BOOLEAN,      -- Whether terrain was procedurally generated
        timestamp INTEGER,      -- Unix timestamp of last save
        
        PRIMARY KEY (x, y, z)
    )

**Row Structure:**

- **x, y, z:** Chunk coordinates (e.g., chunk at x=0, y=0, z=0 covers world voxels 0-47 in each axis)
- **voxel_data:** Compressed blob of shape (CHUNK_VOL,) = (110592,) uint8 values
- **lightmap_data:** Compressed blob of shape (CHUNK_VOL,) containing packed sunlight+blocklight (4 bits each)
- **generated:** True if chunk was procedurally generated (not hand-edited)
- **timestamp:** Used for cleanup/optimization later

**Chunk Coordinate Mapping:**

.. code-block:: text

    World voxel (x, y, z) → Chunk coordinate
    chunk_x = floor(x / CHUNK_SIZE)     # CHUNK_SIZE = 48
    chunk_y = floor(y / CHUNK_SIZE)
    chunk_z = floor(z / CHUNK_SIZE)
    
    Local voxel index within chunk:
    local_index = (x % 48) + (z % 48) * 48 + (y % 48) * 48² = flat_index

**2. Player Data Table**

Stores player position, inventory, and survival stats.

.. code-block:: sql

    CREATE TABLE player_data (
        id INTEGER PRIMARY KEY,
        x REAL,                         -- Position X
        y REAL,                         -- Position Y
        z REAL,                         -- Position Z
        yaw REAL,                       -- Rotation angle (radians)
        pitch REAL,                     -- Rotation angle (radians)
        health REAL,                    -- 0-20
        hunger REAL,                    -- 0-20
        oxygen REAL,                    -- 0-20
        inventory JSON,                 -- JSON array of voxel IDs
        inventory_counts JSON,          -- JSON array of stack sizes
        hotbar_index INTEGER,           -- Selected slot
        timestamp INTEGER
    )

**Storage Format:**

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
        "inventory_counts": [64, 32, 0, 0, 1, 0, 0, 0, 0, 0]
    }

**3. World Meta Table**

Stores world-level metadata (seed, difficulty, game mode).

.. code-block:: sql

    CREATE TABLE world_meta (
        key TEXT PRIMARY KEY,
        value TEXT              -- JSON serialized
    )

**Stored Keys:**

.. code-block:: text

    seed:               Integer seed (or MD5 hash of string seed)
    difficulty:        String ('PEACEFUL', 'EASY', 'NORMAL', 'HARD')
    game_mode:         String ('SURVIVAL', 'CREATIVE')
    created_time:      Unix timestamp of world creation
    last_played:       Unix timestamp of last save
    player_name:       Player name/UUID
    spawn_x, spawn_y, spawn_z: Spawn location

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
        
        # Compress with zlib (level 6 default)
        voxel_compressed = zlib.compress(voxel_bytes, level=6)
        lightmap_compressed = zlib.compress(lightmap_bytes, level=6)
        
        return voxel_compressed, lightmap_compressed
    
    def deserialize_chunk(voxel_compressed, lightmap_compressed):
        """Decompress and convert back to arrays"""
        voxel_bytes = zlib.decompress(voxel_compressed)
        lightmap_bytes = zlib.decompress(lightmap_compressed)
        
        voxel_array = np.frombuffer(voxel_bytes, dtype=np.uint8).reshape((110592,))
        lightmap_array = np.frombuffer(lightmap_bytes, dtype=np.uint8).reshape((110592,))
        
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
        db_path = f'saves/{world_name}/{world_name}.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for performance
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')  # Balance safety/speed
        
        # Create tables
        cursor.execute('''
            CREATE TABLE chunks (
                x INTEGER, y INTEGER, z INTEGER,
                voxel_data BLOB, lightmap_data BLOB,
                generated BOOLEAN, timestamp INTEGER,
                PRIMARY KEY (x, y, z)
            )
        ''')
        
        cursor.execute('''
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
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (chunk_x, chunk_y, chunk_z, voxel_compressed, lightmap_compressed, True, timestamp))
        
        conn.commit()

**Load Chunk:**

.. code-block:: python

    def load_chunk_from_db(conn, chunk_x, chunk_y, chunk_z):
        """Load chunk from database"""
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT voxel_data, lightmap_data 
            FROM chunks 
            WHERE x=? AND y=? AND z=?
        ''', (chunk_x, chunk_y, chunk_z))
        
        row = cursor.fetchone()
        if row is None:
            return None  # Chunk not in database
        
        voxel_compressed, lightmap_compressed = row
        voxels, lightmap = deserialize_chunk(voxel_compressed, lightmap_compressed)
        
        return voxels, lightmap

**Save Player Data:**

.. code-block:: python

    def save_player_data(conn, player):
        """Save player position, inventory, stats"""
        import json
        
        cursor = conn.cursor()
        
        player_data = {
            'x': float(player.feet_pos.x),
            'y': float(player.feet_pos.y),
            'z': float(player.feet_pos.z),
            'yaw': float(player.yaw),
            'pitch': float(player.pitch),
            'health': float(player.health),
            'hunger': float(player.hunger),
            'oxygen': float(player.oxygen),
            'inventory': player.inventory,
            'inventory_counts': player.inventory_counts,
            'hotbar_index': player.hotbar_index,
        }
        
        cursor.execute('''
            INSERT OR REPLACE INTO player_data 
            (id, x, y, z, yaw, pitch, health, hunger, oxygen, inventory, inventory_counts, hotbar_index, timestamp)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            player_data['x'], player_data['y'], player_data['z'],
            player_data['yaw'], player_data['pitch'],
            player_data['health'], player_data['hunger'], player_data['oxygen'],
            json.dumps(player_data['inventory']),
            json.dumps(player_data['inventory_counts']),
            player_data['hotbar_index'],
            int(time.time())
        ))
        
        conn.commit()

**Load Player Data:**

.. code-block:: python

    def load_player_data(conn):
        """Load player from database"""
        import json
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM player_data WHERE id=1')
        row = cursor.fetchone()
        
        if row is None:
            # New world: return spawn point
            return {
                'x': 0, 'y': 64, 'z': 0,
                'yaw': 0, 'pitch': 0,
                'health': 20, 'hunger': 20, 'oxygen': 20,
                'inventory': [0] * 41,
                'inventory_counts': [0] * 41,
                'hotbar_index': 0
            }
        
        # Parse from database
        return {
            'x': row[1], 'y': row[2], 'z': row[3],
            'yaw': row[4], 'pitch': row[5],
            'health': row[6], 'hunger': row[7], 'oxygen': row[8],
            'inventory': json.loads(row[9]),
            'inventory_counts': json.loads(row[10]),
            'hotbar_index': row[11]
        }

Asynchronous I/O and Threading
-------------------------------

**Background Save Queue:**

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    import threading
    
    class WorldPersistence:
        def __init__(self, world_name):
            self.db_path = f'saves/{world_name}/{world_name}.db'
            self.save_queue = Queue()  # (chunk_x, chunk_y, chunk_z, voxels, lightmap)
            self.executor = ThreadPoolExecutor(max_workers=2)
            self.lock = threading.Lock()
        
        def queue_chunk_save(self, chunk_x, chunk_y, chunk_z, voxels, lightmap):
            """Queue chunk for background save"""
            self.save_queue.put((chunk_x, chunk_y, chunk_z, voxels, lightmap))
        
        def process_save_queue(self):
            """Called from background thread"""
            while True:
                try:
                    chunk_x, chunk_y, chunk_z, voxels, lightmap = self.save_queue.get(timeout=1)
                    
                    with threading.Lock():  # Thread-safe DB access
                        conn = sqlite3.connect(self.db_path)
                        save_chunk_to_db(conn, chunk_x, chunk_y, chunk_z, voxels, lightmap)
                        conn.close()
                except:
                    pass  # Timeout, continue
        
        def shutdown(self):
            """Flush all queued saves before closing"""
            while not self.save_queue.empty():
                chunk_data = self.save_queue.get()
                # Synchronously save remaining chunks
                conn = sqlite3.connect(self.db_path)
                save_chunk_to_db(conn, *chunk_data)
                conn.close()

**Main Thread Integration:**

.. code-block:: python

    # On world load
    persistence = WorldPersistence(world_name)
    save_thread = threading.Thread(target=persistence.process_save_queue, daemon=True)
    save_thread.start()
    
    # On chunk unload (main thread)
    persistence.queue_chunk_save(chunk_x, chunk_y, chunk_z, voxels, lightmap)
    
    # On application quit
    persistence.shutdown()  # Block until all chunks saved

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


