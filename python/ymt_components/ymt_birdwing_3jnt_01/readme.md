# ymt_birdwing_3jnt_01

Three-section wing component for bird and dragon style rigs.

The component provides:

- FK controls for root, elbow, and wrist/hand sections.
- IK A: a root to wrist 2-bone IK with up-vector, roll, soft IK, and stretch.
- IK B: a wrist to hand IK target with hand roll.
- Wrist Control Mode for the hand IK target: `IK` keeps the legacy main IK rotation parent,
  while `Chain` follows the solved upper/lower wing extension from the up-vector instead.
- FK/IK blending with match references for FK, wrist IK, hand IK, and up-vector.
- Separate deformation anchors and in-span division drivers, following the structure used in `ymt_leg_4jnt_01`.
