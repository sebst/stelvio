from dataclasses import dataclass
from typing import Literal, Unpack, final

import pulumi
from pulumi import Input, Output, ResourceOptions, StringAsset


from pulumi_cloudflare import Record as CloudflareRecord

from stelvio.component import Component


@dataclass(frozen=True)
class RecordResources:
    record: CloudflareRecord


@final
class Record(Component[RecordResources]):
    def __init__(self, name: str = "default", zone_id: Input[str] | None = None, type: Literal["A", "AAAA", "CNAME", "TXT"] = "A", domain: str = "example.com", proxied: bool = False, content: str = "192.0.2.1", **kwargs):
        super().__init__(name)
        # self.name = name
        self.zone_id = zone_id
        self.type = type
        self.domain = domain
        self.content = content
        self.proxied = proxied
        self.kwargs = kwargs

    def _create_resources(self) -> None:
        from pulumi_cloudflare import Record as CloudflareRecord

        record = CloudflareRecord(self.name,
            zone_id=self.zone_id,
            name=self.domain,
            content=self.content,
            type=self.type,
            proxied=self.proxied,
            ttl=30,
        )

        return record
