from app.schema.city import CityData
from app.schema.friendshipsRequest import IncomingFriendshipRequestOut
from app.schema.our_base_model import PaginatedResponse
from app.schema.user_search import UserSearchResult


class UserSearchOut(PaginatedResponse):
    users: list[UserSearchResult] = []


class IncomingFriendshipRequestsOut(PaginatedResponse):
    requests: list[IncomingFriendshipRequestOut] = []


class CitiesOut(PaginatedResponse):
    cities: list[CityData] = []

