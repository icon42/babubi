# MCP Server

Babubi has a [Model Context Protocol](https://modelcontextprotocol.io) (MCP)
server that lets AI assistants — like Claude Desktop — log and query Babubi
data using natural language. Ask your assistant to record a feeding, check last
night's sleep, or summarize the day, and it reads and writes through Babubi's
[API](api.md).

The server lives in its own repository:
[**icon42/babubi-mcp**](https://github.com/icon42/babubi-mcp).

## What it can do

The server exposes tools grouped by domain, covering create, list, update, and
delete operations where applicable:

- Children
- Diaper changes
- Feedings
- Sleep
- Pumping
- Tummy times
- Timers
- Measurements (weight, height, head circumference, BMI, temperature)
- Notes (and tags)

## Setup

The MCP server connects to a running Babubi instance and authenticates with an
API token. Generate a token from the User Settings page of the user the assistant
should act as (see [Authentication](api.md#authentication)).

!!! note

    Installation and configuration — including Docker (`http` transport) and Claude
    Desktop (`stdio` transport) setups and the `BABUBI_URL` / `BABUBI_TOKEN`
    environment variables — are documented in the
    [icon42/babubi-mcp](https://github.com/icon42/babubi-mcp) repository.
    Because the server is maintained there, that repository is the source of truth
    for setup steps.
