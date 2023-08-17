import datetime
from typing import Any
from typing import Union
from uuid import UUID


def mo_datestring_to_utc(datestring: Union[datetime.datetime, None]):
    """
    Returns datetime object at UTC+0

    Notes
    ------
    Mo datestrings are formatted like this: "2023-02-27T00:00:00+01:00"
    This function essentially removes the "+01:00" part, which gives a UTC+0 timestamp.
    """
    if datestring:
        return datestring.replace(tzinfo=None)
    else:
        return None


class DataLoader:
    def __init__(self, mo):
        self.mo = mo

    @staticmethod
    def extract_current_or_latest_object(objects: list[Any]):
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
                valid_to = mo_datestring_to_utc(obj.validity.to)  # type: ignore
                valid_from = mo_datestring_to_utc(obj.validity.from_)  # type: ignore

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
                            latest_object.validity.to
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
        result = await self.mo.get_manager_data(uuid)
        return self.extract_current_or_latest_object(result.objects[0].objects).dict()

    async def load_mo_user_data(self, uuid: UUID) -> Any:
        """
        Loads a user's data

        Args:
            uuids: List of user UUIDs to query
            graphql_session: The GraphQL session to run queries on

        Return:
            Dictionary with queried user data
        """
        result = await self.mo.get_user_data(uuid)
        return result.objects[0].objects[0].dict()

    async def load_mo_root_org_uuid(self):
        result = await self.mo.get_root_org()
        return result.uuid

    async def load_mo_org_unit_data(self, uuid: UUID) -> Any:
        """
        Loads a user's data

        Args:
            key: User UUID
            graphql_session: The GraphQL session to run queries on

        Return:
            Dictionary with queried org unit data
        """
        result = await self.mo.get_org_unit_data(uuid)
        return result.objects[0].objects[0].dict()

    async def load_mo_address_data(self, uuid: UUID) -> Any:
        """
        Loads information concerning an employee's address

        Args:
            key: User UUID
            graphql_session: The GraphQL session to run queries on

        Return:
            Dictionary with queried address data
        """
        result = await self.mo.get_address_data(uuid)
        if result.objects:
            return result.objects[0].current.dict()
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
