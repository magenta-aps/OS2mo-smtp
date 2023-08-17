import datetime
from typing import Any
from typing import Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from fastramqpi.context import Context
from gql import gql


def mo_datestring_to_utc(datestring: Union[str, None]):
    """
    Returns datetime object at UTC+0

    Notes
    ------
    Mo datestrings are formatted like this: "2023-02-27T00:00:00+01:00"
    This function essentially removes the "+01:00" part, which gives a UTC+0 timestamp.
    """
    if datestring:
        return datetime.datetime.fromisoformat(datestring).replace(tzinfo=None)
    else:
        return None


class DataLoader:
    def __init__(self, context: Context):
        self.gql_client = context["user_context"]["gql_client"]

    @staticmethod
    def extract_current_or_latest_object(objects: list[dict]):
        """
        Check the validity in a list of object dictionaries and return the one which
        is either valid today, or has the latest end-date
        """

        if len(objects) == 1:
            return objects[0]
        elif len(objects) == 0:
            raise Exception("Objects is empty")
        else:
            # If any of the objects is valid today, return it
            latest_object = None
            for obj in objects:
                valid_to = mo_datestring_to_utc(obj["validity"]["to"])
                valid_from = mo_datestring_to_utc(obj["validity"]["from"])

                if valid_to and valid_from:
                    now_utc = datetime.datetime.utcnow()
                    if now_utc > valid_from and now_utc < valid_to:
                        return obj

                elif not valid_to and valid_from:
                    now_utc = datetime.datetime.utcnow()
                    if now_utc > valid_from:
                        return obj

                elif valid_to and not valid_from:
                    now_utc = datetime.datetime.utcnow()
                    if now_utc < valid_to:
                        return obj

                # Update latest object
                if valid_to:
                    if latest_object:
                        latest_valid_to = mo_datestring_to_utc(
                            latest_object["validity"]["to"]
                        )
                        if latest_valid_to and valid_to > latest_valid_to:
                            latest_object = obj
                    else:
                        latest_object = obj
                else:
                    latest_object = obj

            # Otherwise return the latest
            return latest_object

    async def load_mo_manager_data(self, uuid: UUID) -> Any:
        query = gql(
            """
            query getManagerData($uuids: [UUID!]) {
              managers(
                  uuids: $uuids,
                  from_date: null
                  to_date: null
              ) {
                objects {
                  objects {
                    employee_uuid
                    org_unit_uuid
                    validity {
                      to
                      from
                    }
                  }
                }
              }
            }
            """
        )

        variable_values = jsonable_encoder({"uuids": uuid})
        result = await self.gql_client.execute(query, variable_values=variable_values)
        return self.extract_current_or_latest_object(
            result["managers"]["objects"][0]["objects"]
        )

    async def load_mo_user_data(self, uuid: UUID) -> Any:
        """
        Loads a user's data

        Args:
            uuids: List of user UUIDs to query
            graphql_session: The GraphQL session to run queries on

        Return:
            Dictionary with queried user data
        """

        query = gql(
            """
                query getData($uuids: [UUID!]) {
                  employees(uuids: $uuids) {
                    objects {
                      objects {
                        name
                        addresses {
                          value
                          address_type {
                            scope
                          }
                        }
                        engagements {
                          org_unit_uuid
                        }
                      }
                    }
                  }
                }
                """
        )
        variable_values = jsonable_encoder({"uuids": uuid})
        result = await self.gql_client.execute(query, variable_values=variable_values)
        return result["employees"]["objects"][0]["objects"][0]

    async def load_mo_root_org_uuid(self):
        query = gql(
            """
                query getData {
                  org {
                    uuid
                  }
                }
                """
        )
        result = await self.gql_client.execute(query)
        return result["org"]["uuid"]

    async def load_mo_org_unit_data(self, uuid: UUID) -> Any:
        """
        Loads a user's data

        Args:
            key: User UUID
            graphql_session: The GraphQL session to run queries on

        Return:
            Dictionary with queried org unit data
        """
        query = gql(
            """
                query getData($uuids: [UUID!]) {
                  org_units(uuids: $uuids) {
                    objects {
                      objects {
                        name
                        user_key
                        parent_uuid
                        managers {
                          employee_uuid
                        }
                      }
                    }
                  }
                }
                """
        )
        variable_values = jsonable_encoder({"uuids": uuid})
        result = await self.gql_client.execute(query, variable_values=variable_values)
        return result["org_units"]["objects"][0]["objects"][0]

    async def load_mo_address_data(self, uuid: UUID) -> Any:
        """
        Loads information concerning an employee's address

        Args:
            key: User UUID
            graphql_session: The GraphQL session to run queries on

        Return:
            Dictionary with queried address data
        """
        query = gql(
            """
                query getData($uuids: [UUID!]) {
                  addresses(uuids: $uuids) {
                    objects {
                      current {
                        name
                        employee_uuid
                        address_type {
                          scope
                        }
                      }
                    }
                  }
                }
                """
        )
        variable_values = jsonable_encoder({"uuids": uuid})
        result = await self.gql_client.execute(query, variable_values=variable_values)
        if result["addresses"]:
            return result["addresses"]["objects"][0]["current"]
        else:
            return

    async def get_org_unit_location(self, org_unit):
        """
        Constructs and org-unit location string, where different org-units in the
        hierarchy are separated by forward slashes.
        """
        root_org_uuid = await self.load_mo_root_org_uuid()
        org_unit_location = org_unit["name"]
        parent_uuid = org_unit["parent_uuid"]

        # do not include the root-org unit in the location string
        while parent_uuid != root_org_uuid:
            parent = await self.load_mo_org_unit_data(parent_uuid)
            parent_uuid = parent["parent_uuid"]
            org_unit_location = parent["name"] + " / " + org_unit_location

        return org_unit_location
