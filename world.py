from settings import *
from world_objects.chunk import Chunk
from meshes.cube_mesh import CubeMesh
from voxel_handler import VoxelHandler
import concurrent.futures
import glm
import numpy as np
import os
import sqlite3
import zlib
import threading
import time
import moderngl as mgl
from frustum import frustum_cull_fast


class World:
    def __init__(self, app):
        self.app = app
        self.app.render_loading_screen("ALLOCATING MEMORY...")
        self.chunks = [None for _ in range(WORLD_VOL)]
        self.active_chunks = {}
        self.chunk_positions = np.full((WORLD_VOL, 3), -999, dtype='int32')
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(4, (os.cpu_count() or 5) - 1))
        self.mesh_queue = []
        self.build_queue = []
        self.load_queue = []
        
        self.voxels = np.empty([WORLD_VOL, CHUNK_VOL], dtype='uint8')
        self.voxel_handler = VoxelHandler(self)
        self.vbo_pool = []
        self.last_player_chunk_pos = None
        self.sorted_chunks = []
        self.last_active_chunk_count = 0
        self.chunk_centers = np.empty((0, 3), dtype='float32')
        self.bbox_mesh = CubeMesh(app)

        self.app.render_loading_screen("CONNECTING TO DATABASE...")
        self.save_path = 'save.db'
        self.db_lock = threading.Lock()
        self.conn = sqlite3.connect(self.save_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chunks (
                                x INTEGER, y INTEGER, z INTEGER, 
                                data BLOB,
                                PRIMARY KEY (x, y, z))''')
        self.conn.commit()
        
        # WARM UP NUMBA COMPILER:
        # Run Numba compilation on a background thread so the main thread can keep pumping Pygame events!
        self.app.render_loading_screen("COMPILING NUMBA JIT (MAY TAKE A MOMENT)...")
        print("[SYSTEM] Warming up Numba JIT Compiler... this may take a few seconds.")
        t0 = time.perf_counter()
        
        def compile_numba():
            from meshes.chunk_mesh_builder import build_chunk_mesh
            dummy_voxels = np.zeros(CHUNK_VOL, dtype='uint8')
            Chunk.generate_terrain(dummy_voxels, 0, 0, 0)
            build_chunk_mesh(
                chunk_voxels=dummy_voxels,
                format_size=1,
                chunk_pos=(0, 0, 0),
                world_voxels=self.voxels,
                chunk_positions=self.chunk_positions
            )
            
        future = self.executor.submit(compile_numba)
        
        while not future.done():
            self.app.render_loading_screen("COMPILING NUMBA JIT (MAY TAKE A MOMENT)...")
            self.app.clock.tick(60)
            
        print(f"[SYSTEM] Numba compilation finished in {time.perf_counter() - t0:.3f} seconds!")
        self.app.render_loading_screen("NUMBA COMPILATION SUCCESSFUL!")

    def update(self):
        self.db_load_time = 0.0
        self.terrain_gen_time = 0.0

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
        mesh_limit = 4 if self.app.game_state != 'LOADING' else 64
        while self.build_queue and len(self.mesh_queue) < mesh_limit:
            chunk = self.build_queue.pop()
            future = self.executor.submit(chunk.mesh.get_vertex_data)
            self.mesh_queue.append((chunk, future))
            
        self.process_mesh_queue()

    def process_mesh_queue(self):
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
                    
                chunk.mesh.vao = chunk.mesh.get_vao()
                self.mesh_queue.remove(item)
                ready_count += 1
                if ready_count >= 2 and self.app.game_state != 'LOADING':  # Process max 2 per frame to keep FPS high
                    break

    def process_load_queue(self):
        for item in list(self.load_queue):
            chunk, future = item
            if future.done():
                source, elapsed_time, voxel_data, is_empty = future.result()
                
                if source == 'db':
                    self.db_load_time += elapsed_time
                else:
                    self.terrain_gen_time += elapsed_time

                # Only apply if the chunk wasn't unloaded while loading
                if self.active_chunks.get(chunk.position) is chunk:
                    chunk_index = (chunk.position[0] % WORLD_W) + WORLD_W * (chunk.position[2] % WORLD_D) + WORLD_AREA * (chunk.position[1] % WORLD_H)
                    
                    self.voxels[chunk_index] = voxel_data
                    chunk.voxels = self.voxels[chunk_index]
                    chunk.is_empty = is_empty
                    self.chunk_positions[chunk_index] = chunk.position
                    
                    chunk.build_mesh()
                    self.build_queue.append(chunk)

                    # Force remesh of neighbors to clean up boundaries
                    x, y, z = chunk.position
                    for dx, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        n_pos = (x + dx, y, z + dz)
                        if n_pos in self.active_chunks:
                            n_chunk = self.active_chunks[n_pos]
                            if n_chunk.voxels is not None and n_chunk not in self.build_queue:
                                self.build_queue.append(n_chunk)
                
                self.load_queue.remove(item)

    def _fetch_or_generate_voxels(self, x, y, z):
        t0 = time.perf_counter()
        with self.db_lock:
            self.cursor.execute('SELECT data FROM chunks WHERE x=? AND y=? AND z=?', (x, y, z))
            row = self.cursor.fetchone()

        if row:
            voxel_data = np.frombuffer(zlib.decompress(row[0]), dtype='uint8').copy()
            is_empty = not np.any(voxel_data)
            return ('db', time.perf_counter() - t0, voxel_data, is_empty)
        else:
            voxel_data = np.zeros(CHUNK_VOL, dtype='uint8')
            cx, cy, cz = x * CHUNK_SIZE, y * CHUNK_SIZE, z * CHUNK_SIZE
            Chunk.generate_terrain(voxel_data, cx, cy, cz)
            is_empty = not np.any(voxel_data)
            return ('gen', time.perf_counter() - t0, voxel_data, is_empty)

    def stream_chunks(self):
        render_dist = int(self.app.config.get('render_distance', 4))
        player_cx = int(self.app.player.position.x // CHUNK_SIZE)
        player_cz = int(self.app.player.position.z // CHUNK_SIZE)
        
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
                        
    def load_chunk(self, x, y, z):
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

    def save_chunk_to_db(self, x, y, z, voxels):
        data = zlib.compress(voxels.tobytes())
        with self.db_lock:
            self.cursor.execute('INSERT OR REPLACE INTO chunks (x, y, z, data) VALUES (?, ?, ?, ?)', (x, y, z, data))
            self.conn.commit()

    def unload_chunk(self, pos):
        if pos in self.active_chunks:
            chunk = self.active_chunks.pop(pos)

            if not chunk.is_empty and chunk.voxels is not None:
                self.executor.submit(self.save_chunk_to_db, pos[0], pos[1], pos[2], chunk.voxels)

            chunk_index = (pos[0] % WORLD_W) + WORLD_W * (pos[2] % WORLD_D) + WORLD_AREA * (pos[1] % WORLD_H)
            self.chunks[chunk_index] = None
            self.chunk_positions[chunk_index] = (-999, -999, -999)
            if chunk.mesh:
                if chunk.mesh.vao and chunk.mesh.vbo:
                    self.vbo_pool.append((chunk.mesh.vbo, chunk.mesh.vao))
                chunk.mesh.vbo, chunk.mesh.vao = None, None
            if chunk in self.build_queue:
                self.build_queue.remove(chunk)
            for item in list(self.load_queue):
                if item[0] is chunk:
                    self.load_queue.remove(item)
                    break

    def render(self):
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
            else:
                self.chunk_centers = np.empty((0, 3), dtype='float32')
            self.last_player_chunk_pos = player_chunk_pos
            self.last_active_chunk_count = active_chunk_count
            
        freeze = getattr(self.app, 'freeze_culling', False)
        
        # Vectorized frustum culling
        frustum_mask = np.ones(len(self.sorted_chunks), dtype=np.bool_)
        if not freeze and len(self.chunk_centers) > 0:
            frustum = player.frustum
            frustum_mask = frustum_cull_fast(
                self.chunk_centers, np.array(player_pos, dtype='float32'), 
                np.array(player.forward, dtype='float32'), np.array(player.right, dtype='float32'), 
                np.array(player.up, dtype='float32'),
                frustum.tan_y, frustum.tan_x, frustum.factor_y, frustum.factor_x
            )

        # 1. Update visibility from occlusion queries
        if not freeze:
            for i, chunk in enumerate(self.sorted_chunks):
                if not frustum_mask[i] or chunk.is_empty:
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
                    if chunk.is_empty or not frustum_mask[i]:
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
            
    def render_water(self):
        # We assume visibility is already calculated by the primary render() pass!
        freeze = getattr(self.app, 'freeze_culling', False)
        for chunk in self.sorted_chunks:
            if chunk.is_visible:
                chunk.render_water()
            
    def save(self):
        # Save all currently active chunks synchronously
        for chunk in self.active_chunks.values():
            if not chunk.is_empty and chunk.voxels is not None:
                self.save_chunk_to_db(chunk.position[0], chunk.position[1], chunk.position[2], chunk.voxels)

        # Wait for any pending asynchronous saves from unload_chunk to complete
        self.executor.shutdown(wait=True)
        self.conn.close()
