from __future__ import annotations

import factory

from .models import Priority, PriorityIcon, TeamMember


class PriorityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Priority

    icon_key = PriorityIcon.SHIELD
    title = factory.Sequence(lambda n: f"Priority {n}")
    description = ""
    order = factory.Sequence(lambda n: n)
    is_active = True


class TeamMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeamMember

    full_name = factory.Sequence(lambda n: f"Член команди {n}")
    role = factory.Sequence(lambda n: f"Посада {n}")
    bio = ""
    order = factory.Sequence(lambda n: n)
    is_active = True
