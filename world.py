from settings import *
from world_objects.chunk import Chunk
from voxel_handler import VoxelHandler
import concurrent.futures


class World:
    def __init__(self, app):
        self.app = app
        self.chunks = [None for _ in range(WORLD_VOL)]
        self.voxels = np.empty([WORLD_VOL, CHUNK_VOL], dtype='uint8')
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.mesh_queue = []
        
        self.build_chunks()
        self.build_chunk_mesh()
        self.voxel_handler = VoxelHandler(self)

    def update(self):
        self.voxel_handler.update()
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

    def build_chunks(self):
        for x in range(WORLD_W):
            for y in range(WORLD_H):
                for z in range(WORLD_D):
                    chunk = Chunk(self, position=(x, y, z))

                    chunk_index = x + WORLD_W * z + WORLD_AREA * y
                    self.chunks[chunk_index] = chunk

                    # put the chunk voxels in a separate array
                    self.voxels[chunk_index] = chunk.build_voxels()

                    # get pointer to voxels
                    chunk.voxels = self.voxels[chunk_index]

    def build_chunk_mesh(self):
        for chunk in self.chunks:
            chunk.build_mesh()
            # Submit the Numba mesh generation to a background thread
            future = self.executor.submit(chunk.mesh.get_vertex_data)
            self.mesh_queue.append((chunk, future))

    def render(self):
        for chunk in self.chunks:
            chunk.render()
