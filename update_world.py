import re

with open('src/world.py', 'r') as f:
    code = f.read()

batch_func = """    def _fetch_or_generate_voxels_batch(self, batch):
        results = {}
        for x, y, z in batch:
            results[(x, y, z)] = self._fetch_or_generate_voxels(x, y, z)
        return results

"""

code = code.replace(
    "    @global_profiler.profile_func('Stream_Chunks')",
    batch_func + "    @global_profiler.profile_func('Stream_Chunks')",
)


stream_chunks_old = """
        for position in chunks_to_load:
            self.load_chunk(*position)"""

stream_chunks_new = """
        batch_size = 8
        batches = [chunks_to_load[i:i + batch_size] for i in range(0, len(chunks_to_load), batch_size)]

        for batch in batches:
            future = self.executor.submit(self._fetch_or_generate_voxels_batch, batch)
            for position in batch:
                self.load_chunk_sync(*position, future)"""

code = code.replace(stream_chunks_old, stream_chunks_new)

load_chunk_old = '''    @global_profiler.profile_func('Load_Chunk')
    def load_chunk(self, x: int, y: int, z: int) -> None:
        """
        Initializes a Chunk instance at the given coordinates and dispatches
        an asynchronous task to fetch or generate its actual voxel data.
        """
        # Register chunk
        chunk_index = (x % WORLD_WIDTH) + WORLD_WIDTH * (z % WORLD_DEPTH) + WORLD_AREA * (y % WORLD_HEIGHT)
        old_chunk = self.chunks[chunk_index]
        if old_chunk:
            self.unload_chunk(old_chunk.position)

        # Create chunk
        chunk = Chunk(self, position=(x, y, z))
        self.chunks[chunk_index] = chunk
        self.active_chunks[(x, y, z)] = chunk

        # Dispatch load task
        future = self.executor.submit(self._fetch_or_generate_voxels, x, y, z)
        self.load_queue.append((chunk, future))'''

load_chunk_new = '''    @global_profiler.profile_func('Load_Chunk')
    def load_chunk_sync(self, x: int, y: int, z: int, future: 'concurrent.futures.Future') -> None:
        """
        Initializes a Chunk instance and associates it with an existing batch future.
        """
        chunk_index = (x % WORLD_WIDTH) + WORLD_WIDTH * (z % WORLD_DEPTH) + WORLD_AREA * (y % WORLD_HEIGHT)
        old_chunk = self.chunks[chunk_index]
        if old_chunk:
            self.unload_chunk(old_chunk.position)

        chunk = Chunk(self, position=(x, y, z))
        self.chunks[chunk_index] = chunk
        self.active_chunks[(x, y, z)] = chunk

        self.load_queue.append((chunk, future))

    def load_chunk(self, x: int, y: int, z: int) -> None:
        # Legacy fallback if used elsewhere
        future = self.executor.submit(self._fetch_or_generate_voxels_batch, [(x, y, z)])
        self.load_chunk_sync(x, y, z, future)'''

code = code.replace(load_chunk_old, load_chunk_new)


process_load_queue_old = """            if future.done():
                source, elapsed_time, voxel_data, lightmap_data, is_empty, needs_lighting = future.result()"""

process_load_queue_new = """            if future.done():
                all_results = future.result()
                if chunk.position not in all_results:
                    self.load_queue.remove(item)
                    continue
                source, elapsed_time, voxel_data, lightmap_data, is_empty, needs_lighting = all_results[chunk.position]"""

code = code.replace(process_load_queue_old, process_load_queue_new)

with open('src/world.py', 'w') as f:
    f.write(code)

print('Updated world.py to thread batching')
