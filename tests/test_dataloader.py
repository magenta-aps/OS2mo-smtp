# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastramqpi.context import Context

from mo_smtp.dataloaders import DataLoader


@pytest.fixture
async def graphql_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def dataloader(graphql_session: AsyncMock) -> DataLoader:
    context = Context({"user_context": {"gql_client": graphql_session}})
    return DataLoader(context)


@pytest.fixture
async def graphql_session_execute() -> AsyncGenerator:
    """
    Mocks a qraphql query execution
    """

    yield {
        "employees": [{"objects": [{"name": "Jack"}]}],
        "org_units": [{"objects": [{"name": "Jack's organisation"}]}],
        "addresses": [
            {"current": {"name": "jack@place.net", "address_type": {"scope": "EMAIL"}}}
        ],
    }


async def test_load_mo_user_data(
    dataloader: DataLoader, graphql_session_execute: dict
) -> None:

    uuid = uuid4()

    dataloader.gql_client.execute.return_value = graphql_session_execute

    result = await dataloader.load_mo_user_data(uuid)
    assert graphql_session_execute["employees"][0]["objects"][0] == result


async def test_load_mo_org_unit_data(
    dataloader: DataLoader, graphql_session_execute: dict
) -> None:

    uuid = uuid4()

    dataloader.gql_client.execute.return_value = graphql_session_execute

    result = await dataloader.load_mo_org_unit_data(uuid)
    assert graphql_session_execute["org_units"][0]["objects"][0] == result


async def test_load_mo_address_data(
    dataloader: DataLoader, graphql_session_execute: dict
) -> None:

    uuid = uuid4()

    dataloader.gql_client.execute.return_value = graphql_session_execute

    result = await dataloader.load_mo_address_data(uuid)
    assert graphql_session_execute["addresses"][0]["current"] == result


async def test_load_mo_manager_data(dataloader: DataLoader):
    manager_dict = {
        "employee_uuid": uuid4(),
        "org_unit_uuid": uuid4(),
        "validity": {"to": "2020-01-01T00:00+02:00"},
    }
    manager_response = {"managers": [{"objects": [manager_dict]}]}
    dataloader.gql_client.execute.return_value = manager_response

    result = await dataloader.load_mo_manager_data(uuid4())
    assert result == manager_dict


async def test_load_mo_root_org_uuid(dataloader: DataLoader):
    root_org_uuid = uuid4()
    root_org_response = {"org": {"uuid": root_org_uuid}}
    dataloader.gql_client.execute.return_value = root_org_response

    result = await dataloader.load_mo_root_org_uuid()
    assert result == root_org_uuid


async def test_get_org_unit_location(dataloader: DataLoader):
    root_org_uuid = str(uuid4())
    dataloader.load_mo_root_org_uuid = AsyncMock()  # type: ignore
    dataloader.load_mo_root_org_uuid.return_value = root_org_uuid

    root_org = {"uuid": root_org_uuid}

    org_unit_1 = {
        "parent_uuid": root_org_uuid,
        "name": "org1",
        "uuid": str(uuid4()),
    }
    org_unit_2 = {
        "parent_uuid": org_unit_1["uuid"],
        "name": "org2",
        "uuid": str(uuid4()),
    }

    org_unit_dict = {
        root_org["uuid"]: root_org,
        org_unit_1["uuid"]: org_unit_1,
        org_unit_2["uuid"]: org_unit_2,
    }

    async def load_org_unit_data(uuid):
        return org_unit_dict[uuid]

    dataloader.load_mo_org_unit_data = AsyncMock()  # type: ignore
    dataloader.load_mo_org_unit_data.side_effect = load_org_unit_data

    assert await dataloader.get_org_unit_location(org_unit_1) == "org1"
    assert await dataloader.get_org_unit_location(org_unit_2) == "org1 / org2"
