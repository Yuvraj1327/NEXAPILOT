"""Aggregates every v1 endpoint router under a single APIRouter."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    activity,
    ai,
    auth,
    blockchain,
    health,
    policies,
    policy,
    risk,
    transactions,
    users,
    wallets,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(wallets.router)
api_router.include_router(policies.router)
api_router.include_router(transactions.router)
api_router.include_router(activity.router)
api_router.include_router(blockchain.router)
api_router.include_router(ai.router)
api_router.include_router(risk.router)
api_router.include_router(policy.router)
