sequenceDiagram
    autonumber
    actor User as 👤 Developer
    participant VSCode as 💻 VS Code (MCP Client)
    participant Okta as 🔐 Okta (Identity Provider)
    participant Server as ⚙️ MCP Server (Python)

    Note over VSCode, Server: 🔒 PHASE 1: AUTHENTICATION (AuthN)

    User->>VSCode: Connect to MCP Server
    VSCode->>Server: POST /mcp (Streamable HTTP)
    Server-->>VSCode: 401 Unauthorized
    Note right of Server: Header: WWW-Authenticate<br/>(Go to Okta to login)

    VSCode->>User: 📝 Prompt for Okta Client ID (One-time)
    User->>VSCode: Enters Client ID
    VSCode->>User: Opens Browser for Login
    User->>Okta: Enters Credentials
    Okta->>Okta: Validate User
    Okta-->>VSCode: Authorization Code
    VSCode->>Okta: Exchange Code for Token (PKCE)
    Okta-->>VSCode: 🔑 Access Token (JWT)
    Note right of Okta: Payload includes:<br/>- sub: user@email.com<br/>- scp: ["openid", "profile"]<br/>- groups: ["devopsadmin_group"]

    Note over VSCode, Server: 🛡️ PHASE 2: CONNECTION & DISCOVERY

    VSCode->>Server: POST /mcp (Authorization: Bearer 🔑)
    
    rect rgb(240, 255, 240)
        Note right of Server: 🔍 Verify Token (Stateless)<br/>1. Check Signature (JWKS)<br/>2. Check Expiry<br/>3. Check Audience
    end
    
    Server-->>VSCode: 200 OK (Session Started)

    VSCode->>Server: JSON-RPC: list_tools
    
    rect rgb(255, 250, 240)
        Note right of Server: 🕵️ Dynamic Visibility<br/>Server checks 'groups' claim.<br/>Filters tools based on permissions.
    end
    
    Server-->>VSCode: Return List [pipeline_troubleshoot, pipeline_creation]

    Note over VSCode, Server: ⛔ PHASE 3: AUTHORIZATION (AuthZ)

    User->>VSCode: Run "pipeline_creation" (Restricted Tool)
    VSCode->>Server: JSON-RPC: call_tool("pipeline_creation")
    
    rect rgb(255, 240, 240)
        Note right of Server: 👮 Authorization Check<br/>Server verifies user is in<br/>'devopsadmin_group'
    end

    alt User has Group
        Server->>Server: Execute Tool
        Server-->>VSCode: Result: "Pipeline Created"
    else User missing Group
        Server-->>VSCode: ⛔ Error: Access Denied
    end

    User->>VSCode: Run "pipeline_troubleshoot" (Open Tool)
    VSCode->>Server: JSON-RPC: call_tool("pipeline_troubleshoot")
    Server->>Server: Execute Tool
    Server-->>VSCode: Result: "Troubleshooting Info..."