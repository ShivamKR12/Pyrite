from settings import *
from world_objects.chunk import Chunk
from meshes.cube_mesh import CubeMesh
from voxel_handler import VoxelHandler
import concurrent.futures
import numpy as np
import os
import sqlite3
import zlib
import threading
import time
import moderngl as mgl


class World:
    def __init__(self, app):
        self.app = app
        self.chunks = [None for _ in range(WORLD_VOL)]
        self.active_chunks = {}
        self.chunk_positions = np.full((WORLD_VOL, 3), -999, dtype='int32')
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.mesh_queue = []
        self.build_queue = []
        
        self.voxels = np.empty([WORLD_VOL, CHUNK_VOL], dtype='uint8')
        self.voxel_handler = VoxelHandler(self)
        self.vbo_pool = []
        self.bbox_mesh = CubeMesh(app)

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
        # Generate a dummy mesh on the main thread to compile Numba JIT safely
        print("[SYSTEM] Warming up Numba JIT Compiler... this may take a few seconds.")
        t0 = time.perf_counter()
        _dummy = Chunk(self, position=(0,0,0))
        _dummy.voxels = _dummy.build_voxels()
        _dummy.build_mesh()
        _dummy.mesh.vertex_data = _dummy.mesh.get_vertex_data()
        _dummy.mesh.vao = _dummy.mesh.get_vao()
        print(f"[SYSTEM] Numba compilation finished in {time.perf_counter() - t0:.3f} seconds!")

    def update(self):
        self.db_load_time = 0.0
        self.terrain_gen_time = 0.0

        self.voxel_handler.update()
        self.stream_chunks()
        
        if self.db_load_time > 0 or self.terrain_gen_time > 0:
            print(f"[FRAME TIME] Chunk Loading -> DB Read: {self.db_load_time:.4f}s | Terrain Gen: {self.terrain_gen_time:.4f}s")

        # Submit tasks gradually to prevent ThreadPool starvation and startup lag
        while self.build_queue and len(self.mesh_queue) < 4:
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
                chunk.mesh.vertex_data = future.result()
                
                # Recycle the old VBO/VAO to prevent memory leaks during chunk remeshing
                if chunk.mesh.vao and chunk.mesh.vbo:
                    self.vbo_pool.append((chunk.mesh.vbo, chunk.mesh.vao))
                    
                chunk.mesh.vao = chunk.mesh.get_vao()
                self.mesh_queue.remove(item)
                ready_count += 1
                if ready_count >= 2:  # Process max 2 per frame to keep FPS high
                    break

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
        for x in range(player_cx - render_dist, player_cx + render_dist + 1):
            for z in range(player_cz - render_dist, player_cz + render_dist + 1):
                if (x - player_cx)**2 + (z - player_cz)**2 > render_dist**2:
                    continue
                for y in range(WORLD_H):
                    if (x, y, z) not in self.active_chunks:
                        self.load_chunk(x, y, z)
                        
    def load_chunk(self, x, y, z):
        chunk_index = (x % WORLD_W) + WORLD_W * (z % WORLD_D) + WORLD_AREA * (y % WORLD_H)
        
        old_chunk = self.chunks[chunk_index]
        if old_chunk:
            self.unload_chunk(old_chunk.position)
            
        chunk = Chunk(self, position=(x, y, z))
        self.chunks[chunk_index] = chunk
        self.active_chunks[(x, y, z)] = chunk
        self.chunk_positions[chunk_index] = (x, y, z)
        
        t0 = time.perf_counter()
        with self.db_lock:
            self.cursor.execute('SELECT data FROM chunks WHERE x=? AND y=? AND z=?', (x, y, z))
            row = self.cursor.fetchone()
            
        if row:
            voxel_data = np.frombuffer(zlib.decompress(row[0]), dtype='uint8')
            self.voxels[chunk_index] = voxel_data
            if not np.any(voxel_data):
                chunk.is_empty = True
            else:
                chunk.is_empty = False
            self.db_load_time += time.perf_counter() - t0
        else:
            self.voxels[chunk_index] = chunk.build_voxels()
            self.terrain_gen_time += time.perf_counter() - t0

        chunk.voxels = self.voxels[chunk_index]
        
        chunk.build_mesh()
        self.build_queue.append(chunk)
        
        # Force remesh of neighbors to clean up boundaries
        for dx, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            n_pos = (x + dx, y, z + dz)
            if n_pos in self.active_chunks:
                n_chunk = self.active_chunks[n_pos]
                if n_chunk not in self.build_queue:
                    self.build_queue.append(n_chunk)

    def save_chunk_to_db(self, x, y, z, voxels):
        data = zlib.compress(voxels.tobytes())
        with self.db_lock:
            self.cursor.execute('INSERT OR REPLACE INTO chunks (x, y, z, data) VALUES (?, ?, ?, ?)', (x, y, z, data))
            self.conn.commit()

    def unload_chunk(self, pos):
        if pos in self.active_chunks:
            chunk = self.active_chunks.pop(pos)

            if not chunk.is_empty:
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

    def render(self):
        # Sort chunks front-to-back for Early-Z hardware depth culling
        player_pos = self.app.player.position
        sorted_chunks = sorted(
            self.active_chunks.values(),
            key=lambda c: (c.center.x - player_pos.x)**2 + (c.center.y - player_pos.y)**2 + (c.center.z - player_pos.z)**2
        )

        freeze = getattr(self.app, 'freeze_culling', False)
        
        # 1. Update visibility from occlusion queries
        if not freeze:
            for chunk in sorted_chunks:
                if chunk.is_empty:
                    chunk.is_visible = False
                    continue
                    
                if chunk.query_submitted:
                    chunk.is_visible = chunk.query.samples > 0
                else:
                    chunk.is_visible = True

        # 2. Render visible chunks AND query them simultaneously
        for chunk in sorted_chunks:
            if chunk.is_visible:
                if not freeze and not chunk.is_on_frustum(chunk):
                    chunk.is_visible = False
                    chunk.query_submitted = False
                    continue
                    
                if not freeze:
                    with chunk.query:
                        chunk.render()
                    chunk.query_submitted = True
                else:
                    chunk.render()
                
        # 3. Issue occlusion queries for INVISIBLE chunks
        if not freeze:
            ctx = self.app.ctx
            # Reliably get the active framebuffer across all ModernGL versions
            fbo = getattr(ctx, 'fbo', getattr(ctx, 'screen', getattr(ctx, 'default_framebuffer', None)))
                
            if fbo:
                fbo.color_mask = (False, False, False, False)
                fbo.depth_mask = False
            ctx.depth_func = '<='
            ctx.disable(mgl.CULL_FACE)
            
            # Grab our lightweight voxel_marker shader and the tiny cube mesh
            bbox_prog = self.app.shader_program.voxel_marker
            bbox_vao = self.bbox_mesh.vao
            
            bbox_prog['is_bbox'] = 1
            
            for chunk in sorted_chunks:
                if not chunk.is_visible:
                    if chunk.is_empty or not chunk.is_on_frustum(chunk):
                        chunk.query_submitted = False
                        continue
                        
                    # Render a tiny 12-triangle bounding box instead of the massive chunk mesh!
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
            
    def save(self):
        # Save all currently active chunks synchronously
        for chunk in self.active_chunks.values():
            if not chunk.is_empty:
                self.save_chunk_to_db(chunk.position[0], chunk.position[1], chunk.position[2], chunk.voxels)

        # Wait for any pending asynchronous saves from unload_chunk to complete
        self.executor.shutdown(wait=True)
        self.conn.close()
