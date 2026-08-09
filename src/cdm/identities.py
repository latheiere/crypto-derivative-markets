"""Exact, order-independent native-identity selection."""

from __future__ import annotations

from typing import Sequence

from .errors import ValidationError
from .models import (
    NativeIdentitySelectionStatus,
    NativeIdentitySelectionV1,
    NativeIdentitySelectorV1,
    NativeIdentityV1,
)


def select_native_identity(
    identities: Sequence[NativeIdentityV1],
    selector: NativeIdentitySelectorV1,
) -> NativeIdentitySelectionV1:
    """Select by exact role and namespace without resolving aliases by order."""

    if not isinstance(identities, Sequence) or isinstance(identities, (str, bytes, bytearray)):
        raise ValidationError(
            "invalid_type",
            "$.identities",
            "expected a sequence of NativeIdentityV1",
        )
    if not isinstance(selector, NativeIdentitySelectorV1):
        raise ValidationError(
            "invalid_type",
            "$.selector",
            "expected NativeIdentitySelectorV1",
        )
    candidates = []
    for index, identity in enumerate(identities):
        if not isinstance(identity, NativeIdentityV1):
            raise ValidationError(
                "invalid_type",
                f"$.identities[{index}]",
                "expected NativeIdentityV1",
            )
        if selector.matches(identity):
            candidates.append(identity)
    status = (
        NativeIdentitySelectionStatus.MISSING
        if not candidates
        else NativeIdentitySelectionStatus.UNIQUE
        if len(candidates) == 1
        else NativeIdentitySelectionStatus.AMBIGUOUS
    )
    return NativeIdentitySelectionV1(
        selector=selector,
        status=status,
        candidates=tuple(candidates),
    )
