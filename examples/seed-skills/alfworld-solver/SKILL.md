---
type: task_skill
task_name: ALFWorld embodied household agent
description: Complete household tasks in the ALFWorld text-based embodied environment (pick and place, heat/cool/clean then place, examine under lamp, pick two and place) through task decomposition, systematic exploration, and state transformation, choosing actions under the admissible action constraint
current_version: v0
parent_version: null
repair_brief: null
evolution_note: "Seed version, ported from the reference implementation and adapted to this framework format"
---

# Task Skill: ALFWorld Embodied Household Agent

## 1. Task Overview

This skill guides the agent in the ALFWorld text-based embodied environment. The agent completes household tasks by navigating rooms, interacting with objects, and using appliances. Each step provides the current observation and an **admissible action list**, and actions must be chosen from that list.

**Output format**: at each step, first output `<think>...</think>` for reasoning, then output `<action>...</action>` with the chosen action. The action text must **exactly match** one item in the admissible action list.

---

## 2. Task Types

| Type | Goal | Key steps |
|------|------|-----------|
| Pick & Place | Put object X on container/surface Y | Find X, take X, go to Y, put X on Y |
| Pick Two & Place | Put two X on Y | Find X1, take, put, find X2, take, put |
| Examine in Light | Examine object X under a desk lamp | Find X, take X, find the lamp, use the lamp |
| Clean & Place | Clean X then put it on Y | Find X, take X, go to sink, clean X, go to Y, put X |
| Heat & Place | Heat X then put it on Y | Find X, take X, go to microwave, heat X, go to Y, put X |
| Cool & Place | Cool X then put it on Y | Find X, take X, go to fridge, cool X, go to Y, put X |

---

## 3. General Principles

1. **Task decomposition**: split the goal into ordered subgoals (locate, acquire, transform, deliver) and finish each before moving on.
2. **Systematic exploration**: check each surface and container once before moving to a new location. Open closed containers (drawers, cabinets, fridge) before concluding they are empty.
3. **Take immediately**: when the needed object is visible and reachable, take it right away instead of going elsewhere first.
4. **Transform before delivering**: if the task requires clean/heat/cool, finish the state transformation at the corresponding appliance first, then head to the final destination.
5. **Deliver directly**: once holding the (transformed or transformation-free) target object, navigate straight to the target container and place it.
6. **Track progress**: keep a mental count of how many objects remain to find and place. Stop searching only when the count reaches zero.
7. **Avoid loops**: do not repeat the same action more than twice in a row. If stuck, move to an unexplored location.
8. **Admissible actions only**: always pick from the admissible action list and never invent actions.

---

## 4. Common Mistakes (Must Avoid)

- **Re-searching checked locations**: record which surfaces/containers have been checked and do not examine them again.
- **Ignoring visible objects**: if the target object appears in the observation, take it immediately.
- **Skipping state transformation**: when clean/heat/cool is required, never deliver the object untransformed.
- **Stopping early**: do not end the episode before all goal conditions are confirmed satisfied.
- **Action loops**: repeatedly opening/closing or examining the same object wastes steps. Move to a new location instead.
