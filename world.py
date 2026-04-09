from settings import *
from world_objects.chunk import Chunk
from voxel_handler import VoxelHandler
import concurrent.futures
import os


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
        
        # WARM UP NUMBA COMPILER:
        # Generate a dummy mesh on the main thread to compile Numba JIT safely
        _dummy = Chunk(self, position=(0,0,0))
        _dummy.voxels = np.zeros(CHUNK_VOL, dtype='uint8')
        _dummy.build_mesh()
        _dummy.mesh.rebuild()

    def update(self):
        self.voxel_handler.update()
        self.stream_chunks()
        
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
        
        self.voxels[chunk_index] = chunk.build_voxels()
        chunk.voxels = self.voxels[chunk_index]
        
        chunk.build_mesh()
        self.build_queue.append(chunk)
        
        # Force remesh of neighbors to clean up boundaries
        for dx, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            n_pos = (x + dx, y, z + dz)
            if n_pos in self.active_chunks:
                n_chunk = self.active_chunks[n_pos]
                if n_chunk not in self.build_queue:
                    n_chunk.mesh.rebuild()
                    self.build_queue.append(n_chunk)

    def unload_chunk(self, pos):
        if pos in self.active_chunks:
            chunk = self.active_chunks.pop(pos)
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
        for chunk in self.active_chunks.values():
            chunk.render()
            
    def save(self):
        # Region-based dynamic saving will be built in the future!
        pass
