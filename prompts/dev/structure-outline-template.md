# Structure Outline: [Feature Name]

> This is the "C header file" for the implementation. It defines WHAT will exist (types, signatures, phases) without writing the full implementation. Each phase must be independently testable. Build vertically, not horizontally.

## Overview
_One paragraph: what this implementation produces and how it's structured._

## New Types / Modified Types

```python
# List new or changed type signatures here — just the shape, not the implementation

class ExampleType:
    field_a: str
    field_b: int
```

## New Functions / Modified Functions

```python
# List new or changed function signatures — just the signature and a one-line docstring

def example_function(input: ExampleType) -> OutputType:
    """One line explaining what this does."""
    ...
```

## Implementation Phases

### Phase 1: [Name] — [What's testable after this phase]
- Files touched: `src/...`
- What happens: _brief description_
- Test checkpoint: _how to verify this phase works before moving on_

### Phase 2: [Name] — [What's testable after this phase]
- Files touched: `src/...`
- What happens: _brief description_
- Test checkpoint: _how to verify_

### Phase 3: [Name] — [What's testable after this phase]
- Files touched: `src/...`
- What happens: _brief description_
- Test checkpoint: _how to verify_

## Dependencies Between Phases
_Which phases must complete before others can start? Are any parallelizable?_

## What This Does NOT Change
_Explicitly list what's out of scope to prevent drift._
