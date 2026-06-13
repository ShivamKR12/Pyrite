.. _survival:

============================
Survival & Physics Mechanics
============================

Pyrite includes a fully functional collision and physics engine to support its survival gameplay loop.

Player Physics & AABB Collisions
--------------------------------
The player is represented as an Axis-Aligned Bounding Box (AABB) parameterized by `PLAYER_WIDTH` and `PLAYER_HEIGHT`.

To ensure smooth wall-sliding and prevent corner-snagging, velocity movement is separated into distinct X, Y, and Z axis steps. After moving along a single axis, the engine loops over the immediate surrounding voxel grid using `glm.floor()`. If a solid block intersects with the player's AABB, the player's position is snapped perfectly flush to the face of the voxel, halting velocity on that axis while allowing movement on the others to continue smoothly.

**Fluid Dynamics:**
When the player enters a `WATER` block, a heavy dampening multiplier is applied to the velocity vectors to simulate liquid drag. The jump mechanics are overridden, allowing the player to swim upward, and a "dolphin leap" velocity boost is applied when breaking the surface of the water.

Inventory & Crafting
--------------------
The UI handles a complete 41-slot inventory system:
* **Slots 0-8:** Hotbar
* **Slots 9-35:** Main Storage
* **Slots 36-39:** 2x2 Crafting Grid
* **Slot 40:** Crafting Output

The entire UI allows for left-click stack swapping and right-click stack halving.

**Crafting Matrix:**
The 2x2 crafting grid matches the four input slots against a hardcoded dictionary tuple matrix (e.g., `(WOOD, 0, 0, 0): (WOOD_PLANKS, 4)`). If a match is found, the output slot populates. When the player left-clicks to extract the crafted item, exactly 1 count is iteratively removed from all participating input slots.

Tool Dependencies & Mining Hardness
-----------------------------------
Every block has a specific hardness mapped in `BLOCK_HARDNESS` (measured in milliseconds to break). The engine applies dynamic multipliers based on the item currently held in the player's hand. For example, attempting to mine `STONE` with bare hands applies a `5x` penalty multiplier, while holding a `WOODEN_PICKAXE` divides the base hardness by `5.0`.

3D Item Entities
----------------
When blocks are mined, they are spawned into the world as independent `Item` instances. These items possess their own isolated velocity and gravity vectors, allowing them to bounce and slide across the voxel terrain until they fall asleep.

When the player walks within the `ITEM_PICKUP_RADIUS`, the items are destroyed and injected into the player's inventory array. To protect CPU physics threads and GPU draw limits from entity overflow, the `ItemManager` enforces a hard FIFO (First-In-First-Out) cap of 256 items. If the 257th item drops, the oldest item is instantly despawned.

Next Steps
----------

With the physical gameplay mechanics established, move on to the :doc:`ui` system to learn how 2D interfaces like the hotbar and menus are drawn over the 3D world.
