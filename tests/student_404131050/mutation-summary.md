# Mutation Testing Summary

## Tool

Mutmut was executed on Ubuntu through GitHub Actions because native
execution was not available in the Windows development environment.

## Mutation target

`openunderstand/analysis_passes/Throws_ThrowsBy.py`

## Initial result

- Total mutants: 247
- Killed mutants: 221
- Survived mutants: 26
- Mutation score: 89.47%

## Test improvements

The surviving mutants revealed weaknesses in the following areas:

- Multi-level parent-context traversal
- Passing the original parser context to helper functions
- Validation of reference dictionary keys
- Distinguishing scope names from parent names
- Multi-digit source-column extraction
- Callback interaction contracts for methods, constructors, and interface methods

Manual tests were strengthened to verify these behavioral contracts.

## Final result

- Total mutants: 247
- Killed mutants: 247
- Survived mutants: 0
- Mutation score: 100%

The strengthened test suite killed all previously surviving mutants.