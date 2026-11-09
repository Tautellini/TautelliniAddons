"""Self-check for preview.barrier_mask on a synthetic map. Run: py -3.13 test_barrier.py"""
import numpy as np

import preview

N = 200
preview.SS = 2
preview.BARRIER_MIN_CELLS = 10  # every cliff ring in this small map counts as a range


def walled(steep, ground, row, col, height):
    """A square cliff ring 40 cells wide whose inside sits at the given height."""
    steep[row:row + 40, col:col + 40] = True
    steep[row + 3:row + 37, col + 3:col + 37] = False
    ground[row + 3:row + 37, col + 3:col + 37] = height
    return row + 20, col + 20  # center of the pocket


steep, ground = np.zeros((N, N), bool), np.zeros((N, N), np.float32)
mesa = walled(steep, ground, 20, 20, 50.0)
pit = walled(steep, ground, 20, 120, -50.0)
road_shelf = walled(steep, ground, 120, 20, 50.0)
cave_shelf = walled(steep, ground, 120, 120, 50.0)
road = np.zeros((N * 2, N * 2), bool)
road[road_shelf[0] * 2, road_shelf[1] * 2] = True
none, hi = np.zeros((N, N), bool), np.zeros((N * 2, N * 2), bool)
masks = {"steep": steep, "raw_steep": steep, "ground": ground, "water": none, "slime": none, "lava": none, "tar": none, "sky": none,
         "in_zone": np.ones((N, N), bool), "bridge": hi, "building": hi, "road": road,
         "entrances": [(cave_shelf[0] * preview.SS, cave_shelf[1] * preview.SS)]}
barrier = preview.barrier_mask(masks)

assert barrier[mesa], "a shelf above its surroundings is cut off"
assert not barrier[pit], "players can drop into a pit"
assert not barrier[road_shelf], "a road means there is a way up"
assert not barrier[cave_shelf], "a cave entrance means there is a way up"
assert barrier[20, 20] and not barrier[100, 100], "cliffs are barrier, open ground is not"

# A floating island: the flat sky around it is bigger than the island but is not ground.
sky, rim, island = np.ones((N, N), bool), np.zeros((N, N), bool), np.full((N, N), 1.5, np.float32)
sky[50:150, 50:150] = False
rim[50:150, 50:150] = True
rim[53:147, 53:147] = False
island[50:150, 50:150] = 200.0
floating = preview.barrier_mask({**masks, "steep": rim, "raw_steep": rim, "ground": island, "sky": sky,
                                 "road": np.zeros((N * 2, N * 2), bool), "entrances": []})
assert not floating[100, 100], "the land of a floating island is reachable"

plateau = np.zeros((N, N), np.float32)
plateau[85:115, 85:115] = 100.0
relief = preview.height_above_floor({**masks, "ground": plateau, "steep": none, "barrier": none})
assert relief[100, 100] > 80, "a plateau stands high above the floor around it"
assert abs(relief[5, 5]) < 10, "the open floor has no height"
print("ok")
