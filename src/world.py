"""
Global 3D environment and multi-threading architecture controller.

The World manager orchestrates the engine's asynchronous lifeblood: dynamic chunk 
streaming, ThreadPool dispatching for mesh generation and lighting, and background 
Write-Ahead Logging (WAL) SQLite disk saving/loading. It directly handles the 
GPU dispatch via hardware occlusion queries and dynamic vectorized frustum culling.
"""

import concurrent.futures
from pyglm import glm
import numpy as np
import os
import sqlite3
import zlib
import threading
from collections import deque
import json
import time
import moderngl as mgl
import datetime
from typing import Any, Dict, List, Optional, Tuple
from numpy.typing import NDArray

from settings import (
    WORLD_VOL, CHUNK_VOL, CHUNK_SIZE, WORLD_W, WORLD_H, WORLD_D, WORLD_AREA, 
    PLAYER_EYE_HEIGHT, MESH_BUILD_LIMIT_INGAME, MESH_BUILD_LIMIT_LOADING, 
    MAIN_THREAD_MESH_PROCESS_LIMIT_INGAME, MAIN_THREAD_MESH_PROCESS_LIMIT_LOADING, 
    MAIN_THREAD_CHUNK_PROCESS_LIMIT_INGAME, MAIN_THREAD_CHUNK_PROCESS_LIMIT_LOADING, 
    VBO_POOL_CAP
)
from world_objects.chunk import Chunk
from meshes.cube_mesh import CubeMesh
from voxel_handler import VoxelHandler
from frustum import frustum_cull_fast
from meshes.chunk_mesh_builder import build_chunk_mesh
from lighting import init_chunk_lighting, stitch_chunk_lighting, update_light_place_block, update_light_remove_block, place_torch
import noise
from profiler import global_profiler


class World:
    """
    Manages the global 3D voxel environment.
    
    Responsible for chunk streaming, multithreaded terrain generation, mesh 
    building queues, and persistent background SQLite disk storage. It acts
    as the central hub linking the player, terrain data, lighting updates,
    and GPU render dispatching.
    
    Args:
        app (Any): The main Pyrite application instance.
        save_name (str): The string identifier/filename for the SQLite world database.
        world_seed (int): The deterministic seed used for procedural terrain generation.
    """
    @global_profiler.profile_func("World_Init")
    def __init__(self, app: Any, save_name: str, world_seed: int) -> None:
        """
        Initializes the world arrays, establishes an async-like SQLite database 
        connection, restores player data, and warms up the Numba compiler.
        """
        self.world_seed: int = world_seed
        self.app: Any = app
        self.app.render_loading_screen("ALLOCATING MEMORY...")
        self.chunks: List[Optional[Any]] = [None for _ in range(WORLD_VOL)]
        self.active_chunks: Dict[Tuple[int, int, int], Any] = {}
        self.chunk_positions: NDArray[np.int32] = np.full((WORLD_VOL, 3), -999, dtype='int32')
        
        self.executor: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(max_workers=max(4, (os.cpu_count() or 5) - 1))
        self.mesh_queue: List[Tuple[Any, concurrent.futures.Future[Any]]] = []
        self.build_queue: List[Any] = []
        self.load_queue: List[Tuple[Any, concurrent.futures.Future[Any]]] = []
        
        self.voxels: NDArray[np.uint8] = np.empty([WORLD_VOL, CHUNK_VOL], dtype='uint8')
        self.lightmaps: NDArray[np.uint8] = np.full([WORLD_VOL, CHUNK_VOL], 255, dtype='uint8')
        self.voxel_handler: Any = VoxelHandler(self)
        self.vbo_pool: deque[Tuple[Any, Any]] = deque()
        self.last_player_chunk_pos: Optional[Tuple[int, int]] = None
        self.sorted_chunks: List[Any] = []
        self.last_active_chunk_count: int = 0
        self.chunk_centers: NDArray[np.float32] = np.empty((0, 3), dtype='float32')
        self.frustum_mask: NDArray[np.bool_] = np.empty(0, dtype=np.bool_)
        self.bbox_mesh: Any = CubeMesh(app)

        self.app.render_loading_screen("CONNECTING TO DATABASE...")
        self.save_name: str = save_name
        os.makedirs('saves', exist_ok=True)
        self.save_path: str = f'saves/{self.save_name}.db'
        self.thread_local: threading.local = threading.local()
        self.db_lock: threading.Lock = threading.Lock()
        self.connection: sqlite3.Connection = sqlite3.connect(self.save_path, check_same_thread=False)
        self.cursor: sqlite3.Cursor = self.connection.cursor()
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chunks (
                                x INTEGER, y INTEGER, z INTEGER, 
                                data BLOB,
                                PRIMARY KEY (x, y, z))''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS player_data (
                                id INTEGER PRIMARY KEY,
                                data TEXT)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS world_meta (
                                id INTEGER PRIMARY KEY,
                                world_name TEXT,
                                seed INTEGER,
                                game_mode INTEGER,
                                creation_date TEXT,
                                last_played TEXT)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS dropped_items (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                voxel_id INTEGER,
                                px REAL, py REAL, pz REAL,
                                vx REAL, vy REAL, vz REAL)''')
        
        # Safely upgrade existing databases to support lightmap caching!
        try:
            self.cursor.execute('ALTER TABLE chunks ADD COLUMN lightmap BLOB')
        except sqlite3.OperationalError:
            pass # Column already exists!
            
        self.connection.commit()
        
        # Optimize SQLite for async-like high performance disk writing
        self.cursor.execute('PRAGMA journal_mode = WAL')
        self.cursor.execute('PRAGMA synchronous = NORMAL')
        
        # Initialize metadata if missing (e.g. creating a new world)
        self.cursor.execute('SELECT * FROM world_meta WHERE id=1')
        meta_row = self.cursor.fetchone()
        
        if not meta_row:
            now = datetime.datetime.now().isoformat()
            
            # Use the seed passed from main.py
            self.cursor.execute('''INSERT INTO world_meta (id, world_name, seed, game_mode, creation_date, last_played)
                                   VALUES (?, ?, ?, ?, ?, ?)''', 
                                (1, self.save_name.replace('_', ' '), world_seed, self.app.player.game_mode, now, now))
        
            self.connection.commit()
        
        else:
            self.app.player.game_mode = meta_row[3]

        # Load player inventory and hotbar state
        self.cursor.execute('SELECT data FROM player_data WHERE id=1')
        row = self.cursor.fetchone()
        
        if row:
            try:
                p_data = json.loads(row[0])
                loaded_inv = p_data.get('inventory', [])
                loaded_counts = p_data.get('counts', [])
                
                # Safely copy items over up to the current INVENTORY_SIZE to prevent crashes from old saves
                for i in range(min(len(loaded_inv), len(self.app.player.inventory))):
                    self.app.player.inventory[i] = loaded_inv[i]
                    self.app.player.inventory_counts[i] = loaded_counts[i]
                    
                self.app.player.hotbar_index = p_data.get('hotbar_index', self.app.player.hotbar_index)
                self.app.player.health = p_data.get('health', self.app.player.max_health)
                self.app.player.hunger = p_data.get('hunger', self.app.player.max_hunger)
                self.app.player.oxygen = p_data.get('oxygen', self.app.player.max_oxygen)
                self.app.world_session_time = p_data.get('time_played', 0.0)
                
                pos = p_data.get('position')
                
                if pos:
                    self.app.player.position = glm.vec3(pos[0], pos[1], pos[2])
                    self.app.player.feet_pos = glm.vec3(pos[0], pos[1] - PLAYER_EYE_HEIGHT, pos[2])
                    self.app.player.highest_y = pos[1]
                
                else:
                    self.app.player.respawn()
                    
                yaw = p_data.get('yaw')
                
                if yaw is not None:
                    self.app.player.yaw = yaw
                    
                pitch = p_data.get('pitch')
                
                if pitch is not None:
                    self.app.player.pitch = pitch
            
            except Exception as e:
                print(f"[SYSTEM] Failed to load player data: {e}")
                self.app.player.respawn()
        
        else:
            self.app.player.respawn()
            
        # Load dropped items
        self.saved_dropped_items: List[Any] = []
        
        try:
            self.cursor.execute('SELECT voxel_id, px, py, pz, vx, vy, vz FROM dropped_items')
            self.saved_dropped_items = self.cursor.fetchall()
        
        except sqlite3.OperationalError:
            pass # Table might not exist in old saves before migration

        # WARM UP NUMBA COMPILER:
        # Run Numba compilation on a background thread so the main thread can keep pumping Pygame events!
        self.app.render_loading_screen("COMPILING NUMBA JIT (MAY TAKE A MOMENT)...")
        print("[SYSTEM] Warming up Numba JIT Compiler... this may take a few seconds.")
        t0 = time.perf_counter()
        
        def compile_numba() -> None:
            dummy_voxels = np.zeros(CHUNK_VOL, dtype='uint8')
            dummy_lights = np.full(CHUNK_VOL, 255, dtype='uint8')
            Chunk.generate_terrain(dummy_voxels, dummy_lights, 0, 0, 0, noise.perm, noise.perm_grad_index3, self.world_seed)
            init_chunk_lighting(0, 0, 0, self.voxels, self.lightmaps, self.chunk_positions)
            stitch_chunk_lighting(0, 0, 0, self.voxels, self.lightmaps, self.chunk_positions)
            update_light_place_block(0, 0, 0, self.voxels, self.lightmaps, self.chunk_positions)
            update_light_remove_block(0, 0, 0, self.voxels, self.lightmaps, self.chunk_positions)
            place_torch(0, 0, 0, self.voxels, self.lightmaps, self.chunk_positions)
            build_chunk_mesh(
                chunk_voxels=dummy_voxels,
                chunk_lightmap=dummy_lights,
                format_size=2,
                chunk_pos=(0, 0, 0),
                world_voxels=self.voxels,
                world_lightmaps=self.lightmaps,
                chunk_positions=self.chunk_positions
            )
            
        with global_profiler.measure("Numba_Warmup_Submit"):
            future = self.executor.submit(compile_numba)
        
        while not future.done():
            self.app.render_loading_screen("COMPILING NUMBA JIT (MAY TAKE A MOMENT)...")
            self.app.clock.tick(60)
            
        print(f"[SYSTEM] Numba compilation finished in {time.perf_counter() - t0:.3f} seconds!")
        self.app.render_loading_screen("NUMBA COMPILATION SUCCESSFUL!")

    @global_profiler.profile_func("World_Update")
    def update(self) -> None:
        """
        Tick loop that handles continuous background data processing. Steps through
        loading chunks, dispatching thread-pool mesh tasks, and streaming logic.
        """
        self.db_load_time: float = 0.0
        self.terrain_gen_time: float = 0.0

        self.voxel_handler.update()
        self.stream_chunks()
        self.process_load_queue()
        
        if self.db_load_time > 0 or self.terrain_gen_time > 0:
            print(f"[FRAME TIME] Chunk Loading -> DB Read: {self.db_load_time:.4f}s | Terrain Gen: {self.terrain_gen_time:.4f}s")

        # Sort the build queue so the closest chunks are popped from the end first
        if self.build_queue:
            player_cx = int(self.app.player.position.x // CHUNK_SIZE)
            player_cz = int(self.app.player.position.z // CHUNK_SIZE)
            
            # Optimization: Only re-sort if the player moves to a new chunk or the queue size changes!
            if getattr(self, '_last_sort_pos', None) != (player_cx, player_cz) or getattr(self, '_last_queue_len', None) != len(self.build_queue):
                self.build_queue.sort(key=lambda c: (c.position[0] - player_cx)**2 + (c.position[2] - player_cz)**2, reverse=True)
                self._last_sort_pos = (player_cx, player_cz)
                self._last_queue_len = len(self.build_queue)

        # Submit tasks gradually to prevent ThreadPool starvation and startup lag
        mesh_limit = MESH_BUILD_LIMIT_INGAME if self.app.game_state != 'LOADING' else MESH_BUILD_LIMIT_LOADING
        
        while self.build_queue and len(self.mesh_queue) < mesh_limit:
            chunk = self.build_queue.pop()
            nl = getattr(chunk, 'pending_lighting', False)
            chunk.pending_lighting = False
            
            def build_task(c: Any = chunk, needs_light: bool = nl) -> Any:
                cx, cy, cz = c.position
                if needs_light:
                    init_chunk_lighting(cx * CHUNK_SIZE, cy * CHUNK_SIZE, cz * CHUNK_SIZE, self.voxels, self.lightmaps, self.chunk_positions)
                
                stitch_chunk_lighting(cx * CHUNK_SIZE, cy * CHUNK_SIZE, cz * CHUNK_SIZE, self.voxels, self.lightmaps, self.chunk_positions)
                return c.mesh.get_vertex_data()
                
            future = self.executor.submit(build_task)
            self.mesh_queue.append((chunk, future))
            
        self.process_mesh_queue()

    @global_profiler.profile_func("Process_Mesh_Queue")
    def process_mesh_queue(self) -> None:
        """
        Pulls completed mesh data from background threads and safely initializes 
        OpenGL Vertex Array Objects (VAOs) on the main thread, utilizing a 
        recycling VBO pool to prevent VRAM memory leaks.
        """
        # Safely create OpenGL VAOs on the main thread
        ready_count = 0
        
        for item in list(self.mesh_queue):
            chunk, future = item
            
            if future.done():
                result = future.result()
                chunk.mesh.vertex_data = result[0]
                chunk.mesh.opaque_count = result[1]
                chunk.mesh.water_count = result[2]
                
                # Recycle the old VBO/VAO to prevent memory leaks during chunk remeshing
                if chunk.mesh.vao and chunk.mesh.vbo:
                    self.vbo_pool.append((chunk.mesh.vbo, chunk.mesh.vao))
                    
                    while len(self.vbo_pool) > VBO_POOL_CAP:
                        p_vbo, p_vao = self.vbo_pool.popleft()
                        p_vbo.release()
                        p_vao.release()
                    
                chunk.mesh.vao = chunk.mesh.get_vao()
                self.mesh_queue.remove(item)
                ready_count += 1
                limit = MAIN_THREAD_MESH_PROCESS_LIMIT_LOADING if self.app.game_state == 'LOADING' else MAIN_THREAD_MESH_PROCESS_LIMIT_INGAME
                
                if ready_count >= limit:  # Limit processing to prevent frame drops
                    break

    @global_profiler.profile_func("Process_Load_Queue")
    def process_load_queue(self) -> None:
        """
        Consumes asynchronously loaded/generated chunk data, registers it into 
        the active world arrays, applies volumetric lighting (BFS), and schedules 
        the chunk and its neighbors for mesh building.
        """
        processed = 0
        
        for item in list(self.load_queue):
            chunk, future = item
            
            if future.done():
                source, elapsed_time, voxel_data, lightmap_data, is_empty, needs_lighting = future.result()
                
                if source == 'db':
                    self.db_load_time += elapsed_time
                
                else:
                    self.terrain_gen_time += elapsed_time

                # Only apply if the chunk wasn't unloaded while loading
                if self.active_chunks.get(chunk.position) is chunk:
                    chunk_index = (chunk.position[0] % WORLD_W) + WORLD_W * (chunk.position[2] % WORLD_D) + WORLD_AREA * (chunk.position[1] % WORLD_H)
                    x, y, z = chunk.position
                    
                    self.voxels[chunk_index] = voxel_data
                    chunk.voxels = self.voxels[chunk_index]
                    
                    self.lightmaps[chunk_index] = lightmap_data
                    chunk.lightmap = self.lightmaps[chunk_index]
                    
                    chunk.is_empty = is_empty
                    self.chunk_positions[chunk_index] = chunk.position
                    
                    if needs_lighting:
                        chunk.pending_lighting = True
                    
                    chunk.build_mesh()
                    self.build_queue.append(chunk)

                    # Force remesh of all 6 chunk neighbors to ensure light spills render properly
                    for dx, dy, dz in [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]:
                        n_pos = (x + dx, y + dy, z + dz)
                        
                        if n_pos in self.active_chunks:
                            n_chunk = self.active_chunks[n_pos]
                            
                            if n_chunk.voxels is not None and n_chunk not in self.build_queue:
                                self.build_queue.append(n_chunk)
                
                self.load_queue.remove(item)
                processed += 1
                
                # Limit chunks processed per frame to prevent FPS drops and Main Thread freezing!
                limit = MAIN_THREAD_CHUNK_PROCESS_LIMIT_LOADING if self.app.game_state == 'LOADING' else MAIN_THREAD_CHUNK_PROCESS_LIMIT_INGAME
                
                if processed >= limit:
                    break

    @global_profiler.profile_func("Fetch_Or_Generate_Voxels")
    def _fetch_or_generate_voxels(self, x: int, y: int, z: int) -> Tuple[str, float, NDArray[np.uint8], NDArray[np.uint8], bool, bool]:
        """
        Background worker function that attempts to retrieve compressed chunk data
        from the SQLite database. If the chunk has never been visited, generates 
        brand new procedural terrain using Numba logic instead.
        """
        t0 = time.perf_counter()
        cx, cy, cz = x * CHUNK_SIZE, y * CHUNK_SIZE, z * CHUNK_SIZE
        
        if not hasattr(self.thread_local, 'cursor'):
            conn = sqlite3.connect(self.save_path, timeout=10)
            self.thread_local.cursor = conn.cursor()
            
        self.thread_local.cursor.execute('SELECT data, lightmap FROM chunks WHERE x=? AND y=? AND z=?', (x, y, z))
        row = self.thread_local.cursor.fetchone()

        if row:
            voxel_data = np.frombuffer(zlib.decompress(row[0]), dtype='uint8').copy()
            is_empty = not np.any(voxel_data)
            
            if len(row) > 1 and row[1] is not None:
                # Lightmap exists in DB! Skip expensive Numba BFS calculations entirely!
                lightmap_data = np.frombuffer(zlib.decompress(row[1]), dtype='uint8').copy()
                return ('db', time.perf_counter() - t0, voxel_data, lightmap_data, is_empty, False)
                
            # Old save file format, fallback to generating sunlight
            lightmap_data = np.zeros(CHUNK_VOL, dtype='uint8')
            Chunk.fill_initial_sunlight_only(voxel_data, lightmap_data, cx, cy, cz, noise.perm)
            
            return ('db', time.perf_counter() - t0, voxel_data, lightmap_data, is_empty, True)
            
        voxel_data = np.zeros(CHUNK_VOL, dtype='uint8')
        lightmap_data = np.zeros(CHUNK_VOL, dtype='uint8')
        Chunk.generate_terrain(voxel_data, lightmap_data, cx, cy, cz, noise.perm, noise.perm_grad_index3, self.world_seed)
        is_empty = not np.any(voxel_data)
        
        return ('gen', time.perf_counter() - t0, voxel_data, lightmap_data, is_empty, True)

    @global_profiler.profile_func("Stream_Chunks")
    def stream_chunks(self) -> None:
        """
        Checks the player's position against the render distance to determine 
        which distant chunks to unload, and which new surrounding chunks to queue 
        for background loading.
        """
        render_dist = int(self.app.config.get('render_distance', 4))
        player_cx = int(self.app.player.position.x // CHUNK_SIZE)
        player_cz = int(self.app.player.position.z // CHUNK_SIZE)
        
        # Optimization: Only scan for chunks to stream if the player moves to a new chunk or changes render distance!
        stream_state = (player_cx, player_cz, render_dist)
        
        if getattr(self, 'last_stream_state', None) == stream_state:
            return
            
        self.last_stream_state = stream_state
        
        # 1. Unload chunks out of range
        for pos in list(self.active_chunks.keys()):
            x, y, z = pos
            
            if (x - player_cx)**2 + (z - player_cz)**2 > (render_dist + 1)**2:
                self.unload_chunk(pos)
                
        # 2. Load chunks in range
        chunks_to_load = []
        for x in range(player_cx - render_dist, player_cx + render_dist + 1):
            for z in range(player_cz - render_dist, player_cz + render_dist + 1):
                if (x - player_cx)**2 + (z - player_cz)**2 > render_dist**2:
                    continue
                
                for y in range(WORLD_H):
                    if (x, y, z) not in self.active_chunks:
                        self.load_chunk(x, y, z)
                        chunks_to_load.append((x, y, z))
                        
        # Sort chunks by distance (closest first) so the ThreadPool executes them first
        chunks_to_load.sort(key=lambda pos: (pos[0] - player_cx)**2 + (pos[2] - player_cz)**2)
        
        for pos in chunks_to_load:
            self.load_chunk(*pos)
                        
    @global_profiler.profile_func("Load_Chunk")
    def load_chunk(self, x: int, y: int, z: int) -> None:
        """
        Initializes a Chunk instance at the given coordinates and dispatches 
        an asynchronous task to fetch or generate its actual voxel data.
        """
        chunk_index = (x % WORLD_W) + WORLD_W * (z % WORLD_D) + WORLD_AREA * (y % WORLD_H)
        
        old_chunk = self.chunks[chunk_index]
        if old_chunk:
            self.unload_chunk(old_chunk.position)
            
        chunk = Chunk(self, position=(x, y, z))
        self.chunks[chunk_index] = chunk
        self.active_chunks[(x, y, z)] = chunk
        
        # Send the heavy load task to the background thread pool
        future = self.executor.submit(self._fetch_or_generate_voxels, x, y, z)
        self.load_queue.append((chunk, future))

    @global_profiler.profile_func("Save_Chunk_To_DB")
    def save_chunk_to_db(self, x: int, y: int, z: int, voxels: NDArray[np.uint8], lightmap: Optional[NDArray[np.uint8]]) -> None:
        """
        Compresses a chunk's massive 1D voxel and lighting arrays using zlib, 
        and executes a thread-safe write to the SQLite database.
        """
        data = zlib.compress(voxels.tobytes())
        l_data = zlib.compress(lightmap.tobytes()) if lightmap is not None else None
        
        with self.db_lock:
            self.cursor.execute('INSERT OR REPLACE INTO chunks (x, y, z, data, lightmap) VALUES (?, ?, ?, ?, ?)', (x, y, z, data, l_data))
            self.connection.commit()

    @global_profiler.profile_func("Unload_Chunk")
    def unload_chunk(self, pos: Tuple[int, int, int]) -> None:
        """
        Removes a chunk from the active world space, triggers an asynchronous 
        disk save, purges it from any pending queues, and recycles its VRAM.
        """
        if pos in self.active_chunks:
            chunk = self.active_chunks.pop(pos)

            if not chunk.is_empty and chunk.voxels is not None:
                lightmap_copy = chunk.lightmap.copy() if chunk.lightmap is not None else None
                self.executor.submit(self.save_chunk_to_db, pos[0], pos[1], pos[2], chunk.voxels.copy(), lightmap_copy)

            chunk_index = (pos[0] % WORLD_W) + WORLD_W * (pos[2] % WORLD_D) + WORLD_AREA * (pos[1] % WORLD_H)
            self.chunks[chunk_index] = None
            self.chunk_positions[chunk_index] = (-999, -999, -999)
            
            if chunk.mesh:
                if chunk.mesh.vao and chunk.mesh.vbo:
                    self.vbo_pool.append((chunk.mesh.vbo, chunk.mesh.vao))
                    
                    while len(self.vbo_pool) > VBO_POOL_CAP:
                        p_vbo, p_vao = self.vbo_pool.popleft()
                        p_vbo.release()
                        p_vao.release()
                
                chunk.mesh.vbo, chunk.mesh.vao = None, None
            
            if chunk in self.build_queue:
                self.build_queue.remove(chunk)
            
            for item in list(self.load_queue):
                if item[0] is chunk:
                    self.load_queue.remove(item)
                    break
            
            for item in list(self.mesh_queue):
                if item[0] is chunk:
                    self.mesh_queue.remove(item)
                    break

    @global_profiler.profile_func("World_Render")
    def render(self) -> None:
        """
        Performs dynamic vectorized frustum culling and hardware occlusion 
        queries to identify visible chunks, then safely dispatches rendering 
        calls to the GPU.
        """
        player = self.app.player
        player_pos = player.position
        player_chunk_pos = (int(player_pos.x // CHUNK_SIZE), int(player_pos.z // CHUNK_SIZE))
        active_chunk_count = len(self.active_chunks)

        # Re-sort chunks only when player moves to a new chunk or when chunks are loaded/unloaded
        if player_chunk_pos != self.last_player_chunk_pos or active_chunk_count != self.last_active_chunk_count:
            self.sorted_chunks = sorted(
                self.active_chunks.values(),
                key=lambda c: glm.distance2(c.center, player_pos)
            )
            
            # Update the chunk centers array for vectorized culling
            if self.sorted_chunks:
                self.chunk_centers = np.array([c.center for c in self.sorted_chunks], dtype='float32')
                self.frustum_mask = np.ones(len(self.sorted_chunks), dtype=np.bool_)
            
            else:
                self.chunk_centers = np.empty((0, 3), dtype='float32')
                self.frustum_mask = np.ones(0, dtype=np.bool_)
            
            self.last_player_chunk_pos = player_chunk_pos
            self.last_active_chunk_count = active_chunk_count
            
        freeze = getattr(self.app, 'freeze_culling', False)
        
        # Vectorized frustum culling
        if not freeze and len(self.chunk_centers) > 0:
            frustum = player.frustum
            with global_profiler.measure("Frustum_Culling"):
                frustum_cull_fast(
                    self.chunk_centers, self.frustum_mask, np.array(player_pos, dtype='float32'), 
                    np.array(player.forward, dtype='float32'), np.array(player.right, dtype='float32'), 
                    np.array(player.up, dtype='float32'),
                    frustum.tan_y, frustum.tan_x, frustum.factor_y, frustum.factor_x
                )

        # 1. Update visibility from occlusion queries
        if not freeze:
            for i, chunk in enumerate(self.sorted_chunks):
                if not self.frustum_mask[i] or chunk.is_empty:
                    chunk.is_visible = False
                    continue
                    
                if chunk.query_submitted:
                    chunk.is_visible = chunk.query.samples > 0
                else:
                    chunk.is_visible = True # Assume visible until queried

        # 2. Render visible chunks AND query them simultaneously
        for chunk in self.sorted_chunks:
            if chunk.is_visible:
                
                if not freeze:
                    with chunk.query:
                        chunk.render()
                    chunk.query_submitted = True
                
                else:
                    chunk.render()
            
        # 3. Issue occlusion queries for INVISIBLE chunks
        if not freeze:
            ctx = self.app.ctx
            fbo = getattr(ctx, 'fbo', getattr(ctx, 'screen', getattr(ctx, 'default_framebuffer', None)))
                
            if fbo:
                fbo.color_mask = (False, False, False, False)
                fbo.depth_mask = False
            
            ctx.depth_func = '<='
            ctx.disable(mgl.CULL_FACE)
            
            bbox_prog = self.app.shader_program.voxel_marker
            bbox_vao = self.bbox_mesh.vao
            bbox_prog['is_bbox'] = 1
            
            for i, chunk in enumerate(self.sorted_chunks):
                if not chunk.is_visible:
                    
                    # Only query chunks that are IN the frustum but currently occluded
                    if chunk.is_empty or not self.frustum_mask[i]:
                        chunk.query_submitted = False
                        continue
                        
                    m_model = glm.translate(glm.mat4(), glm.vec3(chunk.position) * CHUNK_SIZE)
                    m_model = glm.scale(m_model, glm.vec3(CHUNK_SIZE))
                    bbox_prog['m_model'].write(m_model)
                    
                    with chunk.query:
                        bbox_vao.render()
                    
                    chunk.query_submitted = True
                    
            bbox_prog['is_bbox'] = 0
            
            if fbo:
                fbo.color_mask = (True, True, True, True)
                fbo.depth_mask = True
            
            ctx.depth_func = '<'
            ctx.enable(mgl.CULL_FACE)
            
    @global_profiler.profile_func("World_Render_Water")
    def render_water(self) -> None:
        """
        A secondary rendering pass explicitly designed to draw transparent water 
        meshes properly blended over the previously drawn opaque terrain.
        """
        # We assume visibility is already calculated by the primary render() pass!
        for chunk in self.sorted_chunks:
            if chunk.is_visible:
                chunk.render_water()
            
    @global_profiler.profile_func("World_Save")
    def save(self) -> None:
        """
        Synchronously dumps all currently active chunks, inventory contents, 
        player coordinates, and world metadata safely to the SQLite disk on exit.
        """
        # Save all currently active chunks synchronously
        for chunk in self.active_chunks.values():
            if not chunk.is_empty and chunk.voxels is not None:
                self.save_chunk_to_db(chunk.position[0], chunk.position[1], chunk.position[2], chunk.voxels, chunk.lightmap)
                
        # Save player inventory, hotbar state & position
        p_data = {
            'inventory': [int(item) for item in self.app.player.inventory],
            'counts': [int(count) for count in self.app.player.inventory_counts],
            'hotbar_index': int(self.app.player.hotbar_index),
            'position': [float(self.app.player.position.x), float(self.app.player.position.y), float(self.app.player.position.z)],
            'yaw': float(self.app.player.yaw),
            'pitch': float(self.app.player.pitch),
            'health': float(self.app.player.health),
            'hunger': float(self.app.player.hunger),
            'oxygen': float(self.app.player.oxygen),
            'time_played': float(self.app.world_session_time)
        }
        
        now = datetime.datetime.now().isoformat()
        with self.db_lock:
            self.cursor.execute('UPDATE world_meta SET last_played = ?, game_mode = ? WHERE id=1', (now, self.app.player.game_mode))
            self.cursor.execute('INSERT OR REPLACE INTO player_data (id, data) VALUES (?, ?)', 
                                (1, json.dumps(p_data)))
                                
            # Save dropped items
            if self.app.scene and hasattr(self.app.scene, 'item_manager'):
                self.cursor.execute('DELETE FROM dropped_items')
                item_data = []
                
                for item in self.app.scene.item_manager.items:
                    item_data.append((item.voxel_id, float(item.position.x), float(item.position.y), float(item.position.z), float(item.velocity.x), float(item.velocity.y), float(item.velocity.z)))
                
                self.cursor.executemany('INSERT INTO dropped_items (voxel_id, px, py, pz, vx, vy, vz) VALUES (?, ?, ?, ?, ?, ?, ?)', item_data)
            
            self.connection.commit()

        # Wait for any pending asynchronous saves from unload_chunk to complete
        self.executor.shutdown(wait=True)
        self.connection.close()
        
        # Safely release heavy OpenGL objects to prevent VRAM leaking when returning to the Main Menu
        for vbo, vao in self.vbo_pool:
            vbo.release()
            vao.release()
        
        self.vbo_pool.clear()
        
        for chunk in self.chunks:
            if chunk:
                if chunk.mesh:
                    if chunk.mesh.vao:
                        chunk.mesh.vao.release()
                    
                    if chunk.mesh.vbo:
                        chunk.mesh.vbo.release()
        
        self.bbox_mesh.vao.release()
