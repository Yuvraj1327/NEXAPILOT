"""
Loads the deployed contract's address and ABI from the `contracts/`
package's generated output — never hand-copied/duplicated into backend
config. See contracts/script/deploy.sh, which writes
contracts/deployments/<network>.json on every deploy.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings
from app.core.exceptions import AppError


class DeploymentNotFoundError(AppError):
    status_code = 503
    code = "CONTRACT_DEPLOYMENT_NOT_FOUND"


@dataclass(frozen=True)
class ContractDeployment:
    network: str
    chain_id: int
    address: str
    abi: List[Dict[str, Any]]


def _deployments_dir() -> Path:
    return settings.contracts_dir / "deployments"


def _abi_path() -> Path:
    return _deployments_dir() / "NexaPilotExecutor.abi.json"


@lru_cache
def get_executor_deployment() -> ContractDeployment:
    """Load the NexaPilotExecutor address + ABI for the configured network.

    Raises DeploymentNotFoundError (a normal, catchable AppError — not a
    crash) if the contracts package hasn't been deployed/built yet, so the
    rest of the API can stay up and report a clear error instead of the
    whole process failing to start.
    """
    network = settings.blockchain_network
    deployment_file = _deployments_dir() / f"{network}.json"
    abi_file = _abi_path()

    if not deployment_file.exists():
        raise DeploymentNotFoundError(
            f"No deployment record for network '{network}' at {deployment_file}. "
            "Run contracts/script/deploy.sh first."
        )
    if not abi_file.exists():
        raise DeploymentNotFoundError(
            f"Contract ABI not found at {abi_file}. Run `forge build` in contracts/ first."
        )

    deployment_data = json.loads(deployment_file.read_text())
    abi = json.loads(abi_file.read_text())

    return ContractDeployment(
        network=network,
        chain_id=deployment_data["chainId"],
        address=deployment_data["address"],
        abi=abi,
    )
