# ADR-0001: Birdtail Guide and Solver Contract

Status: Proposed
Date: 2026-05-26
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_birdtail_01` needs to describe bird tail feathers that can be grouped by feather type, such as long primary feathers and shorter secondary feathers layered above them. These groups are not spatial rows. Each group needs its own detail grid for controls and optional joints.

The component also needs two solver modes. The default solver is `Simple Matrix Connection`, a light matrix/node-driven setup. The second solver is `NURBS Ribbon with Curl`, which provides surface-based placement, surface deformation, and curl behavior. NURBS ribbon mode is allowed to require modern Maya ribbon infrastructure: `uvPin.relativeSpaceMode`, local-space skinning, and the `rotationDriver` plugin. Builds using NURBS ribbon mode must fail clearly on Maya versions that do not support these requirements, including Maya 2023.2 and earlier.

## Decision

The guide schema separates feather grouping from detail grid indices:

- `group` is a feather group such as `primary` or `secondary`.
- `row` is an index inside a group, usually across the tail fan.
- `col` is an index from feather root to feather tip.

Generated detail locator names use `<group>_<row>_<col>_loc`, for example `primary_0_2_loc`. Settings store group names, group row counts, per-group column depths, per-group length/width/stack offsets, and per-group main influence scales. Rebuilding locators deletes existing generated locators and recreates them from these settings.

The component is standalone and creates C/L/R main controls inside the component using temporary naming-side overrides. Main controls are created for each main column up to the maximum group column count and parented as radial FK chains from the tail root toward each C/L/R endpoint. The first main control in each side chain starts at the tail root. Main and detail control initial transforms aim their local X axis along the root-radial feather direction.

Simple Matrix Connection detail controls separate guide placement, main-control translation, and main-control rotation into explicit transform layers:

```text
detail_npo       # guide/grid position and initial radial orientation
  detail_pos_off # blended main local translation only
    detail_rot_off # blended main local rotation only
      detail_ctl
```

Simple Matrix Connection main-control influence is evaluated from local matrices, not world matrices. Each main column exposes a local output matrix in the same evaluation space as the detail offsets. C/L/R main matrices are blended per detail row/column, then decomposed. Each feather group gets an animator-facing `<group>MainInfluence` attribute initialized from the guide's group main influence scale. This attribute scales the decomposed translate and rotate outputs equally after matrix blending; it must not scale `wtAddMatrix` weights directly, because an influence of zero would produce a zero matrix rather than an identity local delta. The scaled translate drives only `detail_pos_off.translate`; the scaled rotate drives only `detail_rot_off.rotate`. Rotation must not be delivered through `parentConstraint` on `detail_npo`, because that mixes rotation with positional orbiting and moves the guide/grid base.

NURBS Ribbon with Curl is a separate solver contract and may use a different detail hierarchy optimized for surface sampling. It should build one NURBS ribbon surface per feather group. Surface U should represent the row/fan direction and surface V should represent the feather root-to-tip column/depth direction. Main C/L/R controls and main columns should drive the ribbon surface through local-space skinning. C/L/R weights are evaluated from the row/fan ratio, and column/depth weights are evaluated from the main column depth. NURBS Ribbon with Curl uses `uvPin` rivets with `relativeSpaceMode` enabled to place detail references on the surface.

NURBS Ribbon with Curl detail controls should follow the surface using a chain/aim/curl structure rather than the Simple Matrix Connection pos/rot split:

```text
detail_rivet_ref     # uvPin-driven surface sample
  detail_aim_ref     # aims toward the next column sample when available

detail_chain_npo     # col 0 follows the rivet position; later cols continue the FK detail chain
  detail_aim_npo     # local offset rotation from the surface/next-column aim
    detail_curl_npo  # weighted curl-control rotation
      detail_ctl
```

NURBS Ribbon with Curl includes animator-facing curl controls. The initial curl control layout should be L/R across the tail fan and shared across groups. The default guide positions place each curl control above the midpoint between `centerEnd` and the matching side endpoint. Center details receive an even L/R curl blend. Curl controls affect the ribbon in two ways:

- Curl translation drives dedicated curl deformation joints that participate in the ribbon surface skinCluster.
- Curl rotation drives `detail_curl_npo.rotate` through `decomposeRotate`/`composeRotate`, weighted per detail by fan position and scaled by column-level curl rotation multipliers.

The surface curl deformation weights should not completely replace main-control weights unless the configured curl strength reaches 1.0. As in the feather ribbon component, the surface skinning should reserve `1.0 - curlStrength` for main/control influences and blend curl influences into the remaining weight. Curl strength should increase toward feather tips and be distributed across L/R curl controls by fan distance, then reduced by a fan envelope so the outer L/R endpoints do not receive full curl influence by default. The guide-level `surfaceCurlEdgeScale` setting controls the minimum edge influence: `0.0` fully applies the fan falloff at the side endpoints, while `1.0` disables the endpoint reduction. Group-level curl influence settings may scale the result per feather group.

Detail controls and joint output keep the same public naming and relation semantics across solver modes, even when the internal hierarchy differs. Joint chains reset per `(group, row)` and continue by `col`.

## Considered Options

1. Treat `primary` and `secondary` as row names
   - Pros: matches the older feather ribbon row table naming.
   - Cons: conflates feather type with detail-grid indices and cannot clearly represent grouped long/short layered feathers.
2. Add a separate segment layer unrelated to row/col
   - Pros: explicit grouping.
   - Cons: adds redundant naming when the group already describes the segment/type.
3. Use `group -> row -> col`
   - Pros: keeps feather type separate from grid indices and maps directly to generated locator names.
   - Cons: requires a new settings schema instead of reusing `rowNames`.
4. Drive detail bases with `parentConstraint` from main controls
   - Pros: simple and exposes both translate and rotate.
   - Cons: main rotation moves detail positions by orbiting the constrained base, so guide/grid placement is no longer stable.
5. Split detail offsets and decompose blended local main matrices
   - Pros: preserves guide/grid bases while allowing main translation and rotation to affect separate offset layers.
   - Cons: requires explicit local matrix outputs and Maya runtime validation of C/L/R matrix blending.
6. Reuse Simple Matrix Connection detail hierarchy for NURBS Ribbon with Curl
   - Pros: reduces code branching and keeps one internal hierarchy.
   - Cons: forces surface sampling into layers designed for local matrix driving, making aim, curl, and uvPin-driven placement harder to reason about.
7. Use a ribbon-specific chain/aim/curl hierarchy
   - Pros: matches NURBS surface sampling, supports per-detail aim stabilization, and cleanly separates surface placement from curl rotation.
   - Cons: requires solver-mode-specific object creation and operator code.
8. Avoid `uvPin.relativeSpaceMode` for old Maya compatibility
   - Pros: could support Maya 2023.2 and earlier.
   - Cons: pushes local-space behavior into custom compatibility code and increases risk under scaled or nested component transforms.
9. Require modern ribbon infrastructure in NURBS Ribbon with Curl
   - Pros: keeps the ribbon solver explicit, local-space, and closer to current Maya behavior.
   - Cons: NURBS Ribbon with Curl is unavailable on Maya 2023.2 and earlier.

## Consequences

Existing feather-ribbon parsing helpers cannot be reused directly because their first locator token is a row name, while birdtail uses it as a group name. The component gets its own `detail_config.py` to keep the guide, settings UI, and runtime aligned.

Simple Matrix Connection detail driver implementation must keep translation and rotation independent. The detail guide transform remains the stable base; main-control translation and rotation are applied as local deltas below that base.

NURBS Ribbon with Curl implementation must keep the surface as the source of placement and aim, with curl applied as an additional local rotation layer. It may use a different hierarchy from Simple Matrix Connection, but it must preserve the same external detail control naming and joint order. NURBS Ribbon with Curl must validate Maya version and required node/plugin availability before building surface operators. It must fail clearly instead of silently falling back to Simple Matrix Connection behavior when `uvPin.relativeSpaceMode`, local-space skinning, or `rotationDriver` support is missing.

Maya runtime validation is required for both solver modes, especially with mirrored or scaled parent transforms.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- tail feather groups need nested subgroups beyond `group -> row -> col`.
- main control columns need non-uniform depths instead of evenly distributed root-to-tip FK positions.
- local matrix blending cannot produce acceptable C/L/R rotation interpolation in Maya and needs a quaternion or custom rotation-driver replacement.
- NURBS Ribbon with Curl needs center or group-specific curl control layouts instead of shared L/R curl controls.
- NURBS Ribbon with Curl needs surface-rivet behavior that changes public control naming or joint order.
