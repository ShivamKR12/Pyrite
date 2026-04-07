from settings import *
from world_objects.chunk import Chunk
from voxel_handler import VoxelHandler
import concurrent.futures
import os


class World:
    def __init__(self, app):
        self.app = app
        self.chunks = [None for _ in range(WORLD_VOL)]
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.mesh_queue = []
        self.build_queue = []
        
        # Check if a saved world exists!
        if os.path.exists('world_data.npy'):
            with open('world_data.npy', 'rb') as f:
                self.voxels = np.load(f)
            self.build_chunks(load_from_disk=True)
        else:
            self.voxels = np.empty([WORLD_VOL, CHUNK_VOL], dtype='uint8')
            self.build_chunks(load_from_disk=False)
        self.build_chunk_mesh()
        self.voxel_handler = VoxelHandler(self)

    def update(self):
        self.voxel_handler.update()
        
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

    def build_chunks(self, load_from_disk=False):
        for x in range(WORLD_W):
            for y in range(WORLD_H):
                for z in range(WORLD_D):
                    chunk = Chunk(self, position=(x, y, z))

                    chunk_index = x + WORLD_W * z + WORLD_AREA * y
                    self.chunks[chunk_index] = chunk

                    # put the chunk voxels in a separate array
                    if not load_from_disk:
                        self.voxels[chunk_index] = chunk.build_voxels()

                    # get pointer to voxels
                    chunk.voxels = self.voxels[chunk_index]
                    
                    if load_from_disk and np.any(chunk.voxels):
                        chunk.is_empty = False

    def build_chunk_mesh(self):
        self.build_queue = []
        for chunk in self.chunks:
            chunk.build_mesh()
            self.build_queue.append(chunk)
            
        # Sort chunks so the ones closest to the player are built first
        player_pos = self.app.player.position
        self.build_queue.sort(key=lambda chunk: glm.distance(chunk.center, player_pos), reverse=True)
        
        # WARM UP NUMBA COMPILER:
        # Process the very first chunk on the main thread.
        # This prevents the ThreadPool from deadlocking while trying to JIT compile simultaneously!
        if self.build_queue:
            chunk = self.build_queue.pop()
            chunk.mesh.rebuild()

    def render(self):
        for chunk in self.chunks:
            chunk.render()
            
    def save(self):
        np.save('world_data.npy', self.voxels)
