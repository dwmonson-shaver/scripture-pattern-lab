# Implementation Checklist

> Use this checklist for each implementation phase. Do not proceed to the next phase until all items are checked.

## Before Writing Code
- [ ] Design discussion artifact exists and has been reviewed
- [ ] Structure outline exists and has been reviewed
- [ ] Current phase is clearly defined with a test checkpoint
- [ ] I know which files I'm touching and what patterns to follow

## During Implementation
- [ ] Following patterns identified in the design discussion
- [ ] Avoiding anti-patterns identified in the design discussion
- [ ] Type hints on all function signatures
- [ ] Pydantic models for all boundary-crossing data
- [ ] Building vertically (this phase is testable on its own)

## After Each Phase
- [ ] Tests written and passing for this phase
- [ ] I have read every line of code generated in this phase
- [ ] Code committed with a descriptive message
- [ ] No divergence from the structure outline (or outline updated if intentional)
- [ ] Ran /commit for this phase
- [ ] Ran /review (or noted "no decisions" for mechanical changes)

## Before Marking Feature Complete
- [ ] All phases implemented and tested
- [ ] Full test suite passes
- [ ] Design discussion updated with any decisions that changed during implementation
- [ ] CHANGELOG updated
