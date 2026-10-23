"""Shared caps for list endpoints so workspaces cannot unbounded-scan the DB."""

from __future__ import annotations

# Creative projects (with nested concepts + voiceovers)
CREATIVE_PROJECTS_DEFAULT = 100
CREATIVE_PROJECTS_MAX = 200

# Video projects load scenes/renders/assets — keep page size modest
VIDEO_PROJECTS_DEFAULT = 50
VIDEO_PROJECTS_MAX = 100

# Admin platform lists
ADMIN_LIST_DEFAULT = 200
ADMIN_LIST_MAX = 500

# Library promote-from-metrics scans
LIBRARY_PROMOTE_METRICS_MAX = 2000

# Generic workspace list fallbacks
WORKSPACE_LIST_DEFAULT = 100
WORKSPACE_LIST_MAX = 250
