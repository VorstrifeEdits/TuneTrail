"""
Documentation visibility and access control configuration.

This module determines what API documentation is publicly visible
versus requiring authentication based on the edition and environment.
"""

from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel


class DocsVisibility(str, Enum):
    """Documentation visibility levels."""
    PUBLIC = "public"              # Anyone can view
    AUTHENTICATED = "authenticated"  # Requires login
    PREMIUM = "premium"            # Requires paid plan
    ENTERPRISE = "enterprise"      # Enterprise customers only


class Edition(str, Enum):
    """TuneTrail editions."""
    COMMUNITY = "community"
    SAAS = "saas"


class DocsConfig(BaseModel):
    """Configuration for API documentation visibility."""

    # General settings
    enable_swagger: bool = True
    enable_redoc: bool = True
    enable_openapi_json: bool = True

    # Visibility settings
    docs_visibility: DocsVisibility = DocsVisibility.PUBLIC
    require_api_key_for_docs: bool = False

    # What to show/hide
    show_internal_endpoints: bool = False
    show_deprecated_endpoints: bool = True
    show_premium_endpoints: bool = True

    # Customization
    docs_title: str = "TuneTrail API Documentation"
    docs_description: str = "Music recommendation platform API"

    # Tag visibility (which endpoint categories to show)
    visible_tags: Optional[List[str]] = None  # None = all tags
    hidden_tags: List[str] = []

    # Premium/Enterprise feature flags
    premium_tags: List[str] = [
        "Neural CF",
        "Advanced ML",
        "Webhooks",
        "Batch Processing",
    ]
    enterprise_tags: List[str] = [
        "Custom Models",
        "White Label",
        "Admin",
    ]


# Edition-specific configurations
DOCS_CONFIGS: Dict[Edition, DocsConfig] = {
    # Community Edition: Everything public
    Edition.COMMUNITY: DocsConfig(
        docs_visibility=DocsVisibility.PUBLIC,
        require_api_key_for_docs=False,
        show_internal_endpoints=False,
        show_premium_endpoints=True,  # Show but mark as unavailable
        docs_title="TuneTrail Community Edition API",
        docs_description="""
        **Open Source Music Recommendation Platform**

        This is the Community Edition API. All features documented here are
        available in the self-hosted version.

        For advanced features like Neural Collaborative Filtering and Webhooks,
        check out the [SaaS Edition](https://tunetrail.app).
        """,
        hidden_tags=["Admin", "Internal"],
    ),

    # SaaS Edition: Tiered visibility
    Edition.SAAS: DocsConfig(
        docs_visibility=DocsVisibility.AUTHENTICATED,
        require_api_key_for_docs=False,  # Can view without key
        show_internal_endpoints=False,
        show_premium_endpoints=True,
        docs_title="TuneTrail API",
        docs_description="""
        **Professional Music Recommendation Platform**

        Access powerful ML models, real-time analytics, and more.

        Features vary by plan:
        - **Starter**: Basic recommendations, audio processing
        - **Pro**: Neural CF, webhooks, advanced analytics
        - **Enterprise**: Custom models, white-label, dedicated support

        [View Pricing](https://tunetrail.app/pricing)
        """,
        hidden_tags=["Internal"],
    ),
}


def get_docs_config(edition: str) -> DocsConfig:
    """Get documentation configuration for the specified edition."""
    try:
        ed = Edition(edition.lower())
        return DOCS_CONFIGS[ed]
    except (ValueError, KeyError):
        # Default to community config
        return DOCS_CONFIGS[Edition.COMMUNITY]


def filter_openapi_spec(openapi_spec: dict, config: DocsConfig, user_plan: Optional[str] = None) -> dict:
    """
    Filter OpenAPI specification based on configuration and user plan.

    Args:
        openapi_spec: The full OpenAPI specification
        config: Documentation configuration
        user_plan: User's subscription plan (free, starter, pro, enterprise)

    Returns:
        Filtered OpenAPI specification
    """
    filtered_spec = openapi_spec.copy()

    # Filter tags
    if config.visible_tags is not None:
        # Only include specified tags
        filtered_spec["tags"] = [
            tag for tag in filtered_spec.get("tags", [])
            if tag["name"] in config.visible_tags
        ]

    if config.hidden_tags:
        # Remove hidden tags
        filtered_spec["tags"] = [
            tag for tag in filtered_spec.get("tags", [])
            if tag["name"] not in config.hidden_tags
        ]

    # Filter paths based on tags and user plan
    filtered_paths = {}
    for path, methods in filtered_spec.get("paths", {}).items():
        filtered_methods = {}

        for method, details in methods.items():
            # Get endpoint tags
            endpoint_tags = details.get("tags", [])

            # Check if any tag is hidden
            if any(tag in config.hidden_tags for tag in endpoint_tags):
                continue

            # Check if endpoint requires premium/enterprise
            is_premium = any(tag in config.premium_tags for tag in endpoint_tags)
            is_enterprise = any(tag in config.enterprise_tags for tag in endpoint_tags)

            # Add plan badges to description
            if is_enterprise:
                details["description"] = f"**🏢 Enterprise Only**\n\n{details.get('description', '')}"
                if user_plan not in ["enterprise"]:
                    details["description"] += "\n\n*Upgrade to Enterprise to access this endpoint.*"
            elif is_premium:
                details["description"] = f"**⭐ Pro Plan Required**\n\n{details.get('description', '')}"
                if user_plan not in ["pro", "enterprise"]:
                    details["description"] += "\n\n*Upgrade to Pro to access this endpoint.*"

            filtered_methods[method] = details

        if filtered_methods:
            filtered_paths[path] = filtered_methods

    filtered_spec["paths"] = filtered_paths

    return filtered_spec


# Example usage in main.py:
"""
from config.docs_config import get_docs_config, filter_openapi_spec
from config import settings

docs_config = get_docs_config(settings.EDITION)

# Option 1: Public docs (recommended for community)
app = FastAPI(
    title=docs_config.docs_title,
    description=docs_config.docs_description,
    docs_url="/docs" if docs_config.enable_swagger else None,
    redoc_url="/redoc" if docs_config.enable_redoc else None,
)

# Option 2: Authenticated docs (for SaaS)
@app.get("/docs", include_in_schema=False)
async def custom_docs(user: User = Depends(get_current_user)):
    # Filter spec based on user's plan
    openapi_spec = app.openapi()
    filtered_spec = filter_openapi_spec(openapi_spec, docs_config, user.plan)
    return get_swagger_ui_html(openapi_url="/filtered-openapi.json")

@app.get("/filtered-openapi.json", include_in_schema=False)
async def filtered_openapi(user: User = Depends(get_current_user)):
    openapi_spec = app.openapi()
    return filter_openapi_spec(openapi_spec, docs_config, user.plan)
"""