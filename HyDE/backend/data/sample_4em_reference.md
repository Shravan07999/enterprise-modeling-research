# 4EM (For Enterprise Modeling) — Synthetic Metamodel Reference

## 1. Overview of 4EM Sub-Models
The 4EM methodology structures enterprise knowledge across six interrelated sub-models:

1. **Goals Model (GM)**:
   - Captures the enterprise rationale, strategy, and intentions.
   - Core Concepts: `Goal`, `Sub-Goal`, `Constraint`, `Problem`, `Opportunity`, `Key Performance Indicator (KPI)`.
   - Core Relationships: `supports`, `hinders`, `refines`, `measured_by`.

2. **Business Process Model (BPM)**:
   - Describes enterprise operational workflows and activities designed to achieve goals.
   - Core Concepts: `Process`, `Sub-Process`, `Activity`, `Event`, `Condition`.
   - Core Relationships: `triggers`, `precedes`, `produces`, `satisfies_goal`.

3. **Concepts Model (CM)**:
   - Defines the structural information and ontological business entities.
   - Core Concepts: `Business Object`, `Attribute`, `Class`, `State`.
   - Core Relationships: `is_a`, `part_of`, `associated_with`.

4. **Actors and Resources Model (ARM)**:
   - Captures human roles, organizational units, and physical/financial assets.
   - Core Concepts: `Actor`, `Role`, `Organizational Unit`, `Resource`.
   - Core Relationships: `performs`, `responsible_for`, `allocates`.

5. **Technical Components and Requirements Model (TCRM)**:
   - Specifies technical IT systems and infrastructure supporting processes.
   - Core Concepts: `System`, `Application`, `Software Component`, `Database`, `Hardware`.
   - Core Relationships: `implements`, `hosts`, `interfaces_with`.

---

## 2. Modeling Rules and Syntactic Validation
- Every `Sub-Goal` must link via a `supports` relation to a parent `Goal`.
- Every `Activity` in the Process Model should be mapped to at least one `Actor` or `Role` that performs it.
- Operational processes must contribute to the fulfillment of at least one enterprise `Goal`.
- Data consumed or produced by an `Activity` must correspond to defined `Business Objects` in the Concepts Model.
