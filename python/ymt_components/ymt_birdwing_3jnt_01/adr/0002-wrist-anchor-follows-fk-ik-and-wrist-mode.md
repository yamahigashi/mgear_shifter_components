# ADR-0002: Wrist Anchor Follows FK/IK and Wrist Control Mode

Status: Proposed
Date: 2026-05-19
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`wrist_jnt_ref` is the deformation anchor for the wrist guide point. The component also uses `wingBones[2]` as the parent basis for the wrist/hand section. When `wingBones[2]` is driven from `handChain[0]` in IK, the wrist deformation anchor can inherit the hand solve basis instead of the wrist control mode basis.

`wristControlMode` already defines how the hand IK target switches between the IK control basis and the solved chain basis. The wrist deformation anchor and the IK wrist result orientation should follow the same policy while still honoring the component FK/IK blend.

## Decision

The wrist deformation anchor will no longer be constrained directly to `wingBones[2]`. It will be driven by a dedicated anchor stack:

- `wristModeBasis_ref` switches between `hand_ik_parent_ik_ref` and `hand_ik_parent_chain_ref` using `wristControlMode`.
- `wristAnchorFk_ref` follows `wingBonesFK[2]`.
- `wristAnchorIkMode_ref` follows `wristModeBasis_ref`.
- `wrist_jnt_ref` blends between `wristAnchorFk_ref` and `wristAnchorIkMode_ref` using the FK/IK `blend` attribute.

The IK result wrist, `wingBonesIK[2]`, uses the hand IK solve only for position. Its orientation follows `wristModeBasis_ref`, so the FK/IK result `wingBones[2]` no longer receives the wrist-hand IK solve rotation as its wrist basis.

## Considered Options

1. Keep `wrist_jnt_ref` constrained to `wingBones[2]`
   - Pros: simplest node graph.
   - Cons: lets hand solve orientation leak into the wrist anchor and ignores `wristControlMode`.
2. Drive `wrist_jnt_ref` only from `wristControlMode`
   - Pros: fixes IK mode behavior.
   - Cons: ignores FK/IK blend and gives wrong FK wrist anchors during blends.
3. Use a dedicated FK/IK and wrist-mode anchor stack
   - Pros: separates wrist deformation ownership from hand solve basis and follows both relevant controls.
   - Cons: adds a small number of hidden reference nodes and constraints.
4. Use a shared wrist mode basis for both the hand IK parent and IK wrist result
   - Pros: makes `wristControlMode` the single owner of the IK wrist orientation while keeping `handChain` as the wrist-hand solve chain.
   - Cons: changes the meaning of `wingBones[2]` in IK mode; Maya runtime validation is required for match and deformation behavior.

## Consequences

The wrist deformation anchor and IK wrist result now have explicit ownership. FK/IK blending controls whether the deformation anchor follows FK or IK, and IK mode uses `wristControlMode` to choose the wrist basis. This reduces hidden coupling between the hand IK solve and deformation joints.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- Maya runtime validation shows FK/IK blended constraints do not match expected wrist deformation interpolation.
- A future component change removes `hand_ik_parent_ik_ref` or `hand_ik_parent_chain_ref`.
- Match references or downstream components require the previous `handChain[0]` solve rotation on `wingBones[2]`.
