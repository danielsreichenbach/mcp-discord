# Real-Time Monitoring Implementation Plan

## Overview

Implement Gateway-based real-time monitoring for Discord events, enabling keyword tracking, conversation history logging, and activity analysis. This provides the infrastructure for researching topics and tracking conversations across Discord channels.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Server                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  HTTP Tools  │  │  Resources   │  │   Gateway    │       │
│  │  (existing)  │  │   (queries)  │  │   Monitor    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                            ▲                  │              │
│                            │                  ▼              │
│                    ┌──────────────────────────────┐          │
│                    │      Event Storage           │          │
│                    │  (SQLite / In-Memory Cache)  │          │
│                    └──────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Gateway Connection Manager

**File:** `src/discord_mcp/gateway.py`

**Purpose:** Manage persistent WebSocket connection to Discord Gateway alongside the existing HTTP bot client.

**Key Design Decisions:**
- Use `discord.py`'s built-in Gateway connection (via bot client)
- Register event listeners on the existing bot instance
- Store events in a local database for querying
- Support filtering and aggregation via MCP resources

---

### 2. Event Storage

**File:** `src/discord_mcp/storage.py`

**Purpose:** Persistent storage for monitored events.

**Database Schema (SQLite):**

```sql
-- Monitored messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    message_id TEXT UNIQUE NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    guild_id TEXT,
    guild_name TEXT,
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_display_name TEXT,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    edited_timestamp TEXT,
    mentions_users TEXT,  -- JSON array of user IDs
    mentions_roles TEXT,  -- JSON array of role IDs
    mentions_channels TEXT,  -- JSON array of channel IDs
    attachments TEXT,  -- JSON array of attachment URLs
    reactions TEXT,  -- JSON array of reaction data
    matched_keywords TEXT,  -- JSON array of matched keyword IDs
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_messages_channel ON messages(channel_id);
CREATE INDEX idx_messages_author ON messages(author_id);
CREATE INDEX idx_messages_guild ON messages(guild_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_messages_content ON messages(content);

-- Full-text search virtual table
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    author_name,
    channel_name,
    guild_name,
    content='messages',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content, author_name, channel_name, guild_name)
    VALUES (new.id, new.content, new.author_name, new.channel_name, new.guild_name);
END;

CREATE TRIGGER messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid) VALUES('delete', old.id);
END;

CREATE TRIGGER messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid) VALUES('delete', old.id);
    INSERT INTO messages_fts(rowid, content, author_name, channel_name, guild_name)
    VALUES (new.id, new.content, new.author_name, new.channel_name, new.guild_name);
END;

-- Keyword definitions
CREATE TABLE keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,  -- Regex pattern or simple string
    pattern_type TEXT DEFAULT 'simple',  -- 'simple', 'regex', 'word'
    is_case_sensitive INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for active keyword lookup
CREATE INDEX idx_keywords_active ON keywords(is_active);

-- Monitored channels configuration
CREATE TABLE monitored_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT UNIQUE NOT NULL,
    guild_id TEXT,
    is_active INTEGER DEFAULT 1,
    include_threads INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Monitored guilds configuration
CREATE TABLE monitored_guilds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT UNIQUE NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Activity summary (aggregated stats)
CREATE TABLE activity_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    guild_id TEXT,
    channel_id TEXT,
    message_count INTEGER DEFAULT 0,
    unique_authors INTEGER DEFAULT 0,
    keyword_matches INTEGER DEFAULT 0,
    UNIQUE(date, guild_id, channel_id)
);

-- Conversation threads (for grouping related messages)
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT UNIQUE NOT NULL,  -- Derived from reply chain or topic
    channel_id TEXT NOT NULL,
    guild_id TEXT,
    started_at TEXT NOT NULL,
    last_message_at TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    participant_ids TEXT,  -- JSON array
    topic_keywords TEXT  -- JSON array of detected topics
);
```

---

### 3. Event Handlers

**File:** `src/discord_mcp/events.py`

**Purpose:** Discord Gateway event handlers for message capture.

#### Event: on_message
```python
async def on_message(message: discord.Message) -> None:
    """Handle incoming messages for monitoring."""
    
    # Skip bot messages unless configured otherwise
    if message.author.bot:
        return
    
    # Check if channel/guild is monitored
    if not await is_monitored(message):
        return
    
    # Check for keyword matches
    matched_keywords = await check_keywords(message.content)
    
    # Store message
    await store_message(message, matched_keywords)
    
    # Update activity summary
    await update_activity_summary(message)
```

#### Event: on_message_edit
```python
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    """Handle message edits - update stored content."""
    await update_message(after)
```

#### Event: on_message_delete
```python
async def on_message_delete(message: discord.Message) -> None:
    """Handle message deletions - mark as deleted or remove."""
    await mark_message_deleted(message.id)
```

#### Event: on_reaction_add / on_reaction_remove
```python
async def on_reaction_add(reaction: discord.Reaction, user: discord.User) -> None:
    """Track reactions on monitored messages."""
    await update_reactions(reaction.message)

async def on_reaction_remove(reaction: discord.Reaction, user: discord.User) -> None:
    await update_reactions(reaction.message)
```

---

### 4. Keyword Management

#### Tool: add_keyword
**Purpose:** Add a keyword or pattern to monitor

**Handler Signature:**
```python
async def add_keyword(
    pattern: str,
    pattern_type: str = "simple",  # 'simple', 'word', 'regex'
    case_sensitive: bool = False,
    description: str | None = None
) -> dict[str, Any]
```

**Pattern Types:**
- `simple`: Simple substring match (case-insensitive by default)
- `word`: Whole word match using word boundaries
- `regex`: Full regular expression pattern

**Returns:**
```python
{
    "keyword_id": int,
    "pattern": str,
    "pattern_type": str,
    "is_active": True
}
```

---

#### Tool: remove_keyword
**Purpose:** Remove a keyword pattern

**Handler Signature:**
```python
async def remove_keyword(keyword_id: int) -> dict[str, Any]
```

---

#### Tool: list_keywords
**Purpose:** List all configured keywords

**Returns:**
```python
{
    "keywords": [
        {
            "id": int,
            "pattern": str,
            "pattern_type": str,
            "is_case_sensitive": bool,
            "is_active": bool,
            "description": str | None,
            "match_count": int  # Number of matches
        },
        ...
    ]
}
```

---

### 5. Channel Monitoring Configuration

#### Tool: monitor_channel
**Purpose:** Add a channel to the monitoring list

**Handler Signature:**
```python
async def monitor_channel(
    channel_id: str,
    include_threads: bool = True
) -> dict[str, Any]
```

---

#### Tool: unmonitor_channel
**Purpose:** Remove a channel from monitoring

**Handler Signature:**
```python
async def unmonitor_channel(channel_id: str) -> dict[str, Any]
```

---

#### Tool: monitor_guild
**Purpose:** Monitor all channels in a guild

**Handler Signature:**
```python
async def monitor_guild(guild_id: str) -> dict[str, Any]
```

---

#### Tool: list_monitored
**Purpose:** List all monitored channels and guilds

**Returns:**
```python
{
    "guilds": [
        {"guild_id": str, "guild_name": str, "is_active": bool}
    ],
    "channels": [
        {"channel_id": str, "channel_name": str, "guild_id": str, "guild_name": str, "is_active": bool}
    ]
}
```

---

### 6. Query Resources

#### Resource: discord://messages/search
**Purpose:** Search stored messages

**Query Parameters (via resource arguments):**
- `query`: Full-text search query
- `channel_id`: Filter by channel
- `author_id`: Filter by author
- `guild_id`: Filter by guild
- `keyword_id`: Filter by matched keyword
- `since`: ISO datetime, messages after this time
- `until`: ISO datetime, messages before this time
- `limit`: Maximum results (default 100)

**Implementation:**
```python
@mcp.resource("discord://messages/search")
async def search_messages_resource(
    query: str = "",
    channel_id: str | None = None,
    author_id: str | None = None,
    guild_id: str | None = None,
    keyword_id: int | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100
) -> str:
    results = await search_messages(
        query=query,
        channel_id=channel_id,
        author_id=author_id,
        guild_id=guild_id,
        keyword_id=keyword_id,
        since=since,
        until=until,
        limit=limit
    )
    return json.dumps(results, indent=2)
```

**Returns:**
```python
[
    {
        "message_id": str,
        "channel_id": str,
        "channel_name": str,
        "guild_id": str,
        "guild_name": str,
        "author_id": str,
        "author_name": str,
        "content": str,
        "timestamp": str,
        "matched_keywords": [{"id": int, "pattern": str}, ...],
        "url": str  # Discord message URL
    },
    ...
]
```

---

#### Resource: discord://messages/keyword/{keyword_id}
**Purpose:** Get all messages matching a specific keyword

---

#### Resource: discord://activity/{date}
**Purpose:** Activity summary for a specific date

**Returns:**
```python
{
    "date": str,
    "total_messages": int,
    "unique_authors": int,
    "keyword_matches": int,
    "top_channels": [
        {"channel_id": str, "channel_name": str, "message_count": int}
    ],
    "top_authors": [
        {"author_id": str, "author_name": str, "message_count": int}
    ],
    "keyword_breakdown": [
        {"keyword": str, "match_count": int}
    ]
}
```

---

#### Resource: discord://activity/range/{start}/{end}
**Purpose:** Activity summary for a date range

---

### 7. Query Tools

#### Tool: search_messages
**Purpose:** Search stored messages with advanced filters

**Handler Signature:**
```python
async def search_messages(
    query: str,
    channel_id: str | None = None,
    author_id: str | None = None,
    guild_id: str | None = None,
    keyword: str | None = None,  # Keyword pattern
    since: str | None = None,
    until: str | None = None,
    limit: int = 100
) -> str
```

**FTS5 Search Syntax Support:**
- Simple terms: `"hello world"`
- Phrase search: `"\"exact phrase\""`
- Boolean operators: `"discord AND bot"`, `"help OR support"`
- Negation: `"bot NOT spam"`
- Prefix: `"disc*"`

---

#### Tool: get_conversation
**Purpose:** Get a conversation thread by starting message ID

**Handler Signature:**
```python
async def get_conversation(message_id: str) -> str
```

**Returns:**
```python
{
    "messages": [
        {
            "message_id": str,
            "author_name": str,
            "content": str,
            "timestamp": str,
            "is_reply_to": str | None  # Message ID this replies to
        },
        ...
    ],
    "participants": [{"id": str, "name": str}, ...],
    "started_at": str,
    "last_message_at": str
}
```

---

#### Tool: get_activity_report
**Purpose:** Generate an activity report for a time period

**Handler Signature:**
```python
async def get_activity_report(
    start_date: str,  # YYYY-MM-DD
    end_date: str,    # YYYY-MM-DD
    guild_id: str | None = None,
    channel_id: str | None = None
) -> str
```

**Returns:**
```python
{
    "period": {"start": str, "end": str},
    "summary": {
        "total_messages": int,
        "unique_authors": int,
        "unique_channels": int,
        "keyword_matches": int
    },
    "daily_breakdown": [
        {"date": str, "messages": int, "authors": int}
    ],
    "top_authors": [...],
    "top_channels": [...],
    "top_keywords": [...]
}
```

---

### 8. Export Tools

#### Tool: export_messages
**Purpose:** Export messages to a file format

**Handler Signature:**
```python
async def export_messages(
    format: str,  # 'json', 'csv', 'markdown'
    channel_id: str | None = None,
    guild_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    include_reactions: bool = True
) -> str
```

**Returns:** File path or base64-encoded content

---

## Configuration

### Environment Variables

```bash
# Storage configuration
DISCORD_MCP_DB_PATH=/path/to/discord_mcp.db  # Default: ./discord_mcp.db

# Monitoring configuration  
DISCORD_MCP_MONITOR_ALL_GUILDS=false  # Monitor all guilds bot is in
DISCORD_MCP_MONITOR_DM=false  # Monitor direct messages
DISCORD_MCP_RETENTION_DAYS=30  # Delete messages older than this
DISCORD_MCP_MAX_MESSAGES=1000000  # Maximum messages to store

# Performance
DISCORD_MCP_BATCH_SIZE=100  # Batch insert size
DISCORD_MCP_CACHE_SIZE=10000  # In-memory cache size
```

### Initial Keywords

Load from `config/keywords.json`:
```json
[
    {"pattern": "help", "type": "word", "description": "Support requests"},
    {"pattern": "bug", "type": "word", "description": "Bug reports"},
    {"pattern": "feature", "type": "word", "description": "Feature discussions"},
    {"pattern": "api", "type": "word", "description": "API-related discussions"},
    {"pattern": "documentation", "type": "word", "description": "Documentation mentions"}
]
```

### Initial Monitored Channels

Load from `config/channels.json`:
```json
{
    "guilds": ["123456789012345678"],
    "channels": ["987654321098765432"],
    "exclude_channels": ["111111111111111111"]
}
```

---

## File Structure

```
src/discord_mcp/
├── __init__.py
├── server.py           # Tool/resource registrations
├── handlers.py         # HTTP API handlers (existing)
├── resources.py        # Resource handlers (existing)
├── client.py           # Discord client setup (existing)
├── gateway.py          # NEW: Gateway connection setup
├── events.py           # NEW: Event handlers
├── storage.py          # NEW: Database operations
├── keywords.py         # NEW: Keyword matching engine
├── export.py           # NEW: Export utilities
└── config.py           # NEW: Configuration loading

config/
├── keywords.json       # Initial keywords
└── channels.json       # Initial monitored channels

migrations/
├── 001_initial.sql     # Initial schema
├── 002_add_conversations.sql
└── 003_add_fts.sql
```

---

## Implementation Phases

### Phase 3A: Core Infrastructure (Week 1-2)

1. **Storage Layer**
   - Implement SQLite database schema
   - Create `storage.py` with async database operations
   - Implement connection pooling
   - Add migration system

2. **Gateway Integration**
   - Modify `client.py` to register event listeners
   - Implement `on_message` handler with storage
   - Handle connection failures and reconnection

3. **Basic Configuration**
   - Environment variable parsing
   - JSON config file loading
   - Initial monitoring setup

**Deliverables:**
- Messages captured and stored
- Database schema deployed
- Basic monitoring active

---

### Phase 3B: Keyword Engine (Week 3)

1. **Keyword Matching**
   - Implement pattern types (simple, word, regex)
   - Create efficient matching algorithm
   - Store matched keywords with messages

2. **Keyword Management Tools**
   - `add_keyword`
   - `remove_keyword`
   - `list_keywords`

3. **Channel Configuration Tools**
   - `monitor_channel` / `unmonitor_channel`
   - `monitor_guild` / `unmonitor_guild`
   - `list_monitored`

**Deliverables:**
- Real-time keyword detection
- Configurable monitoring scope

---

### Phase 3C: Query & Search (Week 4)

1. **Full-Text Search**
   - Configure FTS5 virtual tables
   - Implement search with ranking

2. **Query Resources**
   - `discord://messages/search`
   - `discord://messages/keyword/{id}`
   - `discord://activity/{date}`

3. **Query Tools**
   - `search_messages` with advanced filters
   - `get_conversation` thread retrieval
   - `get_activity_report`

**Deliverables:**
- Searchable message history
- Activity analytics

---

### Phase 3D: Polish & Export (Week 5)

1. **Event Handling Improvements**
   - `on_message_edit` handler
   - `on_message_delete` handler
   - Reaction tracking

2. **Export Functionality**
   - `export_messages` (JSON, CSV, Markdown)
   - Activity report generation

3. **Performance Optimization**
   - Batch insert optimization
   - Query caching
   - Index optimization

4. **Retention & Cleanup**
   - Automatic old message cleanup
   - Database vacuum scheduling

**Deliverables:**
- Complete monitoring system
- Export capabilities
- Production-ready

---

## Performance Considerations

### Database Optimization

1. **Batch Inserts:** Accumulate messages and insert in batches
   ```python
   message_buffer = []
   BUFFER_SIZE = 100
   
   async def on_message(message):
       message_buffer.append(message)
       if len(message_buffer) >= BUFFER_SIZE:
           await flush_buffer()
   ```

2. **Connection Pooling:** Use aiosqlite with connection pool

3. **Index Maintenance:** Schedule periodic `ANALYZE` calls

4. **WAL Mode:** Enable Write-Ahead Logging for better concurrency
   ```sql
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   ```

### Memory Management

1. **Message Cache:** LRU cache for recent messages
2. **Stream Processing:** Don't load all messages into memory for bulk operations
3. **Pagination:** Always paginate large result sets

---

## Security Considerations

1. **Database Encryption:** Consider SQLCipher for sensitive data
2. **Access Control:** MCP tools should respect Discord permissions
3. **Data Retention:** Implement configurable retention policies
4. **Audit Logging:** Log all monitoring configuration changes

---

## Testing Strategy

### Unit Tests

```python
# tests/test_keywords.py
@pytest.mark.asyncio
async def test_simple_keyword_match():
    engine = KeywordEngine()
    engine.add_keyword("help", "simple")
    
    matches = engine.check("I need help with this")
    assert len(matches) == 1
    assert matches[0].pattern == "help"

@pytest.mark.asyncio
async def test_regex_keyword_match():
    engine = KeywordEngine()
    engine.add_keyword(r"issue-\d+", "regex")
    
    matches = engine.check("Please check issue-123")
    assert len(matches) == 1
```

### Integration Tests

```python
# tests/test_storage.py
@pytest.mark.asyncio
async def test_message_round_trip():
    storage = MessageStorage(":memory:")
    
    # Store message
    await storage.store_message(mock_message)
    
    # Retrieve message
    results = await storage.search_messages(query="test")
    assert len(results) == 1
```

### Load Testing

- Simulate high message volume
- Test concurrent read/write operations
- Verify memory stability under load

---

## Monitoring Dashboard (Future Enhancement)

Consider adding a simple web dashboard for:
- Real-time message feed
- Keyword match notifications
- Activity charts
- Configuration management

Could be implemented as a separate Flask/FastAPI app that reads from the same SQLite database.
