# -*- coding: utf-8 -*-
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest
from fastramqpi.context import Context
from ramqp.mo.models import MORoutingKey
from ramqp.mo.models import PayloadType
from structlog.testing import capture_logs

from mo_smtp.agents import Agents

agents = Agents()


@pytest.fixture
def gql_client() -> Iterator[AsyncMock]:
    yield AsyncMock()


@pytest.fixture
def context(
    gql_client: AsyncMock,
) -> Context:
    context = Context(
        {
            "user_context": {
                "gql_client": gql_client,
            },
        }
    )

    return context


async def test_inform_manager_on_employee_address_creation_no_engagements(
    context: dict[str, Any],
) -> None:
    """
    Test that agents.inform_manager_on_employee_address_creation method performs
    correctly
    """

    uuid_employee = uuid4()
    uuid_address = uuid4()
    employee_address = {"name": "employee@test", "address_type": {"scope": "EMAIL"}}

    employee = {
        "name": "Test McTesterson",
        "uuid": str(uuid_employee),
        "addresses": [
            {
                "value": "employee@test",
                "address_type": {
                    "scope": "EMAIL",
                },
            },
        ],
        "engagements": [],
    }

    async def load_mo_user(uuid: UUID, mo_users: Any) -> Any:
        """Mocks a graphql search for employees"""
        return employee

    async def load_mo_address(uuid: UUID, graphql_client: Any) -> dict[str, Any]:
        """Mocks a graphql search for email address"""
        return employee_address

    usermock = AsyncMock(side_effect=load_mo_user)
    addressmock = AsyncMock(side_effect=load_mo_address)
    payload = PayloadType(
        uuid=uuid_employee, object_uuid=uuid_address, time=datetime.now()
    )

    with patch("mo_smtp.agents.load_mo_user_data", usermock), patch(
        "mo_smtp.agents.send_email", MagicMock
    ), patch("mo_smtp.agents.load_mo_address_data", addressmock):
        mo_routing_key = MORoutingKey.build("employee.address.create")
        await agents.inform_manager_on_employee_address_creation(
            context, payload, mo_routing_key=mo_routing_key
        )

        usermock.assert_any_await(uuid_employee, context["user_context"]["gql_client"])
        addressmock.assert_awaited_with(
            uuid_address, context["user_context"]["gql_client"]
        )


async def test_inform_manager_on_employee_address_creation_multiple_engagements(
    context: dict[str, Any],
) -> None:
    """
    Test that agents.inform_manager_on_employee_address_creation method performs
    correctly
    """

    uuid_employee = uuid4()
    uuid_ou1 = uuid4()
    uuid_ou2 = uuid4()
    uuid_manager = uuid4()
    employee_address = {"name": "employee@test", "address_type": {"scope": "EMAIL"}}

    employee = {
        "name": "Test McTesterson",
        "uuid": str(uuid_employee),
        "addresses": [
            {
                "value": "employee@test",
                "address_type": {
                    "scope": "EMAIL",
                },
            },
        ],
        "engagements": [
            {
                "name": "ou1",
                "org_unit_uuid": uuid_ou1,
            },
            {
                "name": "ou2",
                "org_unit_uuid": uuid_ou2,
            },
        ],
    }
    manager = {
        "name": "Manny O'ager",
        "uuid": str(uuid_manager),
        "addresses": [
            {
                "value": "manager@test",
                "address_type": {
                    "scope": "EMAIL",
                },
            },
        ],
    }
    ou1 = {
        "name": "ou1",
        "uuid": str(uuid_ou1),
        "managers": [
            {
                "employee_uuid": uuid_manager,
                "name": "Manny O'ager",
            },
        ],
    }
    ou2 = {
        "name": "ou2",
        "uuid": str(uuid_ou2),
        "managers": [],
    }

    async def load_mo_user(uuid: UUID, mo_users: Any) -> Any:
        """Mocks a graphql search for employees"""
        if uuid == uuid_employee:
            return employee
        elif uuid == uuid_manager:
            return manager

    async def load_mo_address(uuid: UUID, graphql_client: Any) -> dict[str, Any]:
        """Mocks a graphql search for email address"""
        return employee_address

    usermock = AsyncMock(side_effect=load_mo_user)
    addressmock = AsyncMock(side_effect=load_mo_address)
    org_unit_mock = AsyncMock(side_effect=[ou1, ou2])
    payload = PayloadType(uuid=uuid_employee, object_uuid=uuid4(), time=datetime.now())

    with patch("mo_smtp.agents.load_mo_user_data", usermock), patch(
        "mo_smtp.agents.load_mo_org_unit_data", org_unit_mock
    ), patch("mo_smtp.agents.send_email", MagicMock), patch(
        "mo_smtp.agents.load_mo_address_data", addressmock
    ):
        mo_routing_key = MORoutingKey.build("employee.address.create")
        await agents.inform_manager_on_employee_address_creation(
            context, payload, mo_routing_key=mo_routing_key
        )

        usermock.assert_any_await(uuid_employee, context["user_context"]["gql_client"])
        usermock.assert_awaited_with(
            uuid_manager, context["user_context"]["gql_client"]
        )
        org_unit_mock.assert_any_await(uuid_ou1, context["user_context"]["gql_client"])
        org_unit_mock.assert_any_await(uuid_ou2, context["user_context"]["gql_client"])


async def test_inform_manager_on_employee_address_creation_not_email(
    context: dict[str, Any],
) -> None:
    """
    Tests that agents.inform_manager_on_employee_address_creation rejects amqp
    messages regarding addresses, that are not emails
    """

    uuid_address = uuid4()
    employee_address = {
        "name": "Arbitrary home address",
        "address_type": {"scope": "DAR"},
    }

    async def load_mo_address(uuid: UUID, graphql_client: Any) -> Any:
        """Mocks a graphql search for addresses"""
        return employee_address

    addressmock = AsyncMock(side_effect=load_mo_address)
    usermock = AsyncMock()
    payload = PayloadType(uuid=uuid4(), object_uuid=uuid_address, time=datetime.now())

    with patch("mo_smtp.agents.load_mo_user_data", usermock), patch(
        "mo_smtp.agents.load_mo_address_data", addressmock
    ):
        mo_routing_key = MORoutingKey.build("employee.address.create")
        await agents.inform_manager_on_employee_address_creation(
            context, payload, mo_routing_key=mo_routing_key
        )

        addressmock.assert_awaited_once_with(
            uuid_address, context["user_context"]["gql_client"]
        )
        usermock.assert_not_awaited()


async def test_inform_manager_on_employee_address_creation_object_uuid_is_message_uuid(
    context: dict[str, Any],
) -> None:
    """
    Tests that agents.inform_manager_on_employee_address_creation rejects messages where
    payload.uuid==payload.object_uuid, since that would refer to the creation of the
    employee
    """

    uuid_employee = uuid4()

    addressmock = AsyncMock()
    usermock = AsyncMock()
    payload = PayloadType(
        uuid=uuid_employee, object_uuid=uuid_employee, time=datetime.now()
    )

    with patch("mo_smtp.agents.load_mo_user_data", usermock), patch(
        "mo_smtp.agents.load_mo_address_data", addressmock
    ):
        mo_routing_key = MORoutingKey.build("employee.address.create")
        await agents.inform_manager_on_employee_address_creation(
            context, payload, mo_routing_key=mo_routing_key
        )

        usermock.assert_not_awaited()
        addressmock.assert_not_awaited()


async def test_inform_manager_on_employee_address_creation_invalid_user_email(
    context: dict[str, Any],
) -> None:
    """
    Tests that agents.inform_manager_on_employee_address_creation rejects messages with
    invalid emails
    """

    for invalid_email in ["", "   ", "invalidemail"]:

        uuid_employee = uuid4()
        uuid_address = uuid4()
        employee_address = {"name": invalid_email, "address_type": {"scope": "EMAIL"}}
        employee = {
            "name": "Test McTesterson",
            "uuid": str(uuid_employee),
            "addresses": [
                {
                    "value": invalid_email,
                    "address_type": {
                        "scope": "EMAIL",
                    },
                },
            ],
        }

        async def load_mo_user(uuid: UUID, graphql_client: Any) -> Any:
            """Mocks a graphql search for employees"""
            return employee

        async def load_mo_address(uuid: UUID, graphql_client: Any) -> Any:
            """Mocks a graphql search for addresses"""
            return employee_address

        addressmock = AsyncMock(side_effect=load_mo_address)
        usermock = AsyncMock(side_effect=load_mo_user)
        payload = PayloadType(
            uuid=uuid_employee, object_uuid=uuid_address, time=datetime.now()
        )

        with patch("mo_smtp.agents.load_mo_user_data", usermock), patch(
            "mo_smtp.agents.load_mo_address_data", addressmock
        ):
            mo_routing_key = MORoutingKey.build("employee.address.create")
            await agents.inform_manager_on_employee_address_creation(
                context, payload, mo_routing_key=mo_routing_key
            )

            usermock.assert_awaited_once_with(
                uuid_employee, context["user_context"]["gql_client"]
            )
            addressmock.assert_awaited_once_with(
                uuid_address, context["user_context"]["gql_client"]
            )


async def test_inform_manager_on_employee_address_creation_multiple_email_addresses(
    context: dict[str, Any],
) -> None:
    """
    Tests that agents.inform_manager_on_employee_address_creation rejects messages
    where there already exists an email address
    """

    uuid_employee = uuid4()
    uuid_address = uuid4()
    employee_address = {"name": "new@email", "address_type": {"scope": "EMAIL"}}
    employee = {
        "name": "Test McTesterson",
        "uuid": str(uuid_employee),
        "addresses": [
            {"value": "old@email", "address_type": {"scope": "EMAIL"}},
            {"value": "new@email", "address_type": {"scope": "EMAIL"}},
        ],
    }

    async def load_mo_user(uuid: UUID, graphql_client: Any) -> Any:
        """Mocks a graphql search for employees"""
        return employee

    async def load_mo_address(uuid: UUID, graphql_client: Any) -> Any:
        """Mocks a graphql search for addresses"""
        return employee_address

    addressmock = AsyncMock(side_effect=load_mo_address)
    usermock = AsyncMock(side_effect=load_mo_user)
    payload = PayloadType(
        uuid=uuid_employee, object_uuid=uuid_address, time=datetime.now()
    )
    mo_routing_key = MORoutingKey.build("employee.address.create")

    with patch("mo_smtp.agents.load_mo_user_data", usermock), patch(
        "mo_smtp.agents.load_mo_address_data", addressmock
    ):
        await agents.inform_manager_on_employee_address_creation(
            context, payload, mo_routing_key=mo_routing_key
        )

        usermock.assert_awaited_once_with(
            uuid_employee, context["user_context"]["gql_client"]
        )
        addressmock.assert_awaited_once_with(
            uuid_address, context["user_context"]["gql_client"]
        )


async def test_listen_to_address_wrong_routing_key(
    context: dict[str, Any],
) -> None:
    """
    Tests that agents.inform_manager_on_employee_address_creation rejects amqp messages
    when routing key is not address.address.create
    """

    with capture_logs() as cap_logs:
        mo_routing_key = MORoutingKey.build("org_unit.org_unit.edit")
        payload = PayloadType(uuid=uuid4(), object_uuid=uuid4(), time=datetime.now())
        context = {}
        await agents.inform_manager_on_employee_address_creation(
            context, payload, mo_routing_key=mo_routing_key
        )

        messages = [w for w in cap_logs if w["log_level"] == "info"]
        assert "Only listening to 'employee.address.create'" in str(messages)
