# Generated by ariadne-codegen on 2024-12-02 10:43
# Source: queries.graphql

from typing import List, Optional
from uuid import UUID

from .base_model import BaseModel


class GetUserData(BaseModel):
    employees: "GetUserDataEmployees"


class GetUserDataEmployees(BaseModel):
    objects: List["GetUserDataEmployeesObjects"]


class GetUserDataEmployeesObjects(BaseModel):
    validities: List["GetUserDataEmployeesObjectsValidities"]


class GetUserDataEmployeesObjectsValidities(BaseModel):
    name: str
    addresses: List["GetUserDataEmployeesObjectsValiditiesAddresses"]
    engagements: List["GetUserDataEmployeesObjectsValiditiesEngagements"]


class GetUserDataEmployeesObjectsValiditiesAddresses(BaseModel):
    value: str
    address_type: "GetUserDataEmployeesObjectsValiditiesAddressesAddressType"


class GetUserDataEmployeesObjectsValiditiesAddressesAddressType(BaseModel):
    scope: Optional[str]


class GetUserDataEmployeesObjectsValiditiesEngagements(BaseModel):
    org_unit_uuid: UUID


GetUserData.update_forward_refs()
GetUserDataEmployees.update_forward_refs()
GetUserDataEmployeesObjects.update_forward_refs()
GetUserDataEmployeesObjectsValidities.update_forward_refs()
GetUserDataEmployeesObjectsValiditiesAddresses.update_forward_refs()
GetUserDataEmployeesObjectsValiditiesAddressesAddressType.update_forward_refs()
GetUserDataEmployeesObjectsValiditiesEngagements.update_forward_refs()
