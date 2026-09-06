# Ember Arcanist source contract

All source coordinates use meters, Blender Z-up, front -Y. Height is 1.86 m and the staff is 2.1 m. JSON retains literal vertex coordinates, corner UVs, named parts, slots and finishing modifiers. Grid helpers connect explicit rows; they do not sample a parametric character generator.

The accepted Battle Prelate source topology is adapted for anatomy, shoulders, limbs, boots, robes and accessories. New literal control patches define hair, collar, robe facings, harness and staff. `inherited/` retains the starting records. `author_ember.py` and `refine_ember.py` replay the exact adaptation; this package does not claim every vertex was built from scratch.

Canonical humanoid_game_v2 bone names, rest matrices and sockets remain unchanged. The body owns nine existing actions. Source validation checks geometry, not likeness. Runtime review must inspect actual GLBs before promotion.
