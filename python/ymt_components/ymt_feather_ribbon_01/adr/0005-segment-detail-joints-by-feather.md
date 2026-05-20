# ADR-0005: Segment Detail Joint Position Order By Feather

Status: Proposed
Date: 2026-05-20
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_feather_ribbon_01` creates detail controls from `DetailSpec` entries keyed by `row/section/col`. The control FK hierarchy follows each feather from root to tip, but `jnt_pos` is consumed differently by mGear Shifter.

In mGear 5.3.2, list-form `jnt_pos` entries are consumed sequentially. Entries without a third parent key do not reset `active_jnt`; after each joint is created, that joint becomes the next active parent. Appending every detail control as `[ctl, detail_name]` therefore creates one continuous joint chain across all detail controls.

## Decision

Detail joint positions will be accumulated after all detail controls exist, grouped by `(row, section)` and sorted by `col` within each group.

The first entry in each `(row, section)` segment will use `"parent_relative_jnt"` as the third `jnt_pos` value so mGear resets the active joint parent to the connector-resolved parent joint at the start of that segment. Remaining entries in the same segment will omit the third value and continue from the previous joint in that segment.

## Considered Options

1. Append detail joints while creating detail controls
   - Pros: simple and local.
   - Cons: creates one continuous joint chain because mGear preserves `active_jnt` between entries.
2. Add `None` as the third value on segment starts
   - Pros: appears explicit.
   - Cons: mGear passes `None` through to `addJoint`, which does not reset `active_jnt`.
3. Group by `(row, section)` and reset segment starts to `"parent_relative_jnt"`
   - Pros: matches mGear's `jnt_pos` consumption, keeps each feather detail segment separate, and attaches segment roots to the connector-resolved parent joint.
   - Cons: detail joint order is now a separate pass from detail control creation and requires the connector parent joint to resolve.

## Consequences

Detail joints no longer form one chain across every detail control. Each row/section feather segment starts under the connector-resolved parent joint and then continues in column order.

Maya runtime validation is still required to confirm the generated hierarchy in a full Shifter build.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- mGear changes list-form `jnt_pos` consumption or active joint handling.
- detail joint segments need to cross row or section boundaries, or use a different root than the connector-resolved parent joint.
