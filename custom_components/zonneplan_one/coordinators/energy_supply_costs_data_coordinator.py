import logging
from datetime import timedelta
from http import HTTPStatus

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Zonneplan reports dates in the Netherlands time zone
_TIME_ZONE = "Europe/Amsterdam"


class EnergySupplyCostsDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Coordinator for today's total energy costs (the "total today" the app shows)."""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    contract: ZonneplanContract
    address_uuid: str

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        address_uuid: str,
        connection_uuid: str,
        contract: ZonneplanContract,
        organization_uuid: str,
        address_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=60, immediate=False),
        )

        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contract = contract
        self.organization_uuid = organization_uuid
        self.address_id = address_id

    async def _async_update_data(self) -> dict:
        """Fetch today's energy supply costs."""
        try:
            today = dt_util.now(dt_util.get_time_zone(_TIME_ZONE)).date()

            costs = await self.api.async_get_energy_supply_costs(
                self.organization_uuid,
                self.address_id,
                today,
                today,
            )

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Energy supply costs data: %s", costs)

            return costs or self.data
