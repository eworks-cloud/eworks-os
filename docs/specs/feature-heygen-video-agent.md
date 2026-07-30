# Software Design Specification — HeyGen Video Generation Agent

**Product:** Eworks OS — Multi-Agent Company Operating System  
**Feature:** HeyGen Video Generation Agent (Goose Plugin Integration)  
**Version:** 1.0.0  
**Status:** Final Specification  
**Author:** Morgan (PM)  
**Owner:** Cesar Schneider, Eworks Labs  
**Last Updated:** 2026-06-05  
**Type:** Feature Specification (SDD Methodology)

---

## Table of Contents

1. [Feature Vision & Motivation](#1-feature-vision--motivation)
2. [Scope & Boundaries](#2-scope--boundaries)
3. [Architecture & Integration Points](#3-architecture--integration-points)
4. [Data Models](#4-data-models)
5. [API Contracts & Interfaces](#5-api-contracts--interfaces)
6. [Execution Flow & Async Patterns](#6-execution-flow--async-patterns)
7. [Error Handling & Recovery](#7-error-handling--recovery)
8. [Credit & Resource Management](#8-credit--resource-management)
9. [Webhook & Notification System](#9-webhook--notification-system)
10. [Configuration & Secrets](#10-configuration--secrets)
11. [Example Workflows](#11-example-workflows)
12. [Acceptance Criteria](#12-acceptance-criteria)
13. [Traceability to Phase 2 Roadmap](#13-traceability-to-phase-2-roadmap)
14. [Risks, Constraints & Mitigations](#14-risks-constraints--mitigations)
15. [Glossary & References](#15-glossary--references)

---

## 1. Feature Vision & Motivation

### 1.1 Problem Statement

Eworks Labs currently generates video content manually via the `content-pipeline` module, requiring developers to invoke HeyGen directly through Python scripts. Video generation is a multi-step process (script → TTS → upload audio → submit job → poll → download), blocking on long-running operations (10–20 min), and lacks production-grade error recovery, retry logic, and credit management.

**Pain Points:**
- **No self-service abstraction:** Video generation buried in content-pipeline; not exposed as a reusable service
- **No async polling pattern:** Callers must wait synchronously or implement custom polling
- **No credit visibility:** Cannot check HeyGen quota before expensive operations
- **No webhook notifications:** No real-time alerts when videos complete or fail
- **No Goose plugin integration:** Video generation not available via Goose autonomous agent framework

### 1.2 Solution Overview

Expose HeyGen video generation as a **first-class Eworks OS agent** callable via the **Goose plugin system**. This agent SHALL:

1. **Provide a unified async video generation interface** supporting avatar selection, voice customization, and format control
2. **Implement full async/polling patterns** with exponential backoff and state persistence
3. **Expose credit checking and quota enforcement** to prevent failed generations
4. **Emit webhook notifications** for completion/failure events
5. **Integrate with Goose framework** as a callable tool/plugin
6. **Include production-grade error handling** with detailed recovery strategies
7. **Support multi-format output** (reel 9:16, YouTube 16:9, custom dimensions)

### 1.3 Business Value

| Dimension | Benefit |
|-----------|---------|
| **Automation** | Eliminates manual HeyGen script invocation; video generation becomes autonomous |
| **Integration** | Video agent participates in Goose autonomous workflows (content → video → publish) |
| **Scalability** | Async polling + persistence enables high-volume batch video generation |
| **Reliability** | Credit pre-checks prevent failed jobs; retry logic handles transient failures |
| **Observability** | Webhook notifications + detailed logging provide full visibility into video pipeline |

### 1.4 Success Metrics

- ✓ Video generation submission success rate ≥ 99%
- ✓ Async polling completes within 20 minutes for 95th percentile of jobs
- ✓ Credit depletion detected proactively; zero wasted generation attempts due to insufficient credits
- ✓ Webhook delivery success rate ≥ 99% (with retries)
- ✓ Agent callable from Goose framework with <100ms invocation latency
- ✓ Full traceability: video_id → job status → artifact storage → notification delivery

---

## 2. Scope & Boundaries

### 2.1 In Scope

| Feature | Details |
|---------|---------|
| **Avatar Selection** | Support built-in HeyGen avatars + allow custom avatar ID override |
| **Voice Configuration** | Support HeyGen TTS voices + pre-uploaded audio assets (asset_id) |
| **Format Support** | Reel (1080×1920, 9:16), YouTube (1920×1080, 16:9), custom dimensions |
| **Async Generation** | Submit job, return immediately with video_id; caller polls or receives webhook |
| **Polling Pattern** | Exponential backoff (10s → max 20 min); state persisted in database |
| **Credit Management** | Pre-flight quota check; track consumption; emit warnings at thresholds |
| **Error Handling** | Comprehensive error taxonomy; retry logic for transient failures |
| **Webhook System** | HTTP POST notifications on completion/failure; exponential retry |
| **Audio Upload** | Support uploading MP3 files to HeyGen as assets (for lip-sync) |
| **Video Download** | Stream-download completed videos to local `data/videos/` directory |
| **Goose Integration** | Callable tool specification; parameter schema; execution promise |

### 2.2 Out of Scope

| Item | Rationale |
|------|-----------|
| Custom avatar creation / training | HeyGen service limitation; Cesar selects from existing library |
| Background replacement / composition | HeyGen has limited options; simple color backgrounds only in MVP |
| Real-time video preview | Violates async pattern; full video only after completion |
| Video editing / post-processing | Domain outside HeyGen API; use separate video editing agent if needed |
| Multi-language TTS | MVP supports single voice; multi-language requires separate story |
| Lip-sync from streaming audio | Requires pre-uploaded asset; streaming not supported by HeyGen |
| Video analytics / performance tracking | Separate agent concern; HeyGen API provides no built-in analytics |

### 2.3 Northbound Integration Points

```
┌─────────────────────────────────────┐
│ Goose Autonomous Agent Framework    │
│ (Callable via plugin system)        │
└────────┬────────────────────────────┘
         │
         │ .invoke({"script": "...", "format": "reel"})
         ▼
┌─────────────────────────────────────┐
│ HeyGen Video Agent                  │
│ (This specification)                │
└────────┬────────────────────────────┘
         │
    ┌────┴─────────────────────┬──────────────────┐
    │                          │                  │
    ▼                          ▼                  ▼
┌──────────────┐   ┌────────────────────┐   ┌──────────────┐
│ HeyGen API   │   │ PostgreSQL (state) │   │ Webhook URLs │
│ v2/generate  │   │ (job tracking)     │   │ (notify)     │
└──────────────┘   └────────────────────┘   └──────────────┘
```

---

## 3. Architecture & Integration Points

### 3.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ HeyGenVideoAgent (Agent)                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Public API                                              │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • submit_video_generation(script, format, avatar, etc) │   │
│  │ • get_video_status(video_id)                           │   │
│  │ • check_credits()                                      │   │
│  │ • cancel_video(video_id)                               │   │
│  │ • list_avatars() / list_voices()                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Internal Services                                       │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • VideoJobManager (state machine, polling, retries)    │   │
│  │ • HeyGenClient (HTTP wrapper, auth, error handling)    │   │
│  │ • AudioAssetManager (upload, cache, lifecycle)         │   │
│  │ • WebhookDispatcher (notify on completion/failure)     │   │
│  │ • CreditTracker (quota checks, consumption tracking)   │   │
│  │ • VideoDownloader (stream to local storage)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Data Models                                             │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • VideoGenerationJob (status, progress, metadata)      │   │
│  │ • HeyGenVideoRequest (config snapshot)                 │   │
│  │ • AudioAsset (uploaded audio metadata)                 │   │
│  │ • WebhookDelivery (attempt tracking, retry state)      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Inheritance & Base Classes

```python
from eworks.agents.publisher.base_publisher import BasePublisher

class HeyGenVideoAgent(BasePublisher):
    """
    Async video generation via HeyGen API.
    
    Inherits:
    - BasePublisher: agent lifecycle, logging, database access
    - Provides: videos_dir, audio_dir, heygen_api_key from config
    """
    pass
```

### 3.3 External Dependencies

| Dependency | Version | Purpose | License |
|------------|---------|---------|---------|
| `requests` | ≥ 2.31.0 | HTTP client for HeyGen API | Apache 2.0 |
| `aiohttp` | ≥ 3.9.0 | Async HTTP client | Apache 2.0 |
| `asyncio` | stdlib | Async/await support | PSF |
| `tenacity` | ≥ 8.2.0 | Exponential backoff/retry | Apache 2.0 |
| PostgreSQL | ≥ 12 | Job state persistence | N/A |
| Python | ≥ 3.11 | Language runtime | PSF |

---

## 4. Data Models

### 4.1 VideoGenerationJob (PostgreSQL Table)

Tracks the complete lifecycle of a video generation request.

```sql
CREATE TABLE video_generation_jobs (
    id BIGSERIAL PRIMARY KEY,
    video_id VARCHAR(255) NOT NULL UNIQUE,  -- HeyGen-assigned ID
    status VARCHAR(50) NOT NULL,             -- submitted, processing, completed, failed, cancelled
    progress INT DEFAULT 0,                  -- percentage 0–100
    script_text TEXT NOT NULL,               -- user-provided script
    format VARCHAR(50) NOT NULL,             -- 'reel', 'youtube', or custom
    avatar_id VARCHAR(255),                  -- HeyGen avatar ID
    voice_id VARCHAR(255),                   -- HeyGen voice ID
    audio_asset_id VARCHAR(255) DEFAULT NULL, -- uploaded audio asset, if any
    voice_config JSONB,                      -- full voice config (text TTS vs audio)
    dimensions JSONB,                        -- {width: int, height: int}
    background_config JSONB,                 -- {type: 'color', value: '#...'}
    video_url TEXT,                          -- HeyGen CDN URL (after completion)
    local_path TEXT,                         -- local filesystem path (after download)
    duration_sec FLOAT DEFAULT NULL,         -- duration in seconds
    file_size_bytes BIGINT DEFAULT NULL,     -- downloaded file size
    error_code VARCHAR(50) DEFAULT NULL,     -- HeyGen error code if failed
    error_message TEXT DEFAULT NULL,         -- detailed error context
    credit_cost INT DEFAULT 0,               -- HeyGen credit units consumed
    polling_attempts INT DEFAULT 0,          -- total number of status checks
    max_polling_timeout_sec INT DEFAULT 1200, -- 20 minutes
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP DEFAULT NULL,
    created_by VARCHAR(255),                 -- Goose agent ID or user identifier
    metadata JSONB DEFAULT '{}',             -- arbitrary caller-provided context
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_video_jobs_video_id ON video_generation_jobs(video_id);
CREATE INDEX idx_video_jobs_status_created ON video_generation_jobs(status, created_at DESC);
CREATE INDEX idx_video_jobs_created_by ON video_generation_jobs(created_by);
```

### 4.2 AudioAsset (PostgreSQL Table)

Tracks uploaded audio files for lip-sync generation.

```sql
CREATE TABLE audio_assets (
    id BIGSERIAL PRIMARY KEY,
    asset_id VARCHAR(255) NOT NULL UNIQUE,  -- HeyGen asset ID
    file_name VARCHAR(255),                 -- original filename
    file_size_bytes INT,                    -- size in bytes
    duration_sec FLOAT,                     -- audio duration
    hash_sha256 VARCHAR(64) UNIQUE,         -- content hash for dedup
    local_path TEXT,                        -- path to local MP3 file
    uploaded_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,                   -- HeyGen assets may expire
    status VARCHAR(50) DEFAULT 'active',    -- active, expired, deleted
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audio_assets_asset_id ON audio_assets(asset_id);
CREATE INDEX idx_audio_assets_hash ON audio_assets(hash_sha256);
```

### 4.3 WebhookDelivery (PostgreSQL Table)

Tracks delivery attempts for webhook notifications.

```sql
CREATE TABLE webhook_deliveries (
    id BIGSERIAL PRIMARY KEY,
    video_job_id BIGINT NOT NULL REFERENCES video_generation_jobs(id),
    webhook_url TEXT NOT NULL,              -- URL to notify
    event_type VARCHAR(50) NOT NULL,        -- 'completion', 'failure'
    payload JSONB NOT NULL,                 -- serialized event data
    status VARCHAR(50) DEFAULT 'pending',   -- pending, delivered, failed, exhausted
    http_status_code INT,                   -- final HTTP response code
    error_message TEXT,                     -- last error
    attempts INT DEFAULT 0,                 -- number of delivery attempts
    max_attempts INT DEFAULT 5,
    next_retry_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhook_deliveries_video_job_id ON webhook_deliveries(video_job_id);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status, next_retry_at);
```

### 4.4 Domain Models (Python Data Classes)

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

class VideoStatus(str, Enum):
    SUBMITTED = "submitted"      # Job queued with HeyGen
    PROCESSING = "processing"    # HeyGen is generating
    COMPLETED = "completed"      # Video ready
    FAILED = "failed"            # Generation error (permanent)
    CANCELLED = "cancelled"      # User or system cancelled
    TIMEOUT = "timeout"          # Polling exceeded max duration

class AudioAssetStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DELETED = "deleted"

@dataclass
class VoiceConfig:
    """Voice configuration for video generation."""
    type: str  # 'text' or 'audio'
    
    # For type='text' (TTS)
    input_text: Optional[str] = None
    voice_id: Optional[str] = None
    
    # For type='audio' (pre-recorded)
    audio_asset_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        if self.type == "text":
            return {
                "type": "text",
                "input_text": self.input_text,
                "voice_id": self.voice_id,
            }
        elif self.type == "audio":
            return {
                "type": "audio",
                "audio_asset_id": self.audio_asset_id,
            }
        raise ValueError(f"Unknown voice config type: {self.type}")

@dataclass
class Dimensions:
    """Video output dimensions."""
    width: int
    height: int
    
    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0 else 0

@dataclass
class VideoGenerationRequest:
    """User-facing request for video generation."""
    script_text: str
    format: str = "reel"  # 'reel' (9:16), 'youtube' (16:9)
    avatar_id: Optional[str] = None
    voice_config: Optional[VoiceConfig] = None
    audio_asset_id: Optional[str] = None
    background_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    webhook_url: Optional[str] = None
    created_by: Optional[str] = None

@dataclass
class VideoGenerationJob:
    """Full job state (from database)."""
    id: int
    video_id: str
    status: VideoStatus
    script_text: str
    format: str
    avatar_id: Optional[str]
    voice_config: Dict[str, Any]
    dimensions: Dict[str, int]
    background_config: Optional[Dict[str, Any]]
    video_url: Optional[str]
    local_path: Optional[str]
    duration_sec: Optional[float]
    error_code: Optional[str]
    error_message: Optional[str]
    polling_attempts: int
    credit_cost: int
    submitted_at: datetime
    completed_at: Optional[datetime]
    created_by: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class AudioAsset:
    """Metadata for an uploaded audio asset."""
    asset_id: str
    file_name: str
    file_size_bytes: int
    duration_sec: Optional[float]
    hash_sha256: str
    local_path: str
    uploaded_at: datetime
    expires_at: Optional[datetime]
    status: AudioAssetStatus
    created_by: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class CreditsInfo:
    """Current credit quota info."""
    remaining_quota: int
    total_quota: int
    consumed_this_month: int
    reset_date: Optional[str]
```

---

## 5. API Contracts & Interfaces

### 5.1 Public Agent Methods

#### 5.1.1 `submit_video_generation(request: VideoGenerationRequest) → dict`

**Signature:**
```python
async def submit_video_generation(
    self,
    request: VideoGenerationRequest
) -> Dict[str, Any]:
    """
    Submit a video generation request to HeyGen.
    
    Returns immediately with video_id and status='submitted'.
    Polling or webhook notification provides completion status.
    
    Args:
        request: VideoGenerationRequest with script, format, audio config
    
    Returns:
        {
            "video_id": str,
            "status": "submitted",
            "job_id": int,  # local database ID
            "dimensions": {"width": int, "height": int},
            "format": str,
            "submitted_at": str (ISO 8601),
            "estimated_completion_min": int
        }
    
    Raises:
        ValueError: Invalid request (missing script, bad format, etc)
        RuntimeError: Insufficient credits, auth failure, API error
        FileNotFoundError: Audio asset file not found
    """
```

**Preconditions:**
- HeyGen API key configured and valid
- script_text is non-empty and ≤ 10,000 characters
- format is one of: 'reel', 'youtube'
- avatar_id (if provided) is a valid HeyGen avatar ID
- voice_id (if provided) is a valid HeyGen voice ID
- audio_asset_id (if provided) exists and is not expired
- Credits available ≥ estimated cost for format

**Postconditions:**
- VideoGenerationJob inserted into database with status='submitted'
- video_id returned to caller
- Job enters polling queue (background task starts polling)
- Webhook URL (if provided) will be called on completion/failure

**Example:**
```python
request = VideoGenerationRequest(
    script_text="Hello, this is a test video.",
    format="reel",
    avatar_id="494ce8a1dbe64573a4cb1684ad0e0e14",
    voice_config=VoiceConfig(
        type="text",
        voice_id="c0a044792fc64b3fa7dfc0700da93016",
        input_text="Hello, this is a test video."
    ),
    webhook_url="https://example.com/webhooks/video-complete",
    metadata={"campaign_id": 42, "user_id": "goose:1"}
)

result = await agent.submit_video_generation(request)
# {
#     "video_id": "abc123def456",
#     "status": "submitted",
#     "job_id": 1001,
#     "format": "reel",
#     "submitted_at": "2026-06-05T10:30:00Z",
#     "estimated_completion_min": 8
# }
```

---

#### 5.1.2 `get_video_status(video_id: str) → dict`

**Signature:**
```python
async def get_video_status(
    self,
    video_id: str
) -> Dict[str, Any]:
    """
    Retrieve current status of a video generation job.
    
    Args:
        video_id: HeyGen-assigned video ID
    
    Returns:
        {
            "video_id": str,
            "status": str,  # submitted, processing, completed, failed, etc
            "progress": int,  # 0–100
            "local_path": str or None,
            "video_url": str or None,
            "error_code": str or None,
            "error_message": str or None,
            "duration_sec": float or None,
            "polling_attempts": int,
            "submitted_at": str (ISO 8601),
            "completed_at": str (ISO 8601) or None,
            "metadata": dict
        }
    
    Raises:
        NotFoundError: video_id not found in database
    """
```

**Example:**
```python
status = await agent.get_video_status("abc123def456")
# {
#     "video_id": "abc123def456",
#     "status": "completed",
#     "progress": 100,
#     "local_path": "/data/videos/abc123def456.mp4",
#     "video_url": "https://cdn.heygen.com/...",
#     "duration_sec": 45.3,
#     "polling_attempts": 45,
#     "submitted_at": "2026-06-05T10:30:00Z",
#     "completed_at": "2026-06-05T10:37:23Z"
# }
```

---

#### 5.1.3 `check_credits() → dict`

**Signature:**
```python
async def check_credits(self) -> Dict[str, Any]:
    """
    Check remaining HeyGen API credits/quota.
    
    Returns:
        {
            "remaining_quota": int,
            "total_quota": int,
            "consumed_this_month": int,
            "reset_date": str (ISO 8601) or None,
            "warning": str or None  # e.g., "10% remaining"
        }
    
    Raises:
        RuntimeError: Auth failure or HeyGen API error
    """
```

**Example:**
```python
credits = await agent.check_credits()
# {
#     "remaining_quota": 250,
#     "total_quota": 10000,
#     "consumed_this_month": 9750,
#     "reset_date": "2026-07-01T00:00:00Z",
#     "warning": "10% remaining"
# }
```

---

#### 5.1.4 `upload_audio(audio_path: str | Path) → dict`

**Signature:**
```python
async def upload_audio(
    self,
    audio_path: str | Path
) -> Dict[str, Any]:
    """
    Upload an MP3 audio file to HeyGen for use in lip-sync generation.
    
    Args:
        audio_path: Absolute or relative path to .mp3 file
    
    Returns:
        {
            "asset_id": str,
            "file_name": str,
            "file_size_bytes": int,
            "duration_sec": float or None,
            "hash_sha256": str,
            "uploaded_at": str (ISO 8601),
            "local_path": str
        }
    
    Raises:
        FileNotFoundError: audio_path does not exist
        ValueError: File is not .mp3 or size exceeds limit (100 MB)
        RuntimeError: Upload failed or HeyGen error
    """
```

**Deduplication:** If the same file (by SHA256 hash) is already uploaded and not expired, return the existing asset_id without re-uploading.

**Example:**
```python
audio_result = await agent.upload_audio("/tmp/my_narration.mp3")
# {
#     "asset_id": "xyz789abc123",
#     "file_name": "my_narration.mp3",
#     "file_size_bytes": 2048576,
#     "duration_sec": 42.5,
#     "hash_sha256": "a1b2c3d4...",
#     "uploaded_at": "2026-06-05T10:20:00Z",
#     "local_path": "/data/audio/my_narration.mp3"
# }
```

---

#### 5.1.5 `cancel_video(video_id: str) → dict`

**Signature:**
```python
async def cancel_video(self, video_id: str) -> Dict[str, Any]:
    """
    Cancel a video generation job (if still processing).
    
    Args:
        video_id: HeyGen video ID
    
    Returns:
        {
            "video_id": str,
            "status": "cancelled",
            "cancelled_at": str (ISO 8601)
        }
    
    Raises:
        NotFoundError: video_id not found
        RuntimeError: Cannot cancel (already completed/failed)
    """
```

**Behavior:**
- If status is 'submitted' or 'processing': mark as 'cancelled', stop polling
- If status is 'completed' or 'failed': raise error (cannot cancel terminal states)
- Return confirmation with timestamp

---

#### 5.1.6 `list_avatars() → dict`

**Signature:**
```python
async def list_avatars(self) -> Dict[str, Any]:
    """
    List available HeyGen avatars for the account.
    
    Returns:
        {
            "avatars": [
                {
                    "avatar_id": str,
                    "name": str,
                    "gender": str,
                    "preview_image_url": str
                },
                ...
            ]
        }
    
    Raises:
        RuntimeError: HeyGen API error
    """
```

---

#### 5.1.7 `list_voices() → dict`

**Signature:**
```python
async def list_voices(self) -> Dict[str, Any]:
    """
    List available HeyGen TTS voices.
    
    Returns:
        {
            "voices": [
                {
                    "voice_id": str,
                    "name": str,
                    "language": str,
                    "accent": str
                },
                ...
            ]
        }
    
    Raises:
        RuntimeError: HeyGen API error
    """
```

---

### 5.2 Goose Plugin Integration

The HeyGen agent is callable via Goose framework as a **tool**.

**Plugin Registration:**
```python
# eworks/plugins/goose/heygen_video_tool.py

from goose.plugin import ToolDefinition, ToolSchema

HEYGEN_VIDEO_TOOL = ToolDefinition(
    name="heygen_generate_video",
    description="Generate an AI avatar video with custom script and format",
    schema=ToolSchema(
        type="object",
        properties={
            "script": {
                "type": "string",
                "description": "Script for the avatar to speak (max 10,000 chars)"
            },
            "format": {
                "type": "string",
                "enum": ["reel", "youtube"],
                "description": "Video format: 'reel' (9:16) or 'youtube' (16:9)"
            },
            "avatar_id": {
                "type": "string",
                "description": "HeyGen avatar ID (optional; defaults to Cesar)"
            },
            "voice_id": {
                "type": "string",
                "description": "HeyGen voice ID for TTS (optional; defaults to Cesar's voice)"
            },
            "audio_asset_id": {
                "type": "string",
                "description": "Pre-uploaded audio asset ID for lip-sync (optional; overrides voice_id)"
            },
            "webhook_url": {
                "type": "string",
                "description": "HTTP URL to notify on completion (optional)"
            },
            "metadata": {
                "type": "object",
                "description": "Caller-provided context (optional)"
            }
        },
        required=["script", "format"]
    ),
    fn=agent.submit_video_generation
)
```

**Goose Invocation:**
```python
# From a Goose agent workflow

result = await goose.invoke_tool(
    "heygen_generate_video",
    {
        "script": "Today we're announcing our new AI automation platform.",
        "format": "youtube",
        "webhook_url": "https://eworks.internal/webhooks/video-ready"
    }
)
# Returns: {
#     "video_id": "vid_xyz123",
#     "status": "submitted",
#     "job_id": 1005,
#     "format": "youtube",
#     "submitted_at": "2026-06-05T10:35:00Z"
# }
```

---

## 6. Execution Flow & Async Patterns

### 6.1 Video Generation State Machine

```
┌─────────────┐
│  SUBMITTED  │  (job queued with HeyGen)
└──────┬──────┘
       │
       │ [polling started]
       ▼
┌─────────────────┐
│  PROCESSING     │  (HeyGen generating)
└──────┬──────────┘
       │
       │ [progress updates via polling]
       │
       ├──► [error detected] ──────┐
       │                           │
       ▼                           ▼
┌──────────────┐          ┌─────────────────┐
│  COMPLETED   │          │  FAILED         │
│  (video_url  │          │  (error_code,   │
│   ready)     │          │   error_message)│
└──────┬───────┘          └─────────────────┘
       │
       │ [download started]
       ▼
┌─────────────────────┐
│  COMPLETED          │
│  (local_path set)   │
└─────────────────────┘
       │
       │ [webhook notification sent (if configured)]
       ▼
     [DONE]

Optional: CANCELLED (user requests cancellation before completion)
```

### 6.2 Submission Flow (Synchronous Return)

```python
async def submit_video_generation(
    self, request: VideoGenerationRequest
) -> Dict[str, Any]:
    """
    Step 1: Validate request
    Step 2: Pre-flight credit check
    Step 3: Resolve voice config (TTS vs audio)
    Step 4: Build HeyGen payload
    Step 5: Submit to HeyGen API (synchronous POST)
    Step 6: Extract video_id from response
    Step 7: Store job in database (status='submitted')
    Step 8: Return immediately with video_id
    Step 9: Background: start async polling task
    """
    
    # Step 1: Validate
    if not request.script_text or len(request.script_text) > 10000:
        raise ValueError("script_text must be 1–10,000 characters")
    if request.format not in ("reel", "youtube"):
        raise ValueError("format must be 'reel' or 'youtube'")
    
    # Step 2: Credit check
    credits = await self.check_credits()
    format_cost = {"reel": 15, "youtube": 20}.get(request.format, 15)
    if credits["remaining_quota"] < format_cost:
        raise RuntimeError(
            f"Insufficient credits: {credits['remaining_quota']} remaining, "
            f"{format_cost} required"
        )
    
    # Step 3: Voice config
    if request.audio_asset_id:
        voice_config = VoiceConfig(
            type="audio",
            audio_asset_id=request.audio_asset_id
        )
    else:
        voice_config = VoiceConfig(
            type="text",
            voice_id=request.voice_config.voice_id or self.DEFAULT_VOICE_ID,
            input_text=request.script_text
        )
    
    # Step 4: Build HeyGen payload
    dimensions = self._get_dimensions(request.format)
    payload = {
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": request.avatar_id or self.DEFAULT_AVATAR_ID
            },
            "voice": voice_config.to_dict(),
            "background": request.background_config or {"type": "color", "value": "#000000"}
        }],
        "dimension": {"width": dimensions.width, "height": dimensions.height}
    }
    
    # Step 5: Submit to HeyGen
    response = await self.heygen_client.post(
        "/v2/video/generate",
        json=payload
    )
    
    # Step 6: Extract video_id
    video_id = response.get("data", {}).get("video_id")
    if not video_id:
        raise RuntimeError(f"HeyGen returned no video_id: {response}")
    
    # Step 7: Store in database
    job = VideoGenerationJob(
        video_id=video_id,
        status=VideoStatus.SUBMITTED,
        script_text=request.script_text,
        format=request.format,
        # ... other fields
    )
    job_id = await self.db.insert_video_job(job)
    
    # Step 8: Return immediately
    return {
        "video_id": video_id,
        "status": "submitted",
        "job_id": job_id,
        "format": request.format,
        "estimated_completion_min": 8
    }
    
    # Step 9: Background task (spawned, not awaited)
    asyncio.create_task(self._poll_video_async(video_id, job_id))
```

### 6.3 Polling Flow (Background Task)

```python
async def _poll_video_async(self, video_id: str, job_id: int):
    """
    Background polling task (spawned on submission, runs until completion).
    
    Exponential backoff: 10s, 15s, 20s, 25s, ..., max 60s
    Max total polling: 20 minutes
    """
    
    attempt = 0
    backoff_sec = 10
    deadline = time.time() + 1200  # 20 minutes
    
    while time.time() < deadline:
        attempt += 1
        await asyncio.sleep(backoff_sec)
        
        try:
            # Query HeyGen for status
            status_resp = await self.heygen_client.get(
                "/v1/video_status.get",
                params={"video_id": video_id}
            )
            
            status = status_resp.get("data", {}).get("status", "unknown")
            progress = status_resp.get("data", {}).get("progress", 0)
            
            # Log progress
            logger.info(
                f"Video {video_id} poll #{attempt}: {status} ({progress}%)"
            )
            
            # Update database with progress
            await self.db.update_video_job(
                job_id,
                status=status,
                progress=progress,
                polling_attempts=attempt
            )
            
            # Check for completion
            if status == "completed":
                video_url = status_resp.get("data", {}).get("video_url")
                duration = status_resp.get("data", {}).get("duration")
                
                # Download video
                local_path = await self._download_video(video_id, video_url)
                
                # Update job with completion
                await self.db.update_video_job(
                    job_id,
                    status=VideoStatus.COMPLETED,
                    progress=100,
                    video_url=video_url,
                    local_path=str(local_path),
                    duration_sec=duration,
                    completed_at=datetime.utcnow()
                )
                
                # Notify via webhook
                await self.webhook_dispatcher.send(
                    job_id,
                    event_type="completion",
                    payload={
                        "video_id": video_id,
                        "video_url": video_url,
                        "local_path": str(local_path),
                        "duration_sec": duration
                    }
                )
                
                logger.info(f"Video {video_id} completed")
                return
            
            elif status == "failed":
                error_code = status_resp.get("data", {}).get("error_code")
                error_msg = status_resp.get("data", {}).get("error_message", "Unknown error")
                
                await self.db.update_video_job(
                    job_id,
                    status=VideoStatus.FAILED,
                    error_code=error_code,
                    error_message=error_msg,
                    completed_at=datetime.utcnow()
                )
                
                await self.webhook_dispatcher.send(
                    job_id,
                    event_type="failure",
                    payload={
                        "video_id": video_id,
                        "error_code": error_code,
                        "error_message": error_msg
                    }
                )
                
                logger.error(f"Video {video_id} failed: {error_msg}")
                return
            
            # Continue polling; apply exponential backoff
            backoff_sec = min(backoff_sec + 5, 60)
        
        except Exception as e:
            logger.exception(f"Poll attempt #{attempt} failed: {e}")
            backoff_sec = min(backoff_sec + 5, 60)
            # Continue retrying until deadline
    
    # Timeout
    await self.db.update_video_job(
        job_id,
        status=VideoStatus.TIMEOUT,
        error_message=f"Polling exceeded {1200}s limit"
    )
    await self.webhook_dispatcher.send(
        job_id,
        event_type="failure",
        payload={"video_id": video_id, "error": "Polling timeout"}
    )
    logger.error(f"Video {video_id} polling timeout")
```

### 6.4 Download Flow

```python
async def _download_video(
    self,
    video_id: str,
    video_url: str
) -> Path:
    """
    Stream-download completed video from HeyGen CDN to local storage.
    
    Args:
        video_id: HeyGen video ID
        video_url: CDN URL from HeyGen
    
    Returns:
        Path to downloaded .mp4 file
    """
    dest = self.videos_dir / f"{video_id}.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(video_url, timeout=300) as resp:
            resp.raise_for_status()
            
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            
            with open(dest, "wb") as f:
                async for chunk in resp.content.iter_chunked(256 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        pct = (downloaded / total_size) * 100
                        logger.debug(f"Download progress: {pct:.1f}%")
    
    logger.info(f"Downloaded {video_id} to {dest}")
    return dest.resolve()
```

---

## 7. Error Handling & Recovery

### 7.1 Error Taxonomy

| Category | Error Code | HTTP Status | Cause | Recovery |
|----------|-----------|-------------|-------|----------|
| **Auth** | INVALID_API_KEY | 401 | Invalid/expired HeyGen API key | Rotate key in secrets; alert operator |
| **Credit** | INSUFFICIENT_CREDITS | 402 | Not enough quota remaining | Check credits; reject submission; alert operator |
| **Validation** | INVALID_REQUEST | 400 | Bad payload structure | Log request; fix before retry |
| **Rate Limit** | RATE_LIMITED | 429 | API rate limit exceeded | Exponential backoff; retry after delay |
| **Server** | INTERNAL_ERROR | 500–599 | HeyGen server error | Exponential backoff; retry up to 5 times |
| **Not Found** | VIDEO_NOT_FOUND | 404 | video_id doesn't exist | Log; mark job as failed |
| **Timeout** | TIMEOUT | — | Polling exceeded 20 min | Mark as TIMEOUT; notify webhook |
| **Network** | CONNECTION_ERROR | — | Network unreachable | Exponential backoff; retry |

### 7.2 Error Handling Strategy

#### 7.2.1 Submission Phase (Synchronous)

```python
async def submit_video_generation(self, request):
    try:
        # Validation errors are immediate failures
        validate_request(request)
    except ValueError as e:
        raise ValueError(f"Invalid request: {e}")
    
    try:
        # Credit check
        credits = await self.check_credits()
    except RuntimeError as e:
        if "401" in str(e):
            logger.critical("HeyGen auth failed; check API key")
            raise
        elif "rate_limited" in str(e).lower():
            # Retry once after exponential backoff
            await asyncio.sleep(30)
            credits = await self.check_credits()
        else:
            raise
    
    # Verify credits
    if credits["remaining_quota"] < estimated_cost:
        raise RuntimeError(
            f"Insufficient credits: {credits['remaining_quota']} "
            f"remaining, {estimated_cost} required"
        )
    
    try:
        # Submit to HeyGen
        response = await self.heygen_client.post(...)
    except RuntimeError as e:
        if "429" in str(e):  # Rate limit
            logger.warning(f"Rate limited on submission; retrying...")
            await asyncio.sleep(60)
            response = await self.heygen_client.post(...)
        elif "500" in str(e) or "502" in str(e):  # Server error
            logger.warning(f"HeyGen server error; retrying...")
            await asyncio.sleep(30)
            response = await self.heygen_client.post(...)
        elif "402" in str(e):  # Out of credits
            raise RuntimeError("Out of HeyGen credits")
        else:
            raise
    
    # On success, return video_id and spawn background polling
    video_id = extract_video_id(response)
    # ... save job, spawn polling task
    return {"video_id": video_id, ...}
```

#### 7.2.2 Polling Phase (Asynchronous)

```python
async def _poll_video_async(self, video_id, job_id):
    """
    Polling is resilient to transient failures.
    - Exponential backoff on network/server errors
    - Permanent failures (404, auth) → mark job as FAILED
    """
    
    backoff = 10
    deadline = time.time() + 1200
    
    while time.time() < deadline:
        await asyncio.sleep(backoff)
        
        try:
            status_resp = await self.heygen_client.get(
                "/v1/video_status.get",
                params={"video_id": video_id}
            )
        except RuntimeError as e:
            if "429" in str(e):  # Rate limit
                backoff = min(backoff * 1.5, 120)
                logger.warning(f"Rate limited; increasing backoff to {backoff}s")
                continue
            elif "500" in str(e) or "502" in str(e):  # Server error
                backoff = min(backoff * 1.5, 120)
                logger.warning(f"Server error; retrying with backoff {backoff}s")
                continue
            elif "401" in str(e):  # Auth failure
                logger.critical("Auth failure during polling; stopping")
                await self.db.update_video_job(
                    job_id,
                    status=VideoStatus.FAILED,
                    error_message="Authentication failed"
                )
                return
            elif "404" in str(e):  # Video not found (shouldn't happen)
                logger.error(f"Video {video_id} not found on HeyGen; marking as FAILED")
                await self.db.update_video_job(
                    job_id,
                    status=VideoStatus.FAILED,
                    error_message="Video not found on HeyGen API"
                )
                return
            else:
                logger.exception(f"Unexpected error during polling: {e}")
                backoff = min(backoff * 1.5, 120)
                continue
        
        # Process status response
        status = status_resp.get("data", {}).get("status")
        
        if status == "completed":
            # Download and finish
            ...
            return
        elif status == "failed":
            # Mark as failed and finish
            ...
            return
        else:
            # Continue polling (pending, processing, etc)
            backoff = min(backoff + 5, 60)  # Exponential backoff up to 60s
    
    # Timeout after 20 minutes
    logger.error(f"Video {video_id} polling timeout")
    await self.db.update_video_job(
        job_id,
        status=VideoStatus.TIMEOUT,
        error_message="Polling exceeded 1200s limit"
    )
```

#### 7.2.3 Download Phase

```python
async def _download_video(self, video_id, video_url):
    """
    Download is resilient to network interruptions.
    - Retry up to 3 times with exponential backoff
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, timeout=300) as resp:
                    resp.raise_for_status()
                    # ... stream download
                    return dest.resolve()
        except Exception as e:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    f"Download attempt {attempt+1} failed; "
                    f"retrying in {backoff}s: {e}"
                )
                await asyncio.sleep(backoff)
            else:
                logger.error(f"Download failed after {max_retries} attempts: {e}")
                raise RuntimeError(f"Failed to download video: {e}")
```

### 7.3 Logging & Observability

All errors logged with:
- **timestamp** (UTC)
- **video_id** (if known)
- **error_code** (if from HeyGen)
- **stack trace** (at ERROR level)
- **context** (request payload, response body)

**Log Levels:**
- `DEBUG`: Polling progress, backoff decisions
- `INFO`: Submission, completion, download finish
- `WARNING`: Rate limits, transient errors, retries
- `ERROR`: Permanent failures, auth issues, timeout
- `CRITICAL`: Out of credits, missing API key

**Example:**
```
2026-06-05T10:35:42Z [INFO] Video abc123 submitted (format=reel)
2026-06-05T10:35:52Z [DEBUG] Video abc123 poll #1: status=submitted (0%)
2026-06-05T10:36:12Z [DEBUG] Video abc123 poll #2: status=processing (25%)
2026-06-05T10:36:32Z [DEBUG] Video abc123 poll #3: status=processing (50%)
2026-06-05T10:36:52Z [DEBUG] Video abc123 poll #4: status=processing (75%)
2026-06-05T10:37:22Z [DEBUG] Video abc123 poll #5: status=completed (100%)
2026-06-05T10:37:23Z [INFO] Video abc123 downloaded to /data/videos/abc123.mp4
2026-06-05T10:37:24Z [INFO] Webhook notification sent to https://example.com/webhooks/video
```

---

## 8. Credit & Resource Management

### 8.1 Credit Cost Model

HeyGen charges credits based on video format and duration:

| Format | Dimension | Duration | Cost/Min | Example 1min |
|--------|-----------|----------|----------|----------------|
| Reel | 1080×1920 (9:16) | ≤ 60s | 15 credits | 15 credits |
| YouTube | 1920×1080 (16:9) | ≤ 60s | 20 credits | 20 credits |
| Custom | variable | variable | variable | contact HeyGen |

**Assumption:** Cost is fixed per format up to 60 seconds; beyond that, charged per minute.

### 8.2 Pre-Flight Credit Check

**All submissions SHALL check credits before sending to HeyGen:**

```python
async def submit_video_generation(self, request):
    # Step: Check credits
    credits = await self.check_credits()
    
    # Estimate cost for this format
    estimated_cost = {"reel": 15, "youtube": 20}.get(request.format, 15)
    
    if credits["remaining_quota"] < estimated_cost:
        raise RuntimeError(
            f"Insufficient credits: {credits['remaining_quota']} remaining, "
            f"{estimated_cost} required. Reset date: {credits.get('reset_date')}"
        )
    
    # Also warn if low (< 20% remaining)
    utilization = (
        (credits["total_quota"] - credits["remaining_quota"]) 
        / credits["total_quota"]
    )
    if utilization > 0.8:
        logger.warning(
            f"HeyGen credit utilization at {utilization*100:.1f}%; "
            f"only {credits['remaining_quota']} remaining"
        )
```

### 8.3 Credit Tracking

Store estimated cost in `VideoGenerationJob`:

```sql
ALTER TABLE video_generation_jobs ADD COLUMN credit_cost INT DEFAULT 0;
```

Update after completion (if HeyGen returns actual cost):

```python
# After polling completes
actual_cost = status_resp.get("data", {}).get("credit_cost", estimated_cost)
await self.db.update_video_job(job_id, credit_cost=actual_cost)
```

### 8.4 Resource Limits

- **Concurrent polling tasks:** ≤ 50 (prevent memory exhaustion)
- **Max job retention:** 30 days (then archive/delete)
- **Video storage:** ≤ 500 GB (auto-prune oldest if exceeded)
- **Webhook retry:** ≤ 5 attempts over 7 days

---

## 9. Webhook & Notification System

### 9.1 Webhook Payload Schemas

#### 9.1.1 Video Completion Event

```json
{
    "event_type": "completion",
    "video_id": "abc123def456",
    "job_id": 1001,
    "timestamp": "2026-06-05T10:37:23Z",
    "video_url": "https://cdn.heygen.com/video/abc123.mp4",
    "local_path": "/data/videos/abc123def456.mp4",
    "format": "reel",
    "dimensions": {
        "width": 1080,
        "height": 1920
    },
    "duration_sec": 45.3,
    "file_size_bytes": 12582912,
    "polling_attempts": 5,
    "total_duration_sec": 108,
    "metadata": {
        "campaign_id": 42,
        "user_id": "goose:1"
    }
}
```

#### 9.1.2 Video Failure Event

```json
{
    "event_type": "failure",
    "video_id": "abc123def456",
    "job_id": 1001,
    "timestamp": "2026-06-05T10:37:23Z",
    "error_code": "AVATAR_NOT_FOUND",
    "error_message": "Avatar ID 'invalid-id' does not exist",
    "polling_attempts": 3,
    "total_duration_sec": 35,
    "metadata": {
        "campaign_id": 42,
        "user_id": "goose:1"
    }
}
```

### 9.2 Webhook Delivery Guarantees

- **At-least-once delivery:** Webhook called 1+ times per event
- **Exponential retry:** 1min, 2min, 5min, 15min, 1hr (5 attempts over ~2hrs)
- **Timeout:** 30-second HTTP timeout per attempt
- **Success criteria:** HTTP 2xx response code
- **Idempotency:** Caller SHOULD treat duplicate events as idempotent

### 9.3 Webhook Dispatcher Implementation

```python
async def send_webhook(
    self,
    job_id: int,
    event_type: str,
    payload: Dict[str, Any]
) -> None:
    """
    Send webhook notification with exponential retry.
    
    Stores in webhook_deliveries table for async processing.
    Background task pulls pending webhooks and retries.
    """
    
    # Get webhook URL from job
    job = await self.db.get_video_job(job_id)
    if not job.webhook_url:
        logger.debug(f"No webhook URL for job {job_id}; skipping")
        return
    
    # Create webhook delivery record
    delivery = WebhookDelivery(
        video_job_id=job_id,
        webhook_url=job.webhook_url,
        event_type=event_type,
        payload=payload,
        status="pending",
        attempts=0,
        max_attempts=5
    )
    
    delivery_id = await self.db.insert_webhook_delivery(delivery)
    
    # Trigger async delivery
    asyncio.create_task(
        self._deliver_webhook_async(delivery_id)
    )

async def _deliver_webhook_async(self, delivery_id: int) -> None:
    """
    Background task to deliver webhook with exponential retry.
    """
    delivery = await self.db.get_webhook_delivery(delivery_id)
    
    backoff_sec = 60
    for attempt in range(delivery.max_attempts):
        await asyncio.sleep(backoff_sec)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    delivery.webhook_url,
                    json=delivery.payload,
                    timeout=30,
                    headers={"X-HeyGen-Event": delivery.event_type}
                ) as resp:
                    if resp.status < 300:  # 2xx success
                        await self.db.update_webhook_delivery(
                            delivery_id,
                            status="delivered",
                            http_status_code=resp.status,
                            delivered_at=datetime.utcnow(),
                            attempts=attempt + 1
                        )
                        logger.info(f"Webhook {delivery_id} delivered")
                        return
                    else:
                        raise RuntimeError(f"HTTP {resp.status}")
        
        except Exception as e:
            logger.warning(
                f"Webhook {delivery_id} attempt {attempt+1} failed: {e}; "
                f"retrying in {backoff_sec}s"
            )
            
            backoff_sec = min(backoff_sec * 3, 3600)  # Cap at 1 hour
            
            if attempt == delivery.max_attempts - 1:
                await self.db.update_webhook_delivery(
                    delivery_id,
                    status="exhausted",
                    error_message=str(e),
                    attempts=attempt + 1
                )
                logger.error(
                    f"Webhook {delivery_id} exhausted after {delivery.max_attempts} attempts"
                )
```

---

## 10. Configuration & Secrets

### 10.1 Environment Variables

```bash
# HeyGen API Authentication
HEYGEN_API_KEY=sk_V2_...  # Loaded from ~/.hermes/.env or Vault

# Defaults
HEYGEN_DEFAULT_AVATAR_ID=494ce8a1dbe64573a4cb1684ad0e0e14
HEYGEN_DEFAULT_VOICE_ID=c0a044792fc64b3fa7dfc0700da93016

# Polling Configuration
HEYGEN_POLL_INTERVAL_SEC=10
HEYGEN_MAX_POLL_DURATION_SEC=1200  # 20 minutes

# Resource Limits
HEYGEN_MAX_CONCURRENT_POLLS=50
HEYGEN_VIDEO_STORAGE_LIMIT_GB=500
HEYGEN_JOB_RETENTION_DAYS=30

# Webhook Configuration
HEYGEN_WEBHOOK_TIMEOUT_SEC=30
HEYGEN_WEBHOOK_MAX_RETRIES=5
```

### 10.2 Agent Configuration (YAML/JSON)

```yaml
# eworks/config/agents/heygen-video-agent.yaml

name: heygen-video-agent
type: video-generation

defaults:
  avatar_id: "494ce8a1dbe64573a4cb1684ad0e0e14"  # Cesar CTO
  voice_id: "c0a044792fc64b3fa7dfc0700da93016"   # Cesar's voice
  
format_defaults:
  reel:
    width: 1080
    height: 1920
    cost_credits: 15
  youtube:
    width: 1920
    height: 1080
    cost_credits: 20

polling:
  interval_sec: 10
  max_duration_sec: 1200
  backoff_multiplier: 1.5
  backoff_max_sec: 60

storage:
  video_dir: "data/videos"
  audio_dir: "data/audio"
  retention_days: 30

webhook:
  timeout_sec: 30
  max_retries: 5
  retry_backoff_sec: [60, 120, 300, 900, 3600]  # 1m, 2m, 5m, 15m, 1h

resource_limits:
  max_concurrent_polls: 50
  max_video_storage_gb: 500
  max_audio_storage_gb: 100
```

### 10.3 Secrets Management

All secrets stored via:
- **Local dev:** `~/.hermes/.env` (gitignored)
- **CI/CD:** GitHub Actions Secrets
- **Production:** AWS Secrets Manager or HashiCorp Vault

**Example `.env`:**
```
HEYGEN_API_KEY=sk_V2_abc123xyz789
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-1001234567890
DATABASE_URL=postgresql://user:pass@localhost:5432/eworks
```

---

## 11. Example Workflows

### 11.1 Goose Content Agent Generates Video

**Context:** Goose content generation agent has drafted a LinkedIn post and wants to generate an accompanying video.

```python
# In Goose workflow (pseudo-code)

# Step 1: Generate post content
post_content = await claude.generate_linkedin_post(topic="AI Automation")
# Returns: "Exciting news: we just launched our new AI automation platform..."

# Step 2: Generate video script (optional enhancement)
video_script = post_content[:300]  # Or full post, depending on content

# Step 3: Submit HeyGen video generation via Goose tool
video_result = await goose.invoke_tool(
    "heygen_generate_video",
    {
        "script": video_script,
        "format": "reel",
        "avatar_id": "494ce8a1dbe64573a4cb1684ad0e0e14",
        "voice_id": "c0a044792fc64b3fa7dfc0700da93016",
        "webhook_url": "https://eworks.internal/webhooks/video-ready",
        "metadata": {
            "post_id": "some_id",
            "content_type": "linkedin_reel"
        }
    }
)

# Step 4: Receive immediate response with video_id
# {
#     "video_id": "vid_abc123",
#     "status": "submitted",
#     "job_id": 1001,
#     "format": "reel",
#     "submitted_at": "2026-06-05T10:35:00Z"
# }

# Step 5: Polling happens asynchronously
# When complete, webhook notifies Goose agent

# Step 6: Goose retrieves video and publishes
webhook_event = await goose.wait_for_webhook("video-ready")
video_local_path = webhook_event["local_path"]

# Upload to Instagram/TikTok
await ig_agent.post_reel(
    video_path=video_local_path,
    caption=post_content,
    hashtags=["#AI", "#Automation"]
)
```

### 11.2 Content Pipeline: Batch Video Generation

**Context:** Content Pipeline agent wants to generate 5 videos in a batch.

```python
# In content-pipeline (pseudo-code)

scripts = [
    "Welcome to AI automation...",
    "Today we're announcing...",
    "Here's how we built...",
    "Case study: Client X...",
    "Tips for scaling AI..."
]

jobs = []

for script in scripts:
    result = await heygen_agent.submit_video_generation(
        VideoGenerationRequest(
            script_text=script,
            format="youtube",
            metadata={"batch_id": "batch_2026_06_05", "index": i}
        )
    )
    jobs.append(result["video_id"])
    logger.info(f"Submitted video {result['video_id']}")

# Polling happens in background
# Check status periodically
while True:
    statuses = []
    for video_id in jobs:
        status = await heygen_agent.get_video_status(video_id)
        statuses.append(status)
        logger.info(f"Video {video_id}: {status['status']}")
    
    if all(s["status"] in ("completed", "failed") for s in statuses):
        break
    
    await asyncio.sleep(30)

# Process results
for status in statuses:
    if status["status"] == "completed":
        logger.info(f"Video {status['video_id']} ready: {status['local_path']}")
    else:
        logger.error(f"Video {status['video_id']} failed: {status['error_message']}")
```

### 11.3 Manual CLI Invocation

**Context:** Cesar wants to generate a quick video from CLI for testing.

```bash
# Command-line interface (hypothetical)

hermes agent heygen-video-agent submit \
    --script "Hello from Eworks Labs!" \
    --format reel \
    --webhook-url https://example.com/webhooks/video

# Output:
# Video submitted: vid_xyz123
# Job ID: 1005
# Check status: hermes agent heygen-video-agent status vid_xyz123

hermes agent heygen-video-agent status vid_xyz123

# Output:
# Status: processing (45%)
# Polling attempts: 4
# Submitted: 2026-06-05T10:35:00Z
# Estimated completion: 2026-06-05T10:42:00Z

# Once complete:
hermes agent heygen-video-agent status vid_xyz123

# Output:
# Status: completed
# Local path: /data/videos/vid_xyz123.mp4
# Duration: 45.3 seconds
# File size: 12.5 MB
# Completed: 2026-06-05T10:37:23Z
```

---

## 12. Acceptance Criteria

### 12.1 Functional Acceptance Criteria

| ID | Requirement | Acceptance Test | Status |
|----|-------------|-----------------|--------|
| **AC-001** | Submit video generation | POST `/agents/heygen/submit` returns `{video_id, status: "submitted", job_id}` within 2 seconds | Ready for dev |
| **AC-002** | Async polling | Video status transitions from "submitted" → "processing" → "completed" without blocking caller | Ready for dev |
| **AC-003** | Polling timeout | If video not complete after 20 minutes, mark as TIMEOUT and fail gracefully | Ready for dev |
| **AC-004** | Credit pre-check | Submission rejected if remaining credits < required cost; error message includes reset date | Ready for dev |
| **AC-005** | Avatar selection | Video generation supports custom avatar_id; defaults to Cesar's avatar if not specified | Ready for dev |
| **AC-006** | Voice customization | Voice config supports both HeyGen TTS (voice_id) and pre-uploaded audio (audio_asset_id) | Ready for dev |
| **AC-007** | Format support | Both reel (1080×1920) and youtube (1920×1080) formats generate correctly sized output | Ready for dev |
| **AC-008** | Video download | Completed video downloaded to `data/videos/{video_id}.mp4` within polling loop; file accessible and playable | Ready for dev |
| **AC-009** | Webhook notifications | On completion, POST to webhook_url with full event payload; retry up to 5 times on failure | Ready for dev |
| **AC-010** | Audio upload | `upload_audio()` accepts MP3 ≤100 MB; returns asset_id within 5 seconds; deduplicates by SHA256 hash | Ready for dev |
| **AC-011** | Cancel video | `cancel_video()` stops polling and marks job as cancelled; cannot cancel completed/failed jobs | Ready for dev |
| **AC-012** | Goose integration | Agent callable via `goose.invoke_tool("heygen_generate_video", {...})` with <100ms latency | Ready for dev |
| **AC-013** | Error handling | All error scenarios (auth, rate limit, server error, network) handled gracefully with retries and logging | Ready for dev |
| **AC-014** | Database persistence | All jobs persisted; can query status by video_id or job_id after restart | Ready for dev |

### 12.2 Non-Functional Acceptance Criteria

| ID | Requirement | Acceptance Test | Status |
|----|-------------|-----------------|--------|
| **AC-001** | Response latency | Submission endpoint returns within 2 seconds (p95) | Ready for dev |
| **AC-002** | Polling latency | Status query returns within 500ms (p95) | Ready for dev |
| **AC-003** | Concurrent polling | System handles ≥50 concurrent polling tasks without memory leak | Ready for dev |
| **AC-004** | Logging | All operations logged (submission, polling, completion, error) with video_id for traceability | Ready for dev |
| **AC-005** | Error recovery | Transient errors (429, 5xx) automatically retried; permanent errors (401, 404) fail fast | Ready for dev |
| **AC-006** | Storage efficiency | Videos stored efficiently; oldest videos auto-pruned if total storage exceeds 500 GB | Ready for dev |
| **AC-007** | Monitoring | Prometheus metrics exported: submission_duration, polling_duration, error_rate, credit_remaining | Ready for dev |

### 12.3 Integration Acceptance Criteria

| ID | Requirement | Acceptance Test | Status |
|----|-------------|-----------------|--------|
| **AC-001** | Goose framework | Agent registered as Goose tool; callable from Goose workflows; results flow through Goose runtime | Ready for dev |
| **AC-002** | BasePublisher inheritance | Agent inherits from `BasePublisher`; uses inherited `videos_dir`, `heygen_api_key`, database access | Ready for dev |
| **AC-003** | Database integration | Uses Eworks database connection; tables created on first run | Ready for dev |
| **AC-004** | Async support | All I/O operations are async (aiohttp, asyncio); no blocking calls in hot paths | Ready for dev |

---

## 13. Traceability to Phase 2 Roadmap

### 13.1 Roadmap Context

From `/docs/prd/product-roadmap.md`:

> **Epic 2 — Content Pipeline Agent (Q3 2026)**  
> The Content Pipeline Agent manages Eworks Labs' content strategy end-to-end: topic research, content drafting, publishing, and engagement tracking. It supports multi-platform publishing (LinkedIn, Twitter/X, etc.) and includes content repurposing and human approval workflows.

This **HeyGen Video Agent** specification is a **sub-feature of Epic 2**, supporting the content pipeline's ability to generate video content (specifically, avatar-driven videos) for repurposing across Instagram Reels, TikTok, YouTube Shorts, and LinkedIn.

### 13.2 Integration Map

```
Phase 2 — Epic 2: Content Pipeline Agent
├─── Topic Research Agent
├─── Content Drafting Agent
│    ├─── Instagram Post Generator
│    ├─── Twitter/X Thread Generator
│    └─── LinkedIn Post Generator
├─── Video Generation Agent (THIS SPEC)
│    ├─── HeyGen Video Agent (async, avatar-based)
│    └─── Video Repurposing Engine (future)
├─── Publishing Agent
│    ├─── LinkedIn Publisher
│    ├─── Twitter/X Publisher
│    └─── Instagram Publisher
├─── Engagement Tracking Agent
└─── Human Approval Workflow

Integration Flow:
  Topic Research → Content Drafting → [HeyGen Video Generation] → Publishing → Engagement Tracking
```

### 13.3 Dependency Chain

| Epic | Feature | Depends On | Enabled By |
|------|---------|-----------|-----------|
| E2 Content | HeyGen Video Agent | E1 Core (db, auth, logging) | Goose plugin system |
| E2 Content | LinkedIn Publisher | E1 Core, HeyGen Video | Video ready for publishing |
| E2 Content | Instagram Publisher | E1 Core, HeyGen Video | Video ready for publishing |
| Future | Content Repurposing | HeyGen Video Agent | Video format standardization |

### 13.4 User Story Mapping

**From E2 Content Pipeline epic:**

| Story | Title | Points | How HeyGen Agent Enables |
|-------|-------|--------|------------------------|
| US-E2-001 | Content Research & Topic Generation | 8 | N/A (upstream) |
| US-E2-002 | LinkedIn Post Drafting | 5 | N/A (upstream) |
| **US-E2-003** | **HeyGen Video Integration** | **8** | **This specification** |
| US-E2-004 | Multi-Platform Publishing | 13 | Uses video from US-E2-003 |
| US-E2-005 | Engagement Analytics | 8 | Tracks video performance |
| US-E2-006 | Human Approval Workflow | 5 | Integrates video review |

**Story US-E2-003 — HeyGen Video Integration:**

```markdown
### Title
As a content agent, I want to generate avatar-driven videos from scripts 
so that content can be repurposed across video platforms (Reels, TikTok, YouTube).

### Acceptance Criteria
1. ✓ Video generation submits asynchronously and returns immediately with video_id
2. ✓ Polling happens in background; no blocking on video completion
3. ✓ Support reel (9:16) and YouTube (16:9) formats
4. ✓ Pre-flight credit checks prevent wasted API calls
5. ✓ Webhook notifications alert downstream agents on completion
6. ✓ Callable from Goose autonomous workflows
7. ✓ Full error handling with retries for transient failures

### Story Points
8 (estimated based on async complexity, error handling, testing)

### Definition of Done
- [ ] Code complete and merged
- [ ] Unit tests: ≥90% coverage
- [ ] Integration tests with real HeyGen API (test account)
- [ ] E2E test: full submission → polling → completion workflow
- [ ] Documentation: API docs, error codes, webhook payload examples
- [ ] Code review approved by tech lead
- [ ] Performance benchmarks: latency, concurrent polling
- [ ] Deployed to staging environment
- [ ] Goose integration tested in real workflow
```

---

## 14. Risks, Constraints & Mitigations

### 14.1 Technical Risks

| Risk ID | Risk | Likelihood | Impact | Mitigation |
|---------|------|------------|--------|-----------|
| **TR-001** | HeyGen API availability (outages) | Medium | High (video generation fails) | Implement circuit breaker pattern; alert operator; provide fallback message to user |
| **TR-002** | Polling timeout (video takes >20 min) | Low | Medium (job marked failed) | Increase timeout to 30 min; implement manual retry capability |
| **TR-003** | Network interruption during download | Medium | Medium (incomplete video) | Retry download up to 3 times with exponential backoff; validate file integrity (checksum) |
| **TR-004** | Concurrent polling memory exhaustion | Low | High (agent crashes) | Cap concurrent polls to 50; implement priority queue; monitor memory usage |
| **TR-005** | Webhook delivery failure (network down) | Medium | Medium (client not notified) | Exponential retry up to 5 times; store delivery history; allow manual query of status |
| **TR-006** | Race condition: duplicate job submission | Low | Low (minor data redundancy) | Use database unique constraint on video_id; idempotent webhook handling |

### 14.2 Operational Risks

| Risk ID | Risk | Likelihood | Impact | Mitigation |
|---------|------|------------|--------|-----------|
| **OR-001** | HeyGen credits depleted | Medium | High (no video generation) | Daily credit monitoring; alert at 20% remaining; auto-pause submissions if <10% |
| **OR-002** | Disk space exhaustion (videos) | Low | Medium (new videos blocked) | Auto-prune oldest videos when total exceeds 500 GB; log space usage |
| **OR-003** | Database connection pool exhausted | Low | High (all operations blocked) | Proper connection pooling; monitoring; alert on >80% utilization |
| **OR-004** | Secret rotation (API key changed) | Low | High (all submissions fail) | Implement secret rotation without restart; periodically refresh key; health check on auth |

### 14.3 Integration Risks

| Risk ID | Risk | Likelihood | Impact | Mitigation |
|---------|------|------------|--------|-----------|
| **IR-001** | Goose framework API incompatibility | Low | High (tool not callable) | Early integration testing; use stable Goose API version; document version constraints |
| **IR-002** | Webhook URL validation (typos) | Medium | Medium (silent notification failure) | Validate webhook URL at submission time; allow dry-run test webhook; log all attempts |
| **IR-003** | Content agent expects sync video generation | Medium | Medium (workflow hangs) | Clear documentation: generation is async; provide polling helper function |

### 14.4 Constraints

| Constraint | Details | Impact |
|-----------|---------|--------|
| **HeyGen API Rate Limit** | ~100 reqs/min | Implement request queuing; exponential backoff on 429 |
| **HeyGen Video Limit** | Max 60s for MVP | Document in UI; reject scripts exceeding limit |
| **HeyGen Avatar Library** | Limited avatars available | Only support built-in avatars; custom avatars out of scope for MVP |
| **Polling Timeout** | 20 minutes max | Longer videos may timeout; provide manual retry |
| **Storage** | 500 GB limit | Auto-prune oldest videos; alert when approaching limit |
| **Audio Upload Size** | 100 MB max | Document in API; reject files exceeding limit |
| **Network Dependency** | Requires internet access | Cannot use offline; provide status page link for outages |

### 14.5 Mitigation Strategies

#### For TR-001 (HeyGen Outage)

```python
# Circuit breaker pattern
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RuntimeError)
)
async def submit_video_generation(self, request):
    try:
        response = await self.heygen_client.post(...)
    except RuntimeError as e:
        if "5" in str(e.status_code):  # 5xx server error
            logger.warning(f"HeyGen server error ({e.status_code}); retrying...")
            raise
        else:
            raise

# Alert operator
if circuit_breaker.is_open():
    await telegram_bot.send_message(
        "ALERT: HeyGen API circuit breaker tripped. "
        "Check https://status.heygen.com for outages."
    )
```

#### For TR-004 (Memory Exhaustion)

```python
# Semaphore to cap concurrent polls
self.poll_semaphore = asyncio.Semaphore(50)

async def _poll_video_async(self, video_id, job_id):
    async with self.poll_semaphore:
        # ... polling logic
        pass
```

#### For OR-001 (Credits Depleted)

```python
# Credit monitoring background task
async def _monitor_credits_async(self):
    while True:
        try:
            credits = await self.check_credits()
            remaining_pct = credits["remaining_quota"] / credits["total_quota"] * 100
            
            if remaining_pct < 10:
                logger.critical(f"CRITICAL: Only {remaining_pct:.1f}% HeyGen credits remain")
                self.submissions_paused = True
            elif remaining_pct < 20:
                logger.warning(f"WARNING: Only {remaining_pct:.1f}% HeyGen credits remain")
        except Exception as e:
            logger.error(f"Credit check failed: {e}")
        
        await asyncio.sleep(3600)  # Check hourly
```

---

## 15. Glossary & References

### 15.1 Glossary

| Term | Definition |
|------|-----------|
| **Avatar** | AI-generated digital character that appears in HeyGen videos |
| **Asset ID** | HeyGen's unique identifier for uploaded audio files |
| **TTS** | Text-to-Speech: synthetic voice generation from text |
| **Lip-sync** | Synchronization of avatar mouth movements to audio |
| **Video ID** | HeyGen-assigned unique identifier for a generated video |
| **Polling** | Periodic status checks to determine when async operation completes |
| **Backoff** | Increasing delay between retry attempts (exponential backoff: 1s, 2s, 4s, ...) |
| **Circuit Breaker** | Pattern to detect repeated failures and fail fast rather than retry indefinitely |
| **Webhook** | HTTP callback URL notified when async event completes |
| **Idempotent** | Operation produces same result if called multiple times |
| **Rate Limit** | Restriction on request frequency (e.g., 100 req/min) |
| **Quota** | Total available resource (e.g., 10,000 HeyGen credits/month) |

### 15.2 References

| Reference | URL |
|-----------|-----|
| HeyGen API Docs | https://docs.heygen.com/api-reference |
| HeyGen Status Page | https://status.heygen.com |
| Goose Framework Docs | https://goose.nousresearch.com/docs |
| Eworks OS Architecture | `/docs/architecture/eworks-core.md` |
| E2 Content Pipeline PRD | `/docs/prd/epic-2-content-pipeline.md` (future) |
| Async Python (asyncio) | https://docs.python.org/3/library/asyncio.html |
| PostgreSQL JSONB | https://www.postgresql.org/docs/current/datatype-json.html |

### 15.3 Related Specifications

- **base_publisher.py** — Base class for all publisher agents
- **content-pipeline/heygen.py** — Existing HeyGen module (to be refactored as Agent)
- **eworks/agents/publisher/video_generator.py** — Current video generation agent (async variant)

### 15.4 Document Approval

| Role | Name | Sign-Off | Date |
|------|------|----------|------|
| Product Manager | Morgan | — | 2026-06-05 |
| Tech Lead | TBD | Pending | — |
| Cesar (Product Owner) | Cesar Schneider | Pending | — |

---

## Appendix A: SQL Schema DDL

See Section 4.1–4.3 for complete schema definitions.

**Summary:**
- `video_generation_jobs` — Main job tracking table (1M rows max in MVP)
- `audio_assets` — Uploaded audio metadata (10K rows max)
- `webhook_deliveries` — Webhook delivery attempt history (10M rows max)

All tables include `created_at`, `updated_at` timestamps for auditing.

---

## Appendix B: Example Python Implementation Skeleton

```python
# eworks/agents/publisher/heygen_video_agent.py

from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from eworks.agents.publisher.base_publisher import BasePublisher
from eworks.db import Database

logger = logging.getLogger(__name__)

class HeyGenVideoAgent(BasePublisher):
    """
    Async video generation via HeyGen API.
    
    Inherits from BasePublisher; integrable with Goose framework.
    """
    
    DEFAULT_AVATAR_ID = "494ce8a1dbe64573a4cb1684ad0e0e14"
    DEFAULT_VOICE_ID = "c0a044792fc64b3fa7dfc0700da93016"
    
    HEYGEN_API_BASE = "https://api.heygen.com"
    HEYGEN_UPLOAD_BASE = "https://upload.heygen.com"
    
    def __init__(self, db: Database, config: dict):
        super().__init__(db, config)
        self.api_key = self.heygen_api_key
        self.poll_semaphore = asyncio.Semaphore(50)
    
    async def submit_video_generation(
        self,
        request: VideoGenerationRequest
    ) -> Dict[str, Any]:
        """
        Submit video generation to HeyGen.
        Returns immediately with video_id; polling happens in background.
        """
        # Validation, credit check, submission...
        # [Implementation per section 6.2]
        pass
    
    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """Query video generation status."""
        # [Implementation per section 5.1.2]
        pass
    
    async def check_credits(self) -> Dict[str, Any]:
        """Check remaining HeyGen credits."""
        # [Implementation per section 5.1.3]
        pass
    
    async def upload_audio(self, audio_path: str | Path) -> Dict[str, Any]:
        """Upload MP3 audio for lip-sync."""
        # [Implementation per section 5.1.4]
        pass
    
    async def cancel_video(self, video_id: str) -> Dict[str, Any]:
        """Cancel a video generation job."""
        # [Implementation per section 5.1.5]
        pass
    
    async def _poll_video_async(self, video_id: str, job_id: int):
        """Background polling task with exponential backoff."""
        # [Implementation per section 6.3]
        pass
    
    async def _download_video(
        self,
        video_id: str,
        video_url: str
    ) -> Path:
        """Download completed video from HeyGen CDN."""
        # [Implementation per section 6.4]
        pass
    
    async def run(self, campaign_id: int) -> dict:
        """
        Async agent entry point (from BasePublisher).
        [To be defined based on Eworks OS scheduler.]
        """
        pass
```

---

**END OF SPECIFICATION**

---

**Document Version:** 1.0.0  
**Status:** Final / Ready for Development  
**Last Updated:** 2026-06-05  
**Author:** Morgan (PM)  
**Target Release:** Q3 2026 (Epic 2 — Content Pipeline)
