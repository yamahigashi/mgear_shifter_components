# ymt_birdwing_3jnt_01

Three-section wing component for bird and dragon style rigs.

The component provides:

- FK controls for root, elbow, and wrist/hand sections.
- IK A: a root to wrist 2-bone IK with up-vector, roll, soft IK, and stretch.
- IK B: a wrist to hand IK target parented under the main IK control, with hand roll.
- FK/IK blending with match references for FK, wrist IK, hand IK, and up-vector.
- Separate deformation anchors and in-span division drivers, following the structure used in `ymt_leg_4jnt_01`.
