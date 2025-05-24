import json
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cache
from hashlib import sha256
from typing import Literal, Unpack, final

import pulumi
from pulumi import Input, Output, ResourceOptions, StringAsset


from pulumi_cloudflare import WorkersScript

from stelvio.component import Component



@dataclass(frozen=True)
class WorkerResources:
    worker_script: WorkersScript


@final
class Worker(Component[WorkerResources]):
    def __init__(self, name: str, file):
        self._file = file
        super().__init__(name)
    
    def _create_resources(self) -> WorkerResources:
        worker_script = WorkersScript(
            name=self.name,
            script=self._file,
        )
        return WorkerResources(worker_script=worker_script)
