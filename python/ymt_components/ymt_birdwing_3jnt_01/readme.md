# ymt_birdwing_3jnt_01

Three-section wing component for bird and dragon style rigs.

The component provides:

- FK controls for root, elbow, and wrist/hand sections.
- Separate guide points for `hand` and `eff`: `hand` is the structural bone/deformation anchor,
  while `eff` is the animator-facing hand IK control position.
- IK A: a root to wrist 2-bone IK with up-vector, roll, soft IK, and stretch.
- Soft IK range and speed initial values can be set from the guide settings.
- The initial up-vector control position is derived from the guide blade and root-to-wrist direction,
  not from a free guide locator.
- IK B: a wrist to hand IK target with hand roll.
- IK rotation control at the wrist rotates the hand IK target around the wrist in both wrist control modes.
- A second hand IK rotation control under the hand IK target owns the final hand bone orientation.
- Wrist Control Mode for the hand IK target: `IK` keeps the legacy main IK rotation parent,
  while `Chain` follows the solved upper/lower wing extension from the up-vector instead.
  Its initial value can be set from the guide settings.
- The hand section has no separate animator-facing up-vector. In `IK` wrist control mode,
  moving the up-vector does not move the hand IK target. In `Chain`
  wrist control mode, the hand IK target inherits the solved wrist basis,
  so they follow the visible up-vector through the root/elbow/wrist IK plane.
- The second hand IK rotation control keeps a stable zero parent under the hand IK target;
  `wristControlMode` does not add another orientation switch on its NPO.
- The wrist deformation anchor is separate from the final hand segment basis. It follows
  FK in FK mode, and in IK mode follows the same `wristControlMode` basis as the hand IK target.
- The IK wrist result uses the wrist/hand IK chain for position, but its orientation follows
  the shared `wristControlMode` basis instead of the `handChain[0]` solve rotation.
- Shoulder Smooth Step affects shoulder connection interpolation when connected to `ymt_shoulder_01`.
- FK/IK blending with match references for FK, wrist IK, hand IK, and up-vector.
- Separate deformation anchors and in-span division drivers, following the structure used in `ymt_leg_4jnt_01`.

Architecture notes: see `adr/0001-hand-upv-follows-wrist-control-mode.md` and
`adr/0002-wrist-anchor-follows-fk-ik-and-wrist-mode.md`.
